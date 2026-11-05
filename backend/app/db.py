"""SQLite access. One shared connection guarded by a lock; schema created on startup."""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    json        TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    ended_at        TEXT,
    status          TEXT NOT NULL,
    dataset_label   TEXT NOT NULL,
    settings_json   TEXT NOT NULL,
    total_records   INTEGER NOT NULL,
    cursor          INTEGER NOT NULL DEFAULT 0,
    report_json     TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    controller      TEXT NOT NULL CHECK (controller IN ('PROPOSED', 'BASELINE')),
    record_index    INTEGER,
    timestamp       TEXT NOT NULL,
    temperature_c   REAL,
    humidity_pct    REAL,
    occupancy       INTEGER,
    previous_mode   TEXT,
    new_mode        TEXT NOT NULL,
    source          TEXT NOT NULL,
    reason          TEXT NOT NULL,
    detail          TEXT NOT NULL DEFAULT '',
    logged_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id, controller, id);
"""


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        with self.tx() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        """Run statements in one committed transaction (FR-08: logs survive restarts)."""
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        self._conn.close()
