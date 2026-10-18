"""Integration tests for the ported supply and claim lanes.

Covers the contract map and the safety verdicts from PORT-CONTRACT-AND-SAFETY.md:
  - supply: scope, validation, audit, status-transition graph
  - claims: the 8 integrity checks, care-first priority, and the hard privacy promise that no
    cleartext reporter contact is ever persisted or returned

Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_supply_claims.py -q
"""
import base64
import io
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'src'
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from PIL import Image  # noqa: E402

SECRET = 'integration-test-secret'
TODAY = '2026-10-18'
FUTURE = '2099-01-01'


def png_bytes(width=400, height=320) -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), '#88aa66').save(buffer, format='PNG')
    return buffer.getvalue()


class LaneHarness(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'C05_CONTACT_HMAC_SECRET': SECRET})
        self.env.start()
        self.temp = tempfile.TemporaryDirectory()
        from c05_bootstrap import create_app
        from shared_mvp.testing import LocalClient as TestClient
        self.app = create_app(str(Path(self.temp.name) / 'lanes.sqlite'))
        self.client = TestClient(self.app)
        self.app.state.rate_limiter.reset()
        self.addCleanup(self._close)

    def _close(self):
        self.env.stop()
        self.client.close()
        self.app.state.store.db.close()
        self.temp.cleanup()

    def make_inspection(self, kitchen='KITCHEN-A', role='SUPERVISOR', day=TODAY):
        payload = {
            'role': role, 'kitchen_id': kitchen, 'shift_id': 'SHIFT-AM',
            'batch_id': 'BATCH-DEMO', 'manifest_version': 1, 'mime_type': 'image/png',
            'data_base64': base64.b64encode(png_bytes()).decode(),
            'idempotency_key': uuid.uuid4().hex,
        }
        response = self.client.post('/api/inspections', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        record = response.json()
        # Force created_at onto the chosen day so claim linkage by date is testable.
        store = self.app.state.store
        record['created_at'] = f'{day}T08:00:00+00:00'
        store.put('inspection', record['inspection_id'], record)
        return record

    def make_lot(self, **overrides):
        payload = {
            'role': 'SUPERVISOR', 'kitchen_id': 'KITCHEN-A', 'ingredient': 'Chicken',
            'supplier': 'Warung Kita', 'origin': 'Bogor', 'travel_time_min': 145,
            'arrival_temp_c': 4.0, 'price_per_unit': 55000, 'quantity': 40,
            'received_at': f'{TODAY}T06:00:00+00:00', 'expires_at': '2026-10-25',
        }
        payload.update(overrides)
        response = self.client.post('/api/supply/lots', json=payload)
        return response


class SupplyLots(LaneHarness):
    def test_create_returns_lot_with_checks(self):
        response = self.make_lot()
        self.assertEqual(response.status_code, 201, response.text)
        lot = response.json()
        self.assertEqual(lot['status'], 'received')
        self.assertEqual(lot['checks']['temp_ok'], True)
        self.assertEqual(lot['checks']['expiry_ok'], True)
        self.assertIsNone(lot['price_baseline_average'], 'cold store means no price baseline')

    def test_create_is_audited(self):
        lot = self.make_lot().json()
        events = self.app.state.store.history(lot['lot_id'])
        self.assertEqual(events[0]['event'], 'lot_received')

    def test_warm_delivery_fails_temp_check(self):
        lot = self.make_lot(arrival_temp_c=11.5).json()
        self.assertFalse(lot['checks']['temp_ok'])

    def test_expired_shelf_fails_expiry_check(self):
        lot = self.make_lot(received_at=f'{TODAY}T06:00:00+00:00', expires_at='2026-10-19').json()
        self.assertFalse(lot['checks']['expiry_ok'])
        self.assertEqual(lot['days_until_expiry_at_receipt'], 1)

    def test_price_anomaly_against_prior_average(self):
        self.make_lot(price_per_unit=100000)
        second = self.make_lot(price_per_unit=200000).json()
        self.assertFalse(second['checks']['price_ok'])
        self.assertEqual(second['price_baseline_average'], 100000)
        self.assertEqual(second['price_baseline_count'], 1)

    def test_crew_cannot_write_lots(self):
        response = self.make_lot(role='CREW')
        self.assertEqual(response.status_code, 403)

    def test_kitchen_outside_scope_rejected(self):
        response = self.make_lot(kitchen_id='KITCHEN-C')
        self.assertEqual(response.status_code, 403)

    def test_unknown_role_rejected(self):
        self.assertEqual(self.make_lot(role='NOBODY').status_code, 422)

    def test_negative_temperature_bound(self):
        self.assertEqual(self.make_lot(arrival_temp_c=-200).status_code, 422)

    def test_non_numeric_price_rejected(self):
        self.assertEqual(self.make_lot(price_per_unit='cheap').status_code, 422)

    def test_bad_received_at_rejected(self):
        self.assertEqual(self.make_lot(received_at='yesterday').status_code, 422)

    def test_list_filters_by_kitchen(self):
        self.make_lot(kitchen_id='KITCHEN-A')
        self.make_lot(kitchen_id='KITCHEN-B')
        a = self.client.get('/api/supply/lots?role=SUPERVISOR&kitchen_id=KITCHEN-A').json()
        self.assertTrue(a['lots'])
        self.assertTrue(all(l['kitchen_id'] == 'KITCHEN-A' for l in a['lots']))

    def test_list_rejects_out_of_scope_kitchen(self):
        self.assertEqual(self.client.get('/api/supply/lots?role=CREW&kitchen_id=KITCHEN-B').status_code, 403)

    def test_unknown_status_filter_rejected(self):
        self.assertEqual(self.client.get('/api/supply/lots?role=ADMIN&status=unknown').status_code, 422)

    def test_out_of_scope_lot_detail_is_404_not_403(self):
        lot = self.make_lot(kitchen_id='KITCHEN-B').json()
        response = self.client.get(f"/api/supply/lots/{lot['lot_id']}?role=CREW")
        self.assertEqual(response.status_code, 404, '403 would confirm the lot exists')

    def test_status_transition_graph_is_enforced(self):
        lot = self.make_lot().json()
        ok = self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                               json={'role': 'SUPERVISOR', 'status': 'inspected'})
        self.assertEqual(ok.status_code, 200, ok.text)
        skipped = self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                                    json={'role': 'SUPERVISOR', 'status': 'received'})
        self.assertEqual(skipped.status_code, 409, 'inspected cannot go back to received')

    def test_reject_requires_reason(self):
        lot = self.make_lot().json()
        no_reason = self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                                      json={'role': 'SUPERVISOR', 'status': 'rejected'})
        self.assertEqual(no_reason.status_code, 422)
        with_reason = self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                                        json={'role': 'SUPERVISOR', 'status': 'rejected',
                                              'reason': 'Cold chain broken'})
        self.assertEqual(with_reason.status_code, 200)

    def test_terminal_status_is_final(self):
        lot = self.make_lot().json()
        self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                          json={'role': 'SUPERVISOR', 'status': 'rejected', 'reason': 'spoiled'})
        again = self.client.patch(f"/api/supply/lots/{lot['lot_id']}",
                                  json={'role': 'SUPERVISOR', 'status': 'inspected'})
        self.assertEqual(again.status_code, 409)


class SupplyAnomalies(LaneHarness):
    def test_warm_and_expiring_are_flagged(self):
        self.make_lot(arrival_temp_c=11.5, expires_at='2026-10-19')
        result = self.client.get('/api/supply/anomalies?role=ADMIN&kitchen_id=KITCHEN-A').json()
        kinds = {f['kind'] for item in result['anomalies'] for f in item['flags']}
        self.assertIn('warm_delivery', kinds)
        self.assertEqual(result['temperature_threshold_c'], 5.0)

    def test_clean_lot_has_no_anomalies(self):
        self.make_lot()
        result = self.client.get('/api/supply/anomalies?role=ADMIN&kitchen_id=KITCHEN-A').json()
        self.assertEqual(result['count'], 0)

    def test_crew_sees_only_own_kitchen(self):
        self.make_lot(kitchen_id='KITCHEN-B', arrival_temp_c=20.0)
        result = self.client.get('/api/supply/anomalies?role=CREW').json()
        self.assertEqual(result['count'], 0)


class ClaimIntake(LaneHarness):
    def claim_payload(self, **overrides):
        payload = {
            'kitchen_id': 'KITCHEN-A', 'reporter_name': 'Orang Tua',
            'reporter_contact': '+62 812-3456-7890', 'meal_date': TODAY,
            'symptoms': ['nausea', 'fever'], 'onset_hours': 6,
        }
        payload.update(overrides)
        return payload

    def test_submit_returns_public_view_only(self):
        response = self.client.post('/api/claims', json=self.claim_payload())
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body['contact_masked'], '*********7890')
        self.assertNotIn('contact_blind_index', body)
        self.assertNotIn('reporter_contact', body)

    def test_no_cleartext_contact_anywhere_in_store(self):
        self.client.post('/api/claims', json=self.claim_payload())
        stored = [c for c in self.app.state.store.list_kind('claim')]
        self.assertTrue(stored)
        blob = repr(stored)
        for leak in ('6281234567890', '812-3456-7890', '+62 812-3456-7890'):
            self.assertNotIn(leak, blob, f'cleartext contact {leak!r} leaked into the store')

    def test_no_cleartext_in_audit_trail(self):
        created = self.client.post('/api/claims', json=self.claim_payload()).json()
        events = repr(self.app.state.store.history(created['claim_id']))
        self.assertNotIn('812-3456', events)

    def test_missing_secret_refuses_intake(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop('C05_CONTACT_HMAC_SECRET', None)
            response = self.client.post('/api/claims', json=self.claim_payload())
        self.assertEqual(response.status_code, 503, 'must fail closed, never fall back to cleartext')

    def test_formatting_variants_are_the_same_person(self):
        first = self.client.post('/api/claims', json=self.claim_payload()).json()
        second = self.client.post('/api/claims', json=self.claim_payload(
            reporter_contact='+6281234567890')).json()
        codes = {f['code'] for f in second['integrity']['findings']}
        self.assertIn('duplicate_submission', codes)
        self.assertNotEqual(first['claim_id'], second['claim_id'])

    def test_medical_priority_stays_urgent_despite_conflicts(self):
        body = self.client.post('/api/claims', json=self.claim_payload(
            meal_date=FUTURE)).json()
        self.assertGreater(body['integrity']['count'], 0)
        self.assertEqual(body['integrity']['medical_priority'], 'URGENT')

    def test_future_meal_date_is_a_finding(self):
        body = self.client.post('/api/claims', json=self.claim_payload(meal_date=FUTURE)).json()
        codes = {f['code'] for f in body['integrity']['findings']}
        self.assertIn('future_meal_date', codes)

    def test_no_inspection_on_date_is_a_finding(self):
        body = self.client.post('/api/claims', json=self.claim_payload()).json()
        codes = {f['code'] for f in body['integrity']['findings']}
        self.assertIn('no_inspection_on_date', codes)
        self.assertIn('no_linked_supply_lot', codes)

    def test_every_finding_names_what_it_compared(self):
        body = self.client.post('/api/claims', json=self.claim_payload()).json()
        for finding in body['integrity']['findings']:
            self.assertIn('compared', finding)
            self.assertIsInstance(finding['compared'], list)

    def test_unknown_symptom_rejected(self):
        self.assertEqual(
            self.client.post('/api/claims', json=self.claim_payload(symptoms=['vibes'])).status_code, 422)

    def test_empty_symptoms_rejected(self):
        self.assertEqual(
            self.client.post('/api/claims', json=self.claim_payload(symptoms=[])).status_code, 422)

    def test_implausible_onset_rejected(self):
        self.assertEqual(
            self.client.post('/api/claims', json=self.claim_payload(onset_hours=0)).status_code, 422)

    def test_missing_contact_rejected(self):
        self.assertEqual(
            self.client.post('/api/claims', json=self.claim_payload(reporter_contact='')).status_code, 422)

    def test_unknown_kitchen_rejected(self):
        self.assertEqual(
            self.client.post('/api/claims', json=self.claim_payload(kitchen_id='KITCHEN-Z')).status_code, 422)


class ClaimTrace(LaneHarness):
    def setUp(self):
        super().setUp()
        self.inspection = self.make_inspection()
        self.lot = self.make_lot().json()
        self.client.patch(f"/api/supply/lots/{self.lot['lot_id']}", json={
            'role': 'SUPERVISOR', 'trace_to': [self.inspection['inspection_id']],
        })
        self.claim = self.client.post('/api/claims', json={
            'kitchen_id': 'KITCHEN-A', 'reporter_contact': '+62 812-3456-7890',
            'meal_date': TODAY, 'symptoms': ['nausea'], 'onset_hours:': None,
            'onset_hours': 6,
        }).json()

    def test_trace_resolves_to_supplier(self):
        trace = self.client.get(f"/api/claims/{self.claim['claim_id']}/trace?role=SUPERVISOR").json()
        self.assertEqual(len(trace['related_lots']), 1)
        self.assertEqual(trace['related_lots'][0]['supplier'], 'Warung Kita')
        self.assertEqual(trace['medical_priority'], 'URGENT')

    def test_trace_masks_contact(self):
        trace = self.client.get(f"/api/claims/{self.claim['claim_id']}/trace?role=SUPERVISOR").json()
        self.assertEqual(trace['contact_masked'], '*********7890')
        self.assertNotIn('contact_blind_index', trace)

    def test_out_of_scope_trace_is_404(self):
        self.make_inspection(kitchen='KITCHEN-B')
        other = self.client.post('/api/claims', json={
            'kitchen_id': 'KITCHEN-B', 'reporter_contact': '+62 800-0000',
            'meal_date': TODAY, 'symptoms': ['nausea'], 'onset_hours': 6,
        }).json()
        response = self.client.get(f"/api/claims/{other['claim_id']}/trace?role=CREW")
        self.assertEqual(response.status_code, 404)

    def test_escalation_requires_note(self):
        no_note = self.client.patch(f"/api/claims/{self.claim['claim_id']}",
                                    json={'role': 'SUPERVISOR', 'status': 'escalated'})
        self.assertEqual(no_note.status_code, 422)
        noted = self.client.patch(f"/api/claims/{self.claim['claim_id']}",
                                  json={'role': 'SUPERVISOR', 'status': 'escalated',
                                        'note': 'Sent to Puskesmas'})
        self.assertEqual(noted.status_code, 200)
        self.assertEqual(noted.json()['status'], 'escalated')

    def test_list_is_scoped(self):
        response = self.client.get('/api/claims?role=CREW').json()
        self.assertTrue(all(c['kitchen_id'] == 'KITCHEN-A' for c in response['claims']))

    def test_list_never_returns_blind_index(self):
        response = self.client.get('/api/claims?role=ADMIN').text
        self.assertNotIn('contact_blind_index', response)


if __name__ == '__main__':
    unittest.main()