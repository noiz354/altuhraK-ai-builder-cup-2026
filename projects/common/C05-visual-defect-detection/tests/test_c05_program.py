"""Integration tests for the menu, blind-labelling and dataset-metrics lane.

The load-bearing properties here are blinding, separation of duties, and gold immutability. If
any of them regress, every accuracy figure computed downstream becomes meaningless, so they are
asserted directly rather than inferred.

Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_program.py -q
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

SECRET = 'program-test-secret'
TODAY = '2026-10-18'


def png_bytes(width=400, height=320, colour='#88aa66') -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), colour).save(buffer, format='PNG')
    return buffer.getvalue()


class ProgramHarness(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {'C05_CONTACT_HMAC_SECRET': SECRET})
        self.env.start()
        self.temp = tempfile.TemporaryDirectory()
        from c05_bootstrap import create_app
        from shared_mvp.testing import LocalClient as TestClient
        self.app = create_app(str(Path(self.temp.name) / 'program.sqlite'))
        self.client = TestClient(self.app)
        self.app.state.rate_limiter.reset()
        self.addCleanup(self._close)

    def _close(self):
        self.env.stop()
        self.client.close()
        self.app.state.store.db.close()
        self.temp.cleanup()

    def make_inspection(self, colour='#88aa66', menu_components=None):
        payload = {
            'role': 'SUPERVISOR', 'kitchen_id': 'KITCHEN-A', 'shift_id': 'SHIFT-AM',
            'batch_id': 'BATCH-DEMO', 'manifest_version': 1, 'mime_type': 'image/png',
            'data_base64': base64.b64encode(png_bytes(colour=colour)).decode(),
            'idempotency_key': uuid.uuid4().hex,
        }
        response = self.client.post('/api/inspections', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        record = response.json()
        if menu_components:
            store = self.app.state.store
            record['menu_required_components'] = menu_components
            store.put('inspection', record['inspection_id'], record)
        return record

    def make_menu(self, menu_id='MBG-STD-01'):
        return self.client.post('/api/menus', json={
            'role': 'ADMIN', 'menu_id': menu_id, 'kitchen_id': 'KITCHEN-A',
            'required_components': ['carbohydrate', 'protein', 'vegetable'],
            'optional_components': ['fruit'],
        })


class Menus(ProgramHarness):
    def test_admin_creates_draft_menu(self):
        response = self.make_menu()
        self.assertEqual(response.status_code, 201, response.text)
        spec = response.json()
        self.assertEqual(spec['status'], 'draft')
        self.assertEqual(spec['version'], 1)

    def test_non_admin_cannot_create_menu(self):
        response = self.client.post('/api/menus', json={
            'role': 'SUPERVISOR', 'menu_id': 'X', 'kitchen_id': 'KITCHEN-A',
            'required_components': ['protein'],
        })
        self.assertEqual(response.status_code, 403)

    def test_version_increments_per_menu_id(self):
        self.make_menu()
        second = self.make_menu()
        self.assertEqual(second.json()['version'], 2)

    def test_bad_menu_id_rejected(self):
        response = self.client.post('/api/menus', json={
            'role': 'ADMIN', 'menu_id': 'bad id!', 'kitchen_id': 'KITCHEN-A',
            'required_components': ['protein'],
        })
        self.assertEqual(response.status_code, 422)

    def test_empty_required_components_rejected(self):
        response = self.client.post('/api/menus', json={
            'role': 'ADMIN', 'menu_id': 'X', 'kitchen_id': 'KITCHEN-A',
            'required_components': [],
        })
        self.assertEqual(response.status_code, 422)

    def test_approval_locks_the_spec(self):
        spec = self.make_menu().json()
        approved = self.client.post(f"/api/menus/{spec['menu_id']}/v/{spec['version']}/approve",
                                    json={'role': 'ADMIN'})
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()['status'], 'approved')
        again = self.client.post(f"/api/menus/{spec['menu_id']}/v/{spec['version']}/approve",
                                 json={'role': 'ADMIN'})
        self.assertEqual(again.status_code, 409, 'approved specifications are immutable')

    def test_only_admin_approves(self):
        spec = self.make_menu().json()
        response = self.client.post(f"/api/menus/{spec['menu_id']}/v/{spec['version']}/approve",
                                    json={'role': 'SUPERVISOR'})
        self.assertEqual(response.status_code, 403)

    def test_menu_read_is_scoped(self):
        spec = self.make_menu().json()
        self.assertEqual(
            self.client.get(f"/api/menus/{spec['menu_id']}/v/{spec['version']}?role=CREW").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/menus/NOPE/v/1?role=ADMIN").status_code, 404)

    def test_approval_is_audited(self):
        spec = self.make_menu().json()
        self.client.post(f"/api/menus/{spec['menu_id']}/v/{spec['version']}/approve", json={'role': 'ADMIN'})
        events = [e['event'] for e in self.app.state.store.history(f"menu:{spec['menu_id']}:v{spec['version']}")]
        self.assertIn('menu_approved', events)


class BlindLabelling(ProgramHarness):
    def test_queue_hides_model_output(self):
        record = self.make_inspection()
        run = self.client.post(f"/api/inspections/{record['inspection_id']}/run",
                               json={'role': 'SUPERVISOR', 'mode': 'baseline'})
        self.assertEqual(run.status_code, 200, run.text)
        queue = self.client.get('/api/annotations/queue?role=SUPERVISOR').json()
        self.assertEqual(queue['count'], 1)
        entry = queue['queue'][0]
        for leaked in ('prediction', 'predicted_label', 'confidence_score', 'regions', 'inference_status'):
            self.assertNotIn(leaked, entry, f'queue leaks model output via {leaked}')
        self.assertIn('image_sha256', entry)

    def test_crew_cannot_annotate(self):
        record = self.make_inspection()
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'CREW', 'annotator_id': 'ann-1', 'image_level_label': 'meal_complete',
        })
        self.assertEqual(response.status_code, 403)

    def test_capturing_actor_may_not_annotate_own_image(self):
        record = self.make_inspection()
        store = self.app.state.store
        self.assertEqual(store.get('inspection', record['inspection_id'])['actor_id'], 'supervisor-demo')
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'supervisor-demo', 'image_level_label': 'meal_complete',
        })
        self.assertEqual(response.status_code, 422)

    def test_annotator_may_not_label_twice(self):
        record = self.make_inspection()
        path = f"/api/inspections/{record['inspection_id']}/annotations"
        first = self.client.post(path, json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'meal_complete'})
        self.assertEqual(first.status_code, 201, first.text)
        second = self.client.post(path, json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'meal_complete'})
        self.assertEqual(second.status_code, 409)

    def test_missing_component_requires_a_named_component(self):
        record = self.make_inspection(menu_components=['carbohydrate', 'protein', 'vegetable'])
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'missing_component',
        })
        self.assertEqual(response.status_code, 422)

    def test_missing_component_must_reference_the_menu(self):
        record = self.make_inspection(menu_components=['carbohydrate', 'protein', 'vegetable'])
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'missing_component',
            'missing_components': ['dessert'],
        })
        self.assertEqual(response.status_code, 422)

    def test_uncertain_requires_a_reason(self):
        record = self.make_inspection()
        bad = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'uncertain'})
        self.assertEqual(bad.status_code, 422)
        good = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'uncertain',
            'uncertainty_reason': 'poor_lighting'})
        self.assertEqual(good.status_code, 201, good.text)

    def test_annotated_record_leaves_the_queue(self):
        record = self.make_inspection()
        self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'meal_complete'})
        queue = self.client.get('/api/annotations/queue?role=SUPERVISOR').json()
        self.assertEqual(queue['count'], 0)


class Adjudication(ProgramHarness):
    def _two_labels(self, second_label='meal_complete'):
        record = self.make_inspection()
        path = f"/api/inspections/{record['inspection_id']}/annotations"
        self.client.post(path, json={'role': 'SUPERVISOR', 'annotator_id': 'ann-1',
                                     'image_level_label': 'meal_complete'})
        second = {'role': 'SUPERVISOR', 'annotator_id': 'ann-2',
                  'image_level_label': second_label}
        if second_label == 'uncertain':
            # `uncertain` is only a valid label with a reason, otherwise the
            # annotation is rejected and adjudication would see a single label.
            second['uncertainty_reason'] = 'poor_lighting'
        response = self.client.post(path, json=second)
        self.assertEqual(response.status_code, 201, response.text)
        return record

    def test_needs_two_independent_labels(self):
        record = self.make_inspection()
        self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-1', 'image_level_label': 'meal_complete'})
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate",
                                    json={'role': 'ADMIN'})
        self.assertEqual(response.status_code, 409)

    def test_agreement_produces_that_label(self):
        record = self._two_labels('meal_complete')
        gold = self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate",
                                json={'role': 'ADMIN'})
        self.assertEqual(gold.status_code, 201, gold.text)
        self.assertEqual(gold.json()['image_level_label'], 'meal_complete')
        self.assertFalse(gold.json()['was_contested'])

    def test_disagreement_is_recorded_as_contested(self):
        record = self._two_labels('uncertain')
        gold = self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate",
                                json={'role': 'ADMIN', 'note': 're-ran capture'}).json()
        self.assertTrue(gold['was_contested'])
        self.assertEqual(gold['image_level_label'], 'uncertain')
        self.assertEqual(sorted(gold['candidate_labels']), ['meal_complete', 'uncertain'])

    def test_only_admin_adjudicates(self):
        record = self._two_labels()
        response = self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate",
                                    json={'role': 'SUPERVISOR'})
        self.assertEqual(response.status_code, 403)

    def test_gold_is_immutable(self):
        record = self._two_labels()
        self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate", json={'role': 'ADMIN'})
        again = self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate",
                                 json={'role': 'ADMIN'})
        self.assertEqual(again.status_code, 409)

    def test_gold_blocks_further_annotation(self):
        record = self._two_labels()
        self.client.post(f"/api/inspections/{record['inspection_id']}/adjudicate", json={'role': 'ADMIN'})
        blocked = self.client.post(f"/api/inspections/{record['inspection_id']}/annotations", json={
            'role': 'SUPERVISOR', 'annotator_id': 'ann-3', 'image_level_label': 'meal_complete'})
        self.assertEqual(blocked.status_code, 409)


class DatasetMetrics(ProgramHarness):
    def test_requires_admin(self):
        self.assertEqual(self.client.get('/api/data/overview?role=SUPERVISOR').status_code, 403)

    def test_empty_dataset_reports_null_not_zero_rates(self):
        result = self.client.get('/api/data/overview?role=ADMIN').json()
        coverage = result['annotation_coverage']
        self.assertEqual(coverage['count'], 0)
        self.assertEqual(coverage['of'], 0)
        self.assertIsNone(coverage['rate'], 'a rate over an empty set must be null, not 0.0')

    def test_identical_images_are_flagged_as_duplicates(self):
        self.make_inspection(colour='#112233')
        self.make_inspection(colour='#112233')
        result = self.client.get('/api/data/overview?role=ADMIN').json()
        self.assertEqual(result['dataset']['exact_duplicate_hashes'], 1)
        self.assertEqual(len(result['dataset']['exact_duplicate_inspection_ids']), 2)
        self.assertFalse(result['tuning_readiness']['ready'])
        self.assertTrue(any('duplicate' in b for b in result['tuning_readiness']['blocked_by']))

    def test_tuning_readiness_states_no_job_is_implemented(self):
        result = self.client.get('/api/data/overview?role=ADMIN').json()
        self.assertIn('No Vertex AI tuning job is implemented',
                      result['tuning_readiness']['note'])

    def test_agreement_is_reported_between_annotators_not_against_model(self):
        record = self.make_inspection()
        path = f"/api/inspections/{record['inspection_id']}/annotations"
        self.client.post(path, json={'role': 'SUPERVISOR', 'annotator_id': 'ann-1',
                                     'image_level_label': 'meal_complete'})
        self.client.post(path, json={'role': 'SUPERVISOR', 'annotator_id': 'ann-2',
                                     'image_level_label': 'meal_complete'})
        result = self.client.get('/api/data/overview?role=ADMIN').json()
        agreement = result['inter_annotator']
        self.assertEqual(agreement['full_agreement']['count'], 1)
        self.assertEqual(agreement['full_agreement']['of'], 1)
        self.assertIn('not against the model', agreement['note'])


if __name__ == '__main__':
    unittest.main()