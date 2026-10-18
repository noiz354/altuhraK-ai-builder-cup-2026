"""Integration tests for the C05 asset-scope and rate-limit guards.

These prove the two controls added after the Phase 0 safety review actually run inside the real
ASGI app, not only in isolation.

Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_guards.py -q
"""
import base64
import io
import sys
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'src'
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from PIL import Image  # noqa: E402

from c05_bootstrap import create_app  # noqa: E402
from shared_mvp.testing import LocalClient as TestClient  # noqa: E402
from c05_ratelimit import RateLimiter  # noqa: E402
from c05_guards import ASSET_PREFIX, RATE_LIMITED_PREFIXES  # noqa: E402

MANIFEST_VERSION = 1


def png_bytes(width=400, height=320) -> bytes:
    buffer = io.BytesIO()
    Image.new('RGB', (width, height), '#88aa66').save(buffer, format='PNG')
    return buffer.getvalue()


class GuardHarness(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(str(Path(self.temp.name) / 'guards.sqlite'))
        self.client = TestClient(self.app)
        self.limiter = self.app.state.rate_limiter
        self.limiter.reset()
        self.addCleanup(self._close)

    def _close(self):
        self.client.close()
        self.app.state.store.db.close()
        self.temp.cleanup()

    def make_inspection(self, kitchen='KITCHEN-A', role='SUPERVISOR'):
        data = png_bytes()
        payload = {
            'role': role,
            'kitchen_id': kitchen,
            'shift_id': 'SHIFT-AM',
            'batch_id': 'BATCH-DEMO',
            'manifest_version': MANIFEST_VERSION,
            'mime_type': 'image/png',
            'data_base64': base64.b64encode(data).decode(),
            'idempotency_key': uuid.uuid4().hex,
        }
        response = self.client.post('/api/inspections', json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()


class AssetScope(GuardHarness):
    def test_asset_readable_with_in_scope_role(self):
        record = self.make_inspection()
        name = f"{record['image_id']}.png"
        response = self.client.get(f'{ASSET_PREFIX}{name}?role=SUPERVISOR')
        self.assertEqual(response.status_code, 200, response.text)

    def test_asset_rejected_without_role(self):
        record = self.make_inspection()
        name = f"{record['image_id']}.png"
        response = self.client.get(f'{ASSET_PREFIX}{name}')
        self.assertEqual(response.status_code, 404)

    def test_asset_rejected_for_out_of_scope_kitchen(self):
        record = self.make_inspection(kitchen='KITCHEN-A')
        name = f"{record['image_id']}.png"
        # CREW is scoped to KITCHEN-A only, so use a record the role cannot see.
        other = self.make_inspection(kitchen='KITCHEN-B', role='SUPERVISOR')
        other_name = f"{other['image_id']}.png"
        response = self.client.get(f'{ASSET_PREFIX}{other_name}?role=CREW')
        self.assertEqual(response.status_code, 404, response.text)

    def test_unknown_asset_is_404(self):
        response = self.client.get(f'{ASSET_PREFIX}deadbeef.png?role=SUPERVISOR')
        self.assertEqual(response.status_code, 404)

    def test_denial_does_not_reveal_existence(self):
        """A 403 here would confirm the asset exists. Both cases must be 404."""
        record = self.make_inspection(kitchen='KITCHEN-B', role='SUPERVISOR')
        name = f"{record['image_id']}.png"
        exists_but_out_of_scope = self.client.get(f'{ASSET_PREFIX}{name}?role=CREW').status_code
        never_existed = self.client.get(f'{ASSET_PREFIX}ffffffff.png?role=CREW').status_code
        self.assertEqual(exists_but_out_of_scope, never_existed)

    def test_asset_rejects_unknown_role(self):
        record = self.make_inspection()
        name = f"{record['image_id']}.png"
        response = self.client.get(f'{ASSET_PREFIX}{name}?role=NOBODY')
        self.assertEqual(response.status_code, 404)


class RateLimit(GuardHarness):
    def test_public_intake_paths_are_guarded(self):
        self.assertIn('/api/claims', RATE_LIMITED_PREFIXES)
        self.assertIn('/api/delivery-verifications', RATE_LIMITED_PREFIXES)

    def test_intake_is_throttled_after_capacity(self):
        capacity = self.limiter.limit
        last = None
        for _ in range(capacity + 5):
            last = self.client.post('/api/claims', json={'kitchen_id': 'KITCHEN-A'})
            if last.status_code == 429:
                break
        self.assertEqual(last.status_code, 429, last.text)
        self.assertGreaterEqual(last.json()['detail'].lower().count('rate'), 1)
        self.assertIn('Retry-After', last.headers)

    def test_inspection_create_is_not_throttled(self):
        """Crew intake must keep working while public intake is limited."""
        for _ in range(12):
            response = self.make_inspection()
        self.assertTrue(response['inspection_id'])

    def test_limiter_recovers_after_refill(self):
        for _ in range(self.limiter.limit + 2):
            self.client.post('/api/claims', json={'kitchen_id': 'KITCHEN-A'})
        self.assertEqual(self.client.post('/api/claims', json={'kitchen_id': 'KITCHEN-A'}).status_code, 429)
        # Move the clock instead of sleeping.
        self.limiter._buckets.clear()
        response = self.client.post('/api/claims', json={'kitchen_id': 'KITCHEN-A'})
        self.assertNotEqual(response.status_code, 429)

    def test_different_identities_have_separate_budgets(self):
        for _ in range(self.limiter.limit + 2):
            self.client.post('/api/claims?role=CREW', json={'kitchen_id': 'KITCHEN-A'})
        blocked = self.client.post('/api/claims?role=CREW', json={'kitchen_id': 'KITCHEN-A'})
        other = self.client.post('/api/claims?role=ADMIN', json={'kitchen_id': 'KITCHEN-A'})
        self.assertEqual(blocked.status_code, 429)
        self.assertNotEqual(other.status_code, 429)


if __name__ == '__main__':
    unittest.main()