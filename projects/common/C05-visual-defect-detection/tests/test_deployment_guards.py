"""Deployment-configuration contracts.

These lock the two behaviours that local runs do not exercise but cloud
requires. MODEL_FREEZE is in effect: nothing here touches the model, prompts,
labels, validators, or inference vocabulary.

1. The ASGI app must accept explicitly allowed Host values and keep rejecting
   everything else. In Cloud Run the Host header is the service URL, not
   loopback; without MVP_ALLOWED_HOSTS every request 403s.
2. The container entrypoint must bind 0.0.0.0, not loopback. Cloud Run cannot
   reach a loopback-bound process, so the service would be unreachable.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from shared_mvp.testing import LocalClient  # noqa: E402


def _load_api(name):
    spec = importlib.util.spec_from_file_location(name, SRC / "c05_api.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HostGuardContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls._saved = os.environ.pop("MVP_ALLOWED_HOSTS", None)
        cls.app = _load_api("c05_api_hostguard").create_app(
            str(Path(cls._tmp.name) / "hosts.sqlite"))
        cls.client = LocalClient(cls.app)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.close()
            cls.app.state.store.db.close()
        finally:
            if cls._saved is None:
                os.environ.pop("MVP_ALLOWED_HOSTS", None)
            else:
                os.environ["MVP_ALLOWED_HOSTS"] = cls._saved
            cls._tmp.cleanup()

    def test_unknown_host_is_rejected(self):
        r = self.client.get("/health", headers={"host": "evil.example.com"})
        self.assertEqual(r.status_code, 403, r.text)

    def test_loopback_hosts_still_accepted_by_default(self):
        for host in ("127.0.0.1", "localhost", "testserver"):
            r = self.client.get("/health", headers={"host": host})
            self.assertEqual(r.status_code, 200, f"host={host}: {r.text}")

    def test_explicitly_allowed_host_is_accepted(self):
        os.environ["MVP_ALLOWED_HOSTS"] = "c05-backend-staging-xyz.a.run.app"
        try:
            r = self.client.get(
                "/health", headers={"host": "c05-backend-staging-xyz.a.run.app"})
            self.assertEqual(r.status_code, 200, r.text)
        finally:
            os.environ.pop("MVP_ALLOWED_HOSTS", None)

    def test_allowed_list_never_implies_unlisted_hosts(self):
        os.environ["MVP_ALLOWED_HOSTS"] = "c05-backend-staging-xyz.a.run.app"
        try:
            r = self.client.get("/health", headers={"host": "other.a.run.app"})
            self.assertEqual(r.status_code, 403, r.text)
        finally:
            os.environ.pop("MVP_ALLOWED_HOSTS", None)


class EntrypointContract(unittest.TestCase):
    def test_entrypoint_binds_all_interfaces(self):
        text = (SRC / "c05_entry.py").read_text()
        self.assertIn('host="0.0.0.0"', text,
                      "Cloud Run cannot reach a loopback-bound process")
        self.assertNotIn('host="127.0.0.1"', text)

    def test_entrypoint_port_comes_from_env(self):
        text = (SRC / "c05_entry.py").read_text()
        self.assertIn('os.environ.get("PORT"', text,
                      "Cloud Run assigns the port at runtime")


if __name__ == "__main__":
    unittest.main(verbosity=2)
