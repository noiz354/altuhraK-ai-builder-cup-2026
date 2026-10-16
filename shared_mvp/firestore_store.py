"""Durable Store backend on Cloud Firestore.

Drop-in replacement for the SQLite `Store` in `store.py`, exposing the same
method names (`get`, `put`, `append`, `history`) plus `list_kind` for the
few list-by-kind queries that C05 performs. The SQLite implementation is
untouched: the other 23 projects keep using it, and C05 selects this backend
only when `C05_FIRESTORE_PROJECT` is set.

Layout inside the database (collections never collide with other workloads):

    items/{kind}/{id}            document {payload: <json string>}
    audit/{run_id}/entries/{auto-id}
                                 document {event, payload, created}

`history()` returns entries ordered by server timestamp with read-time
sequence numbers. Nothing in the system keys on seq values; they are display
ordering for the audit trail. This keeps appends to a single write with no
contention point and no transaction machinery.

Nothing here stores credentials. The client is built from Application Default
Credentials: the ADC file or `gcloud auth` locally, the attached service
account's metadata server on Cloud Run.
"""
from __future__ import annotations

import json
import threading


class FirestoreStore:
    def __init__(self, client=None, project=None, database="(default)"):
        """`client` is injectable so unit tests can pass a fake.

        In production pass nothing: the client is built from ADC.
        """
        if client is None:
            from google.cloud import firestore  # type: ignore

            client = firestore.Client(project=project, database=database)
        self.db = client
        self.lock = threading.RLock()

    # ------------------------------------------------------------------ items

    def get(self, kind, identifier):
        with self.lock:
            doc = self.db.collection("items").document(kind).collection("entries") \
                .document(identifier).get()
            data = doc.to_dict() if doc.exists else None
            return json.loads(data["payload"]) if data else None

    def put(self, kind, identifier, payload):
        with self.lock:
            self.db.collection("items").document(kind).collection("entries") \
                .document(identifier).set(
                    {"payload": json.dumps(payload, allow_nan=False)})

    def list_kind(self, kind):
        """All payloads of one kind. Replaces `SELECT payload FROM items`."""
        with self.lock:
            return [json.loads(d.to_dict()["payload"])
                    for d in self.db.collection("items").document(kind)
                    .collection("entries").stream()]

    # ------------------------------------------------------------------ audit

    def append(self, run_id, event, payload):
        # No counter transaction. Sequence numbers are assigned at read time from
        # timestamp order (see history), which keeps appends to a single write
        # with no contention point. The only approximation versus SQLite
        # AUTOINCREMENT is that two appends landing in the same millisecond have
        # no defined relative order; nothing in the system keys on seq values,
        # they are display ordering for the audit trail.
        with self.lock:
            from google.cloud.firestore import SERVER_TIMESTAMP  # type: ignore

            self.db.collection("audit").document(run_id).collection("entries").add({
                "event": event,
                "payload": json.dumps(payload, allow_nan=False),
                "created": SERVER_TIMESTAMP,
            })

    def history(self, run_id):
        with self.lock:
            docs = self.db.collection("audit").document(run_id).collection("entries") \
                .order_by("created").stream()
            return [{"seq": n, "event": d.to_dict()["event"],
                     "payload": json.loads(d.to_dict()["payload"])}
                    for n, d in enumerate(docs, start=1)]

    def close(self):
        client = getattr(self.db, "_client", None)
        closer = getattr(client or self.db, "close", None)
        if callable(closer):
            closer()
