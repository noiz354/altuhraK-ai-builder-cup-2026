"""Tuning-pipeline contracts: label rules, leakage-free splits, and parity
between training examples and live requests."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TRAINING = HERE.parent / "training"
for extra in (str(TRAINING), str(HERE.parent / "src"), str(HERE.parent.parent.parent.parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import dataset  # noqa: E402
import evaluate  # noqa: E402
import synth  # noqa: E402
import vertex  # noqa: E402


class LabelRules(unittest.TestCase):
    base = {'image': 'x.jpg', 'label': 'meal_complete', 'missing': [], 'plate_type': 'home_plate',
            'group_id': 'g1', 'source': 'field_crew'}

    def test_valid_row(self):
        self.assertEqual(dataset._check_row(self.base), [])

    def test_inconsistent_rows_rejected(self):
        cases = [
            {'label': 'missing_component', 'missing': []},
            {'label': 'meal_complete', 'missing': ['protein']},
            {'label': 'missing_component', 'missing': ['carbohydrate', 'protein', 'vegetable']},
            {'label': 'uncertain'},
            {'group_id': ''},
            {'plate_type': 'teacup'},
        ]
        for patch in cases:
            with self.subTest(patch=patch):
                self.assertTrue(dataset._check_row({**self.base, **patch}))


class PipelineEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = Path(cls.tmp.name) / 'data'
        cls.build = Path(cls.tmp.name) / 'build'
        synth.generate(cls.data, households=12, photos_per_household=3, seed=3)
        cls.report = dataset.load_and_validate(cls.data)
        cls.splits = dataset.split(cls.report.accepted, seed=1)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_no_group_in_two_splits(self):
        groups = {name: {e.group_id for e in rows} for name, rows in self.splits.items()}
        self.assertFalse(groups['train'] & groups['test'])
        self.assertFalse(groups['train'] & groups['validation'])
        self.assertFalse(groups['validation'] & groups['test'])
        self.assertEqual(sum(len(r) for r in self.splits.values()), len(self.report.accepted))

    def test_exact_duplicate_dropped(self):
        manifest = self.data / 'manifest.jsonl'
        first = manifest.read_text(encoding='utf-8').splitlines()[0]
        dup = Path(self.tmp.name) / 'dup'
        (dup / 'images').mkdir(parents=True)
        row = json.loads(first)
        (dup / row['image']).write_bytes((self.data / row['image']).read_bytes())
        row2 = {**row, 'group_id': 'other'}
        (dup / 'manifest.jsonl').write_text(json.dumps(row) + '\n' + json.dumps(row2) + '\n', encoding='utf-8')
        report = dataset.load_and_validate(dup)
        self.assertEqual(len(report.accepted), 1)
        self.assertEqual(report.duplicates[0]['kind'], 'exact')

    def test_path_traversal_rejected(self):
        bad = Path(self.tmp.name) / 'bad'
        bad.mkdir()
        row = {**LabelRules.base, 'image': '../data/manifest.jsonl'}
        (bad / 'manifest.jsonl').write_text(json.dumps(row) + '\n', encoding='utf-8')
        self.assertIn('escapes', dataset.load_and_validate(bad).rejected[0]['errors'][0])

    def test_export_matches_live_contract(self):
        out = vertex.export_split(self.splits['train'][:3], self.data, self.build, 'train', 'gs://b/p')
        line = json.loads(Path(out['file']).read_text(encoding='utf-8').splitlines()[0])
        user, model = line['contents']
        self.assertEqual(user['role'], 'user')
        self.assertTrue(user['parts'][1]['fileData']['fileUri'].startswith('gs://b/p/images/'))
        prompt = json.loads(user['parts'][0]['text'])
        self.assertEqual(set(prompt), {'task', 'schema', 'baseline_result', 'evidence', 'params', 'rules'})
        target = json.loads(model['parts'][0]['text'])
        # The target must satisfy the same contract the live validator enforces.
        self.assertEqual(target['evidence_ids'], [prompt['evidence'][0]['evidence_id']])
        self.assertIsNone(target['confidence_score'])
        self.assertEqual(target['needs_review'], target['predicted_label'] != 'meal_complete')

    def test_tuning_request_shape(self):
        body = vertex.tuning_request('base-model', 'gs://b/p/', 'n', 3, 'ADAPTER_SIZE_FOUR', None)
        self.assertEqual(body['supervisedTuningSpec']['trainingDatasetUri'], 'gs://b/p/train.jsonl')
        self.assertEqual(body['supervisedTuningSpec']['hyperParameters']['epochCount'], 3)


class Metrics(unittest.TestCase):
    def test_missing_component_recall(self):
        m = evaluate.metrics([('missing_component', 'missing_component'), ('missing_component', 'meal_complete'),
                              ('meal_complete', 'meal_complete'), ('uncertain', 'error')])
        self.assertEqual(m['missing_component_recall'], 0.5)
        self.assertEqual(m['accuracy'], 0.5)
        self.assertEqual(m['errors'], 1)


class TunedEndpointRouting(unittest.TestCase):
    def test_endpoint_url(self):
        import c05_gemini
        cfg = c05_gemini.GeminiConfig(provider='vertex', model='m', project='p', location='global',
                                      adc_present=True)
        old = os.environ.get('C05_GEMINI_ENDPOINT')
        os.environ['C05_GEMINI_ENDPOINT'] = 'projects/p/locations/us-central1/endpoints/123'
        c05_gemini._TOKEN_CACHE['p:global'] = ('tok', 9e18)
        try:
            url, headers, _ = c05_gemini.auth_headers(cfg)
        finally:
            c05_gemini._TOKEN_CACHE.pop('p:global', None)
            if old is None:
                os.environ.pop('C05_GEMINI_ENDPOINT')
            else:
                os.environ['C05_GEMINI_ENDPOINT'] = old
        self.assertEqual(url, 'https://us-central1-aiplatform.googleapis.com/v1/'
                              'projects/p/locations/us-central1/endpoints/123:generateContent')
        self.assertEqual(headers['Authorization'], 'Bearer tok')


if __name__ == '__main__':
    unittest.main()
