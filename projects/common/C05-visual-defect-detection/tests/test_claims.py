"""Illness-claim integrity contracts.

Locks the health-first rules: signals are explainable and cite claims, the
model cannot invent claims or accuse reporters, and an incident cannot be
closed as unsubstantiated without evidence and confirmed medical follow-up.
"""
import importlib.util
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import c05_claims  # noqa: E402


def _load_api():
    spec = importlib.util.spec_from_file_location("c05_api_claims", SRC / "c05_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WIB = timezone(timedelta(hours=7))


def _claim(cid, school, affected=1, onset_h=14, submitted_min=0, contact='081200000000', text='', **kw):
    day = date(2026, 10, 15)
    return {'claim_id': cid, 'incident_id': 'INC-KITCHEN-A-2026-10-15', 'kitchen_id': 'KITCHEN-A',
            'school_id': school, 'meal_date': day.isoformat(), 'reporter_type': 'parent',
            'contact_hash': c05_claims.contact_hash(contact), 'affected_count': affected,
            'symptoms': ['vomiting'], 'onset_at': datetime(2026, 10, 15, onset_h, 0, tzinfo=WIB).isoformat(),
            'sought_medical': kw.get('medical', False), 'hospitalized': kw.get('hospital', False),
            'description': text, 'photo': kw.get('photo'), 'channel': 'web_form',
            'submitted_at': (datetime(2026, 10, 15, 18, 0, tzinfo=WIB) + timedelta(minutes=submitted_min)).isoformat()}


SERVICE = [{'service_id': 's1', 'kitchen_id': 'KITCHEN-A', 'school_id': 'SDN-01', 'meal_date': '2026-10-15',
            'batch_id': 'B1', 'portions_served': 10, 'served_at': datetime(2026, 10, 15, 11, 30, tzinfo=WIB).isoformat()}]


class SignalRules(unittest.TestCase):
    def codes(self, claims):
        return {s['code'] for s in c05_claims.assess_incident(claims, SERVICE, [])['signals']}

    def test_plausible_cluster_has_no_integrity_signals(self):
        claims = [_claim(f'c{i}', 'SDN-01', contact=f'08120000000{i}', submitted_min=i * 40,
                         text=f'child {i} unwell') for i in range(4)]
        result = c05_claims.assess_incident(claims, SERVICE, [])
        self.assertEqual(result['signals'], [])
        self.assertEqual(result['integrity_level'], 'low')

    def test_affected_count_above_portions_served(self):
        claims = [_claim('a', 'SDN-01', affected=6, contact='0812000001'),
                  _claim('b', 'SDN-01', affected=6, contact='0812000002', submitted_min=60)]
        self.assertIn('CLAIMS_EXCEED_PORTIONS', self.codes(claims))

    def test_unserved_school_and_onset_before_meal(self):
        claims = [_claim('a', 'SDN-99'), _claim('b', 'SDN-01', onset_h=9, contact='0812000002', submitted_min=60)]
        self.assertEqual({'NO_SERVICE_RECORD', 'ONSET_BEFORE_MEAL'}, self.codes(claims))

    def test_contact_prefix_variants_are_the_same_phone(self):
        self.assertEqual(c05_claims.contact_hash('081299990003'), c05_claims.contact_hash('+62 812-9999-0003'))

    def test_templated_text_photo_and_burst(self):
        text = 'our children got severe food poisoning from the lunch today and must be compensated now'
        photo = {'sha256': 'a' * 64, 'ahash': 'ffc3c3818181c3ff'}
        claims = [_claim(f'c{i}', 'SDN-01', contact=f'08120000{i:04d}', submitted_min=i, text=text, photo=photo)
                  for i in range(5)]
        self.assertTrue({'TEMPLATED_TEXT', 'DUPLICATE_PHOTO', 'SUBMISSION_BURST'} <= self.codes(claims))

    def test_hospitalization_sets_urgent_regardless_of_signals(self):
        claims = [_claim('a', 'SDN-99', hospital=True, medical=True)]
        result = c05_claims.assess_incident(claims, SERVICE, [])
        self.assertEqual(result['health_priority'], 'URGENT')
        self.assertTrue(result['signals'])

    def test_redaction_removes_contact_details(self):
        out = c05_claims.redact('call me on 0812 3456 7890 or ibu@example.com')
        self.assertNotIn('3456', out)
        self.assertNotIn('example.com', out)


class ModelOutputGuards(unittest.TestCase):
    base = {'summary': 'Reports cluster at one school.', 'pattern_assessment': 'mixed',
            'observations': [{'text': 'Onset times fit the serving time.', 'claim_ids': ['a']}],
            'verification_steps': ['Check attendance.'], 'health_actions': ['Refer to Puskesmas.']}

    def test_valid_output_passes(self):
        self.assertEqual(c05_claims.validate_ai(self.base, {'a'})['pattern_assessment'], 'mixed')

    def test_fabricated_claim_id_rejected(self):
        bad = {**self.base, 'observations': [{'text': 'x', 'claim_ids': ['zzz']}]}
        with self.assertRaises(c05_claims.ClaimInvalid):
            c05_claims.validate_ai(bad, {'a'})

    def test_accusatory_language_rejected(self):
        with self.assertRaises(c05_claims.ClaimInvalid):
            c05_claims.validate_ai({**self.base, 'summary': 'These reports are a scam.'}, {'a'})


class ClaimRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from shared_mvp.testing import LocalClient
        cls._tmp = tempfile.TemporaryDirectory()
        cls.app = _load_api().create_app(str(Path(cls._tmp.name) / "claims.sqlite"))
        cls.client = LocalClient(cls.app)
        res = cls.client.post('/api/claims/demo-seed', json={'role': 'ADMIN'})
        assert res.status_code == 200, res.text
        cls.seed = res.json()

    @classmethod
    def tearDownClass(cls):
        cls.app.state.store.close()
        cls._tmp.cleanup()

    def incidents(self, role='ADMIN'):
        return self.client.get(f'/api/claims/incidents?role={role}').json()['incidents']

    def test_seed_produces_contrasting_incidents(self):
        self.assertGreater(self.seed['claims_loaded'], 40)
        scores = sorted(i['integrity_score'] for i in self.incidents())
        self.assertEqual(scores[0], 0)
        self.assertGreaterEqual(scores[-1], 50)

    def test_crew_cannot_see_claims(self):
        self.assertEqual(self.client.get('/api/claims/incidents?role=CREW').status_code, 403)

    def test_public_submission_hashes_contact(self):
        today = datetime.now(WIB).date()
        res = self.client.post('/api/claims', json={
            'kitchen_id': 'KITCHEN-B', 'school_id': 'sdn-12', 'meal_date': today.isoformat(),
            'reporter_type': 'parent', 'contact': '0812 1111 2222', 'affected_count': 1,
            'symptoms': ['nausea'], 'onset_at': datetime.now(timezone.utc).isoformat(),
            'description': 'call 081211112222'})
        self.assertEqual(res.status_code, 201, res.text)
        detail = self.client.get(f"/api/claims/incidents/{res.json()['incident_id']}?role=ADMIN").json()
        mine = next(c for c in detail['claims'] if c['claim_id'] == res.json()['claim_id'])
        self.assertNotIn('contact', mine)
        self.assertNotIn('contact_hash', mine)

    def test_ai_assessment_and_guarded_closure(self):
        target = max(self.incidents(), key=lambda i: i['integrity_score'])
        iid = target['incident_id']
        detail = self.client.get(f'/api/claims/incidents/{iid}?role=ADMIN').json()
        first = detail['claims'][0]['claim_id']
        self.app.state.claims_model = lambda prompt: {
            'summary': 'A small cluster fits the serving time; a larger wave conflicts with delivery records.',
            'pattern_assessment': 'mixed',
            'observations': [{'text': 'Earliest report fits the onset window.', 'claim_ids': [first]}],
            'verification_steps': ['Reconcile delivery manifest.'], 'health_actions': ['Refer all reporters.']}
        try:
            res = self.client.post(f'/api/claims/incidents/{iid}/assess', json={'role': 'SUPERVISOR'})
        finally:
            self.app.state.claims_model = None
        self.assertEqual(res.json()['ai']['inference_status'], 'INFERENCE_SUCCEEDED')
        # Model output never changes the deterministic score.
        self.assertEqual(res.json()['integrity_score'], target['integrity_score'])

        close = {'role': 'SUPERVISOR', 'status': 'CLOSED_UNSUBSTANTIATED', 'comment': 'Delivery records conflict.'}
        self.assertEqual(self.client.post(f'/api/claims/incidents/{iid}/decision', json=close).status_code, 403)
        close['role'] = 'ADMIN'
        if target['health_priority'] != 'ROUTINE':
            self.assertEqual(self.client.post(f'/api/claims/incidents/{iid}/decision', json=close).status_code, 409)
            close['health_followup_confirmed'] = True
        res = self.client.post(f'/api/claims/incidents/{iid}/decision', json=close)
        self.assertEqual(res.status_code, 200, res.text)
        again = self.client.post(f'/api/claims/incidents/{iid}/decision',
                                 json={'role': 'ADMIN', 'status': 'ESCALATED_HEALTH', 'comment': 'reopen attempt'})
        self.assertEqual(again.status_code, 409)
        events = [e['event'] for e in res.json()['audit']]
        self.assertIn('ai_assessment', events)
        self.assertIn('decision', events)

    def test_clean_incident_cannot_be_closed_unsubstantiated(self):
        clean = min(self.incidents(), key=lambda i: i['integrity_score'])
        self.assertEqual(clean['signals'], [])
        res = self.client.post(f"/api/claims/incidents/{clean['incident_id']}/decision",
                               json={'role': 'ADMIN', 'status': 'CLOSED_UNSUBSTANTIATED',
                                     'comment': 'no evidence at all', 'health_followup_confirmed': True})
        self.assertEqual(res.status_code, 409)

    def test_provider_failure_keeps_deterministic_view(self):
        iid = self.incidents()[0]['incident_id']

        def boom(prompt):
            raise c05_claims.ProviderUnavailable('provider_error', {'provider_called': True})
        self.app.state.claims_model = boom
        try:
            res = self.client.post(f'/api/claims/incidents/{iid}/assess', json={'role': 'ADMIN'})
        finally:
            self.app.state.claims_model = None
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['ai']['inference_status'], 'INFERENCE_FAILED')
        self.assertTrue(res.json()['next_steps'])

    def test_agent_answers_from_claim_records(self):
        res = self.client.post('/api/agent/chat', json={'role': 'ADMIN', 'question': 'Any poisoning claims?'})
        body = res.json()
        self.assertEqual(body['tool_calls'][0]['tool'], 'list_claim_incidents')
        self.assertIn('KITCHEN-A, meals of', body['answer'])


if __name__ == '__main__':
    unittest.main()
