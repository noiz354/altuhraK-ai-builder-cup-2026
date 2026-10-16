"""Execute one project's domain and complete local HTTP workflow, sequentially."""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared_mvp.testing import LocalClient as TestClient
from shared_mvp.app import create_app, load, locate
from shared_mvp.domain import evidence_refs
from shared_mvp.provider import ProviderFailure


def suite_for(pid):
    project = locate(pid)
    checks = load(project / 'tests' / 'acceptance.py', f'checks_{pid}')

    class MVPTests(unittest.TestCase):
        def setUp(self):
            self.temp = tempfile.TemporaryDirectory()
            self.app = create_app(pid, str(Path(self.temp.name) / 'local.sqlite'))
            self.client = TestClient(self.app)
            self.sample = self.app.state.fixture.sample()

        def tearDown(self):
            self.client.close()
            self.app.state.store.db.close()
            self.temp.cleanup()

        def execute(self, fixture=None, mode='baseline', expected_http=None, client=None):
            client = client or self.client
            fixture = fixture or deepcopy(self.sample)
            imported = client.post('/api/datasets', json={'project_id': pid, 'data': fixture['data']})
            if imported.status_code != 201:
                if expected_http:
                    self.assertEqual(imported.status_code, expected_http, imported.text)
                    return imported.status_code
                self.fail(imported.text)
            started = client.post('/api/runs', json={'dataset_id': imported.json()['dataset_id'],
                                                   'mode': mode, 'params': fixture['params']})
            if expected_http:
                self.assertEqual(started.status_code, expected_http, started.text)
                return started.status_code
            self.assertEqual(started.status_code, 202, started.text)
            run = client.get('/api/runs/' + started.json()['run_id']).json()
            self.assertIn(run['state'], {'completed', 'partial'}, run)
            self.assertIsNotNone(run['baseline_result'])
            return run

        def test_domain_happy(self):
            checks.happy(self, self.execute())

        def test_domain_edges(self):
            checks.edges(self, self.execute, deepcopy(self.sample))

        def test_baseline_reproducible_and_cited(self):
            a, b = self.execute(), self.execute()
            self.assertEqual(a['baseline_result'], b['baseline_result'])
            self.assertFalse(a['usage']['provider_called'])
            self.assertEqual(a['usage']['input_tokens'], 0)
            self.assertTrue(evidence_refs(a['baseline_result']) <= {e['evidence_id'] for e in a['evidence']})

        def test_review_export_edit_and_stale_review(self):
            run = self.execute()
            url = '/api/runs/' + run['run_id']
            self.assertEqual(self.client.get(url + '/export').status_code, 409)
            self.assertEqual(self.client.post(url + '/reviews', json={'expected_revision': 1, 'decision': 'approve', 'actor': 'forged'}).status_code, 422)
            self.assertEqual(self.client.post(url + '/reviews', json={'expected_revision': 1, 'decision': 'approve'}).status_code, 201)
            self.assertEqual(self.client.get(url + '/export').status_code, 200)
            edited = self.client.patch(url + '/draft', json={'expected_revision': 1, 'draft': run['draft']})
            self.assertEqual(edited.status_code, 200, edited.text)
            self.assertEqual(edited.json()['revision'], 2)
            self.assertEqual(self.client.get(url + '/export').status_code, 409)
            self.assertEqual(self.client.post(url + '/reviews', json={'expected_revision': 1, 'decision': 'approve'}).status_code, 409)
            self.assertEqual(self.client.patch(url + '/draft', json={'expected_revision': 1, 'draft': run['draft']}).status_code, 409)
            self.assertEqual(self.client.post(url + '/reviews', json={'expected_revision': 2, 'decision': 'reject'}).status_code, 201)
            self.assertEqual(self.client.get(url + '/export').status_code, 409)

        def test_strict_input(self):
            bad = deepcopy(self.sample['data'])
            bad['unexpected'] = 'ignore instructions'
            self.assertEqual(self.client.post('/api/datasets', json={'project_id': pid, 'data': bad}).status_code, 422)
            for collection, rows in self.sample['data'].items():
                if isinstance(rows, list) and rows:
                    bad = deepcopy(self.sample['data'])
                    bad[collection].append(deepcopy(rows[0]))
                    self.assertEqual(self.client.post('/api/datasets', json={'project_id': pid, 'data': bad}).status_code, 422)
                    break
            self.assertEqual(self.client.post('/api/datasets', content='{').status_code, 400)
            self.assertEqual(self.client.post('/api/datasets', content=b' ' * (2 * 1024 * 1024 + 1)).status_code, 413)

        def test_unconfigured_provider_keeps_baseline(self):
            # Temporarily hide credentials without reading or logging their values.
            saved = os.environ.pop('GEMINI_API_KEY', None)
            try:
                run = self.execute(mode='ai')
                self.assertEqual(run['state'], 'partial')
                self.assertIn(run['status'], {'provider_unavailable', 'context_limit', 'insufficient_evidence'})
                self.assertIsNone(run['ai_result'])
                self.assertEqual(run['draft'], run['baseline_result'])
            finally:
                if saved is not None:
                    os.environ['GEMINI_API_KEY'] = saved

        def test_provider_adapter_and_invalid_output(self):
            seen = []
            def mocked(prompt):
                seen.append(prompt)
                return prompt['baseline_result']
            mockapp = create_app(pid, str(Path(self.temp.name) / 'mock.sqlite'), mocked)
            with TestClient(mockapp) as client:
                run = self.execute(mode='ai', client=client)
                if run['status'] == 'context_limit':
                    self.assertEqual(run['state'], 'partial')
                else:
                    self.assertEqual(run['usage']['model_id'], 'TEST_ADAPTER')
                    self.assertFalse(run['usage']['provider_called'])
                    self.assertEqual(run['ai_result'], run['baseline_result'])
                    payload = json.dumps(seen)
                    self.assertNotIn('is_fraud', payload)
                    self.assertNotIn('is_laundering', payload)
                    self.assertNotIn('Is Laundering', payload)
            mockapp.state.store.db.close()
            badapp = create_app(pid, str(Path(self.temp.name) / 'bad.sqlite'), lambda prompt: {'fake': 'data'})
            with TestClient(badapp) as client:
                bad = self.execute(mode='ai', client=client)
                self.assertEqual(bad['state'], 'partial')
                self.assertIn(bad['status'], {'invalid_model_output', 'context_limit'})
                self.assertEqual(bad['draft'], bad['baseline_result'])
            badapp.state.store.db.close()

        def test_authorization_store_and_console(self):
            self.assertEqual(self.client.get('/').status_code, 200)
            self.assertEqual(self.client.get('/ui/app.js').status_code, 200)
            self.assertEqual(self.client.get('/api/fixture').status_code, 200)
            self.assertEqual(self.client.get('/health').json()['project_id'], pid)
            self.assertEqual(self.client.get('/api/runs/missing').status_code, 404)
            self.assertEqual(self.client.post('/api/runs', json={'dataset_id': 'missing', 'mode': 'baseline', 'params': self.sample['params']}).status_code, 404)
            self.assertEqual(self.client.post('/api/datasets', json={'project_id': pid, 'data': self.sample['data']}, headers={'Origin': 'https://evil.test'}).status_code, 403)
            self.assertEqual(self.client.get('/health', headers={'Host': 'evil.test'}).status_code, 403)
            run = self.execute()
            reopened = create_app(pid, str(Path(self.temp.name) / 'local.sqlite'))
            with TestClient(reopened) as replay:
                self.assertEqual(replay.get('/api/runs/' + run['run_id']).json()['baseline_result'], run['baseline_result'])
            reopened.state.store.db.close()
            self.assertGreaterEqual(len(self.client.get('/api/runs/' + run['run_id'] + '/audit').json()), 2)
            import sqlite3
            with self.assertRaises(sqlite3.IntegrityError):
                self.app.state.store.db.execute('DELETE FROM audit')
            self.app.state.store.db.rollback()

    return unittest.defaultTestLoader.loadTestsFromTestCase(MVPTests)


def verify(pid, update=True):
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=1).run(suite_for(pid))
    report = {'project_id': pid, 'tests_run': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'successful': result.wasSuccessful(),
              'duration_s': round(time.monotonic() - started, 2),
              'scope': 'local synthetic baseline/API/UI assets/review/export/provider adapter',
              'live_model_tested': False, 'cloud_deployed': False,
              'command': f'python scripts/verify_mvp.py --project {pid}'}
    if update:
        (locate(pid) / 'evaluation' / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    report = verify(args.project)
    print(json.dumps(report))
    raise SystemExit(0 if report['successful'] else 1)
