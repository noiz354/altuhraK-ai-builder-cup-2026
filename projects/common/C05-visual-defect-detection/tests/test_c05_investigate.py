"""Tests for the seven clauses that make an incident summary "grounded".

Each test names the clause it enforces. A summary that reads well but violates any clause is a
failure, because the deck claims the summary "cannot change the score".

Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_investigate.py -q
"""
import base64
import io
import json
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

from c05_investigate import strip_decision_language  # noqa: E402

SECRET = 'investigate-test-secret'
TODAY = '2026-10-18'


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', (400, 320), '#88aa66').save(buffer, format='PNG')
    return buffer.getvalue()


class InvestigateHarness(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'C05_CONTACT_HMAC_SECRET': SECRET})
        self.env.start()
        self.temp = tempfile.TemporaryDirectory()
        from c05_bootstrap import create_app
        from shared_mvp.testing import LocalClient as TestClient
        self.app = create_app(str(Path(self.temp.name) / 'inv.sqlite'))
        self.client = TestClient(self.app)
        self.store = self.app.state.store
        self.app.state.rate_limiter.reset()
        self.addCleanup(self._close)

    def _close(self):
        self.env.stop()
        self.client.close()
        self.store.db.close()
        self.temp.cleanup()

    def post(self, path, body):
        import urllib.request
        request = urllib.request.Request(
            f'http://test{path}', data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'})
        # go through the client instead of urllib so routing and guards apply
        return self.client.post(path, json=body)

    def seed_warm_lot(self, kitchen='KITCHEN-A', supplier='Warung Kita'):
        return self.post('/api/supply/lots', {
            'role': 'SUPERVISOR', 'kitchen_id': kitchen, 'ingredient': 'Chicken',
            'supplier': supplier, 'origin': 'Bogor', 'travel_time_min': 145,
            'arrival_temp_c': 11.5, 'price_per_unit': 55000, 'quantity': 40,
            'received_at': f'{TODAY}T06:00:00+00:00',
        }).json()

    def seed_inspection(self, kitchen='KITCHEN-A', review=None):
        record = self.post('/api/inspections', {
            'role': 'SUPERVISOR', 'kitchen_id': kitchen, 'shift_id': 'SHIFT-AM',
            'batch_id': 'B', 'manifest_version': 1, 'mime_type': 'image/png',
            'data_base64': base64.b64encode(png_bytes()).decode(),
            'idempotency_key': uuid.uuid4().hex,
        }).json()
        if review:
            record['review_status'] = review
            self.store.put('inspection', record['inspection_id'], record)
        return record

    def investigate(self, kitchen='KITCHEN-A', role='SUPERVISOR'):
        return self.post('/api/agent/investigate', {'role': role, 'kitchen_id': kitchen})


class Clause1ScopedSources(InvestigateHarness):
    def test_rejects_kitchen_outside_scope(self):
        response = self.investigate(kitchen='KITCHEN-C')
        self.assertEqual(response.status_code, 403)

    def test_ignores_other_kitchen_records(self):
        self.seed_warm_lot(kitchen='KITCHEN-B', supplier='Supplier B')
        result = self.investigate(kitchen='KITCHEN-A').json()
        self.assertEqual(result['fact_count'], 0, 'KITCHEN-B data must not reach the KITCHEN-A summary')
        self.assertNotIn('Supplier B', result['summary'])

    def test_crew_sees_only_its_own_kitchen(self):
        self.seed_warm_lot(kitchen='KITCHEN-B', supplier='Supplier B')
        result = self.investigate(kitchen='KITCHEN-A', role='CREW').json()
        self.assertEqual(result['fact_count'], 0)


class Clause23SourcesAreShown(InvestigateHarness):
    def test_every_fact_has_a_source(self):
        self.seed_warm_lot()
        result = self.investigate().json()
        self.assertGreater(result['fact_count'], 0)
        self.assertEqual(result['source_count'], result['fact_count'])

    def test_source_entries_name_kind_id_and_field(self):
        self.seed_warm_lot()
        result = self.investigate().json()
        for source in result['sources']:
            self.assertIn(source['kind'], {'supply_lot', 'inspection', 'claim',
                                           'delivery_verification'})
            self.assertTrue(source['id'])
            self.assertTrue(source['field'])
            self.assertIn('supporting_record_count', source)

    def test_empty_kitchen_yields_zero_sources_not_invented_ones(self):
        result = self.investigate().json()
        self.assertEqual(result['fact_count'], 0)
        self.assertEqual(result['source_count'], 0)
        self.assertIn('No cross-lane conflicts', result['summary'])


class Clause4NoMutation(InvestigateHarness):
    def _snapshot(self):
        state = {}
        for kind in ('inspection', 'supply_lot', 'claim', 'delivery_verification'):
            state[kind] = json.dumps(sorted(self.store.list_kind(kind),
                                            key=lambda r: json.dumps(r, sort_keys=True)), sort_keys=True)
        return state

    def test_investigation_changes_no_business_record(self):
        self.seed_warm_lot()
        inspection = self.seed_inspection(review='REVIEW_PENDING')
        before = self._snapshot()
        result = self.investigate()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self._snapshot(), before,
                         'investigation mutated a record outside its own audit session')

    def test_response_declares_it_mutated_nothing(self):
        self.investigate()
        self.assertEqual(self.investigate().json()['mutated_records'], [])

    def test_only_the_audit_session_is_written(self):
        self.investigate()
        self.assertEqual(len(self.store.list_kind('agent_investigation')), 1)


class Clause5NoDecisionLanguage(InvestigateHarness):
    def test_stripper_removes_approval_language(self):
        cleaned, hits = strip_decision_language('The batch should be approved and closed.')
        self.assertNotIn('approved', cleaned.lower())
        self.assertNotIn('closed', cleaned.lower())
        self.assertTrue(hits)

    def test_stripper_removes_safety_language(self):
        cleaned, _ = strip_decision_language('This meal is safe to serve.')
        self.assertNotIn('safe to serve', cleaned.lower())

    def test_summary_contains_no_decision_words(self):
        self.seed_warm_lot()
        inspection = self.seed_inspection(review='REJECTED')
        self.post('/api/claims', {
            'kitchen_id': 'KITCHEN-A', 'reporter_contact': '+62 812-3456-7890',
            'meal_date': TODAY, 'symptoms': ['nausea'], 'onset_hours': 6,
        })
        summary = self.investigate().json()['summary'].lower()
        for banned in ('approve', 'reject', 'close the case', 'safe to'):
            self.assertNotIn(banned, summary, f'summary leaked decision word {banned!r}')

    def test_medical_priority_is_never_lowered(self):
        self.seed_warm_lot()
        self.post('/api/claims', {
            'kitchen_id': 'KITCHEN-A', 'reporter_contact': '+62 800-1111',
            'meal_date': TODAY, 'symptoms': ['fever'], 'onset_hours': 6,
        })
        self.assertEqual(self.investigate().json()['medical_priority'], 'URGENT')


class Clause6CountsMatchCitations(InvestigateHarness):
    def test_lot_count_matches_source_record_count(self):
        self.seed_warm_lot()
        self.seed_warm_lot(supplier='Warung Dua')
        result = self.investigate().json()
        warm = [s for s in result['sources'] if s['field'] == 'arrival_temp_c']
        self.assertEqual(len(warm), 1)
        self.assertEqual(warm[0]['supporting_record_count'], 2)
        self.assertIn('2 ingredient lot(s)', result['summary'])

    def test_conflict_pairs_are_listed_and_counted(self):
        lot = self.seed_warm_lot()
        inspection = self.seed_inspection(review='REJECTED')
        self.post(f"/api/supply/lots/{lot['lot_id']}",
                  {'role': 'SUPERVISOR', 'trace_to': [inspection['inspection_id']]})
        self.post('/api/claims', {
            'kitchen_id': 'KITCHEN-A', 'reporter_contact': '+62 812-9999-0000',
            'meal_date': TODAY, 'symptoms': ['nausea'], 'onset_hours': 6,
        })
        result = self.investigate().json()
        self.assertTrue(result['conflict_pairs'])
        self.assertIn('illness report(s) overlap', result['summary'])


class Clause7ProviderFailure(InvestigateHarness):
    def test_provider_unavailable_still_returns_computed_facts(self):
        self.seed_warm_lot()
        result = self.post('/api/agent/investigate', {
            'role': 'SUPERVISOR', 'kitchen_id': 'KITCHEN-A', 'use_provider': True,
        }).json()
        self.assertEqual(result['provider_used'], True)
        self.assertIn('no model narration was attempted', result['summary'].lower())
        self.assertGreater(result['fact_count'], 0, 'facts must survive provider failure')

    def test_summary_is_never_empty(self):
        self.investigate()
        self.investigate()
        for row in self.store.list_kind('agent_investigation'):
            self.assertTrue(row['summary'].strip())


class RunsListing(InvestigateHarness):
    def test_runs_are_scoped(self):
        self.seed_warm_lot(kitchen='KITCHEN-A')
        self.investigate(kitchen='KITCHEN-A')
        all_runs = self.client.get('/api/agent/runs?role=ADMIN').json()
        self.assertGreaterEqual(all_runs['count'], 1)
        crew_runs = self.client.get('/api/agent/runs?role=CREW&kitchen_id=KITCHEN-B').json()
        self.assertEqual(crew_runs['count'], 0)


if __name__ == '__main__':
    unittest.main()