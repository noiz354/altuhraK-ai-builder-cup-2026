"""Ingredient traceability and supply-insight contracts.

Locks the rules: checks are deterministic and cite lots, a meal date traces
back to its lots and suppliers, the model cannot cite lots or suppliers that
do not exist or declare food safe, and the API keeps kitchen scope.
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

import c05_supply  # noqa: E402

TODAY = date(2026, 10, 17)
WIB = timezone(timedelta(hours=7))
SUP = {'supplier_id': 'S1', 'name': 'Test Farm', 'type': 'farm', 'location': 'Here', 'distance_km': 10,
       'cold_chain': True, 'certifications': []}


def _lot(**kw):
    base = {'lot_id': 'L1', 'kitchen_id': 'KITCHEN-A', 'ingredient': 'chicken', 'supplier_id': 'S1',
            'quantity': 10.0, 'unit': 'kg', 'unit_price': 38000, 'arrival_temp_c': 3.0,
            'dispatched_at': datetime(2026, 10, 17, 5, 0, tzinfo=WIB).isoformat(),
            'received_at': datetime(2026, 10, 17, 6, 0, tzinfo=WIB).isoformat(), 'promised_at': None,
            'use_by': '2026-10-18', 'receiving_status': 'ACCEPTED', 'receiving_note': '',
            'used_in': [{'meal_date': '2026-10-17', 'batch_id': 'B', 'qty': 10.0}]}
    base.update(kw)
    return base


def codes(lot, sup=SUP):
    return {f['code'] for f in c05_supply.lot_flags(lot, sup, TODAY)}


class LotChecks(unittest.TestCase):
    def test_clean_chilled_lot_has_no_flags(self):
        self.assertEqual(codes(_lot()), set())

    def test_warm_chicken_is_a_food_safety_flag(self):
        self.assertIn('TEMP_ABOVE_LIMIT', codes(_lot(arrival_temp_c=9.0)))

    def test_no_cold_chain_and_long_transit(self):
        lot = _lot(dispatched_at=datetime(2026, 10, 17, 0, 0, tzinfo=WIB).isoformat())
        self.assertEqual(codes(lot, {**SUP, 'cold_chain': False}) & {'NO_COLD_CHAIN', 'LONG_TRANSIT'},
                         {'NO_COLD_CHAIN', 'LONG_TRANSIT'})

    def test_price_against_reference(self):
        self.assertIn('PRICE_ABOVE_REFERENCE', codes(_lot(unit_price=46000)))
        self.assertIn('PRICE_BELOW_REFERENCE', codes(_lot(unit_price=28000)))

    def test_expired_stock_left_on_the_shelf(self):
        self.assertIn('EXPIRED_IN_STOCK', codes(_lot(use_by='2026-10-16', used_in=[])))

    def test_rejected_lot_that_was_cooked(self):
        self.assertIn('REJECTED_BUT_USED', codes(_lot(receiving_status='REJECTED')))

    def test_chilled_delivery_needs_a_temperature(self):
        payload = {**_lot(arrival_temp_c=None), 'lot_id': None}
        with self.assertRaises(c05_supply.SupplyInvalid):
            c05_supply.normalize_lot(payload, {'S1': SUP})


class DemoStory(unittest.TestCase):
    def setUp(self):
        sups, self.lots, self.batches = c05_supply.demo_supply(TODAY)
        self.sups = {s['supplier_id']: s for s in sups}

    def test_lot_ids_are_unique(self):
        ids = [l['lot_id'] for l in self.lots]
        self.assertEqual(len(ids), len(set(ids)))

    def test_outbreak_day_traces_to_warm_chicken(self):
        result = c05_supply.trace('KITCHEN-A', (TODAY - timedelta(days=1)).isoformat(),
                                  self.lots, self.sups, self.batches, TODAY)
        first = result['lots'][0]
        self.assertEqual(first['ingredient'], 'chicken')
        self.assertEqual(first['supplier']['supplier_id'], 'SUP-03')
        self.assertIn('TEMP_ABOVE_LIMIT', {f['code'] for f in first['flags']})

    def test_safety_insights_rank_first(self):
        result = c05_supply.analyze('KITCHEN-A', self.lots, self.sups, self.batches, TODAY)
        self.assertEqual(result['insights'][0]['severity'], 'high')
        codes = [i['code'] for i in result['insights']]
        self.assertIn('PRICE_RISING', codes)
        self.assertIn('LOW_STOCK', codes)
        self.assertGreater(result['kpis']['cost_per_portion_idr'], 0)


class ModelGuard(unittest.TestCase):
    def test_rejects_unknown_ids_and_safety_claims(self):
        good = {'summary': 'Chicken arrived warm.', 'insights': [
            {'category': 'food_safety', 'title': 't', 'detail': 'd', 'action': 'a', 'lot_ids': ['L1'], 'supplier_ids': ['S1']}]}
        self.assertEqual(len(c05_supply.validate_ai(good, {'L1'}, {'S1'})['insights']), 1)
        with self.assertRaises(c05_supply.SupplyInvalid):
            c05_supply.validate_ai({**good, 'insights': [{**good['insights'][0], 'lot_ids': ['L9']}]}, {'L1'}, {'S1'})
        with self.assertRaises(c05_supply.SupplyInvalid):
            c05_supply.validate_ai({**good, 'summary': 'The food is safe to serve.'}, {'L1'}, {'S1'})


class SupplyApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from shared_mvp.testing import LocalClient
        cls._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        spec = importlib.util.spec_from_file_location("c05_api_supply", SRC / "c05_api.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.app = mod.create_app(str(Path(cls._tmp.name) / "supply.sqlite"))
        cls.client = LocalClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_overview_autoseeds_and_respects_scope(self):
        res = self.client.get('/api/supply/overview?role=SUPERVISOR&kitchen_id=KITCHEN-A')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()['insights'])
        self.assertEqual(self.client.get('/api/supply/overview?role=CREW&kitchen_id=KITCHEN-B').status_code, 403)

    def test_outbreak_incident_traces_to_warm_chicken(self):
        self.assertEqual(self.client.post('/api/claims/demo-seed', json={'role': 'ADMIN'}).status_code, 200)
        served = [s for s in self.app.state.store.list_kind('service_record') if s['kitchen_id'] == 'KITCHEN-A']
        outbreak_day = max(s['meal_date'] for s in served)
        res = self.client.get(f'/api/supply/trace?role=SUPERVISOR&kitchen_id=KITCHEN-A&meal_date={outbreak_day}')
        chicken = [l for l in res.json()['lots'] if l['ingredient'] == 'chicken']
        self.assertEqual(chicken[0]['supplier']['supplier_id'], 'SUP-03')
        self.assertIn('TEMP_ABOVE_LIMIT', {f['code'] for f in chicken[0]['flags']})

    def test_record_delivery_returns_flags(self):
        now = datetime.now(WIB)
        res = self.client.post('/api/supply/lots', json={
            'role': 'CREW', 'kitchen_id': 'KITCHEN-A', 'ingredient': 'chicken', 'supplier_id': 'SUP-03',
            'quantity': 20, 'unit_price': 30000, 'arrival_temp_c': 9,
            'dispatched_at': (now - timedelta(hours=5)).isoformat(), 'received_at': now.isoformat(),
            'use_by': (now.date() + timedelta(days=1)).isoformat()})
        self.assertEqual(res.status_code, 201, res.text)
        self.assertIn('TEMP_ABOVE_LIMIT', {f['code'] for f in res.json()['flags']})

    def test_insights_use_model_when_valid_and_fall_back_when_not(self):
        self.app.state.supply_model = lambda prompt: {'summary': 'Warm chicken from a distant trader is the top risk.',
                                                      'insights': [{'category': 'food_safety', 'title': 'Warm chicken',
                                                                    'detail': 'd', 'action': 'a', 'lot_ids': [],
                                                                    'supplier_ids': ['SUP-03']}]}
        try:
            res = self.client.post('/api/supply/insights', json={'role': 'SUPERVISOR', 'kitchen_id': 'KITCHEN-A'})
            self.assertEqual(res.json()['ai']['inference_status'], 'INFERENCE_SUCCEEDED')
            self.app.state.supply_model = lambda prompt: {'summary': 'x', 'insights': [
                {'category': 'cost', 'title': 't', 'detail': 'd', 'action': 'a', 'supplier_ids': ['SUP-99']}]}
            res = self.client.post('/api/supply/insights', json={'role': 'ADMIN', 'kitchen_id': 'KITCHEN-A'})
            self.assertEqual(res.json()['ai']['inference_status'], 'INFERENCE_FAILED')
            self.assertTrue(res.json()['insights'])  # deterministic insights still stand
        finally:
            self.app.state.supply_model = None
        self.assertEqual(self.client.post('/api/supply/insights',
                                          json={'role': 'CREW', 'kitchen_id': 'KITCHEN-A'}).status_code, 403)


if __name__ == '__main__':
    unittest.main()
