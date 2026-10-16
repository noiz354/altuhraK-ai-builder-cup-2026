"""Single-process local SQLite store, optimistic revisions, append-only audit."""
import json
import sqlite3
import threading
from pathlib import Path


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS items(kind TEXT,id TEXT,payload TEXT,PRIMARY KEY(kind,id));
            CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY AUTOINCREMENT,
              run_id TEXT,event TEXT,payload TEXT);
            CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
              BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
              BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
        ''')
        self.db.commit()

    def get(self, kind, identifier):
        with self.lock:
            row = self.db.execute('SELECT payload FROM items WHERE kind=? AND id=?',
                                  (kind, identifier)).fetchone()
            return json.loads(row[0]) if row else None

    def put(self, kind, identifier, payload):
        with self.lock:
            self.db.execute('INSERT INTO items VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload',
                            (kind, identifier, json.dumps(payload, allow_nan=False)))
            self.db.commit()

    def append(self, run_id, event, payload):
        with self.lock:
            self.db.execute('INSERT INTO audit(run_id,event,payload) VALUES(?,?,?)',
                            (run_id, event, json.dumps(payload, allow_nan=False)))
            self.db.commit()

    def list_kind(self, kind):
        """All payloads of one kind. Backend-agnostic replacement for raw SQL."""
        with self.lock:
            return [json.loads(payload) for (payload,) in self.db.execute(
                'SELECT payload FROM items WHERE kind=?', (kind,)).fetchall()]

    def close(self):
        with self.lock:
            self.db.close()

    def history(self, run_id):
        with self.lock:
            return [{'seq': seq, 'event': event, 'payload': json.loads(payload)}
                    for seq, event, payload in self.db.execute(
                        'SELECT seq,event,payload FROM audit WHERE run_id=? ORDER BY seq', (run_id,))]
