"""FirestoreStore contract tests with an in-memory fake client.

The adapter must honor the exact Store semantics the rest of the system relies
on: get/put round-trip, list_kind coverage, audit history in insertion order
with gapless sequence numbers, and append-only audit. These run offline; the
live Firestore database is exercised by scripts, not by committed tests, so
the suite never needs credentials.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from shared_mvp.firestore_store import FirestoreStore  # noqa: E402


class _Snap:
    def __init__(self, data):
        self._data = data
        self.exists = data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _Clock:
    """Local stand-in for server time: strictly increasing ticks."""

    _tick = 0

    @classmethod
    def now(cls):
        cls._tick += 1
        return cls._tick


def _resolve_for_fake(data):
    """Resolve server-timestamp sentinels to local ticks.

    The adapter passes the real SERVER_TIMESTAMP sentinel for `created`, which
    is an opaque object, not a number. Anything non-primitive in that field
    becomes a tick so ordering behaves like server time.
    """
    out = {}
    for k, v in data.items():
        if k == "created" and not isinstance(v, (int, float)):
            v = _Clock.now()
        out[k] = v
    return out


class _DocRef:
    def __init__(self, store, path):
        self._store = store
        self._path = path

    def get(self, transaction=None):
        return _Snap(self._store.get(self._path))

    def set(self, data):
        self._store[self._path] = _resolve_for_fake(data)

    def collection(self, name):
        return _Collection(self._store, self._path + (name,))


class _Collection:
    def __init__(self, store, path):
        self._store = store
        self._path = path
        self._counter = 0

    def document(self, doc_id=None):
        if doc_id is None:
            # Derive from stored contents, not an instance counter: the adapter
            # builds a fresh collection object per call, exactly like the real
            # client, so instance state would collide auto-ids.
            existing = sum(1 for k in self._store
                           if len(k) == len(self._path) + 1 and k[:len(self._path)] == self._path)
            doc_id = f"auto-{existing + 1}"
        return _DocRef(self._store, self._path + (doc_id,))

    def add(self, data):
        ref = self.document()
        ref.set(data)
        return ref

    def stream(self):
        n = len(self._path)
        return [_Snap(v) for k, v in sorted(self._store.items())
                if len(k) == n + 1 and k[:n] == self._path]

    def order_by(self, field):
        outer = self

        class _Ordered(_Collection):
            def stream(self):
                return sorted(super().stream(),
                              key=lambda s: s.to_dict()[field])

        return _Ordered(self._store, self._path)


class _Tx:
    """Stand-in for a Firestore Transaction: get/set/commit against refs."""

    @staticmethod
    def get(ref, transaction=None):
        return ref.get()

    @staticmethod
    def set(ref, data):
        ref.set(data)

    @staticmethod
    def commit():
        return None


class _FakeClient:
    """Minimal Firestore surface the adapter touches, backed by a dict."""

    def __init__(self):
        self._store = {}

    def collection(self, name):
        return _Collection(self._store, (name,))

    def transaction(self):
        return _Tx()

    def close(self):
        pass


class FirestoreStoreContract(unittest.TestCase):
    def setUp(self):
        self.store = FirestoreStore(client=_FakeClient())

    def test_put_get_round_trip(self):
        self.assertIsNone(self.store.get("inspection", "missing"))
        self.store.put("inspection", "a1", {"label": "meal_complete", "n": 3})
        self.assertEqual(self.store.get("inspection", "a1"),
                         {"label": "meal_complete", "n": 3})

    def test_put_overwrites(self):
        self.store.put("inspection", "a1", {"v": 1})
        self.store.put("inspection", "a1", {"v": 2})
        self.assertEqual(self.store.get("inspection", "a1"), {"v": 2})

    def test_kinds_are_isolated(self):
        self.store.put("inspection", "a1", {"v": 1})
        self.assertIsNone(self.store.get("run", "a1"))
        self.assertEqual(self.store.list_kind("run"), [])

    def test_list_kind_covers_all(self):
        for i in range(5):
            self.store.put("inspection", f"i{i}", {"i": i})
        got = self.store.list_kind("inspection")
        self.assertEqual(len(got), 5)
        self.assertEqual(sorted(r["i"] for r in got), [0, 1, 2, 3, 4])

    def test_audit_history_is_ordered_with_gapless_seq(self):
        for n in range(4):
            self.store.append("run-1", f"event-{n}", {"n": n})
        hist = self.store.history("run-1")
        self.assertEqual([h["seq"] for h in hist], [1, 2, 3, 4])
        self.assertEqual([h["event"] for h in hist],
                         [f"event-{n}" for n in range(4)])
        self.assertEqual(hist[2]["payload"], {"n": 2})

    def test_audit_isolated_per_run(self):
        self.store.append("run-1", "e", {})
        self.store.append("run-2", "e", {})
        self.assertEqual(len(self.store.history("run-1")), 1)
        self.assertEqual(self.store.history("run-2")[0]["seq"], 1)

    def test_empty_history(self):
        self.assertEqual(self.store.history("nope"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
