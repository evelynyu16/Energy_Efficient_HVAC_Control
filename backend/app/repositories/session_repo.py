"""Simulation sessions and control-event history (FR-02, FR-08)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.control.records import Decision, SensorRecord
from app.db import Database


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------ sessions
    def create(self, session_id: str, dataset_label: str, settings_json: str, total: int) -> None:
        with self.db.tx() as c:
            c.execute(
                "INSERT INTO sessions (id, created_at, status, dataset_label, settings_json, "
                "total_records) VALUES (?, ?, 'READY', ?, ?, ?)",
                (session_id, _now(), dataset_label, settings_json, total),
            )

    def update_progress(self, session_id: str, status: str, cursor: int) -> None:
        with self.db.tx() as c:
            c.execute("UPDATE sessions SET status = ?, cursor = ? WHERE id = ?",
                      (status, cursor, session_id))

    def finish(self, session_id: str, status: str, cursor: int, report: dict) -> None:
        with self.db.tx() as c:
            c.execute(
                "UPDATE sessions SET status = ?, cursor = ?, ended_at = ?, report_json = ? "
                "WHERE id = ?",
                (status, cursor, _now(), json.dumps(report, default=str), session_id),
            )

    def mark_interrupted(self) -> None:
        """Sessions that were live when the server stopped cannot resume; keep their logs."""
        with self.db.tx() as c:
            c.execute(
                "UPDATE sessions SET status = 'INTERRUPTED', ended_at = ? "
                "WHERE status IN ('READY', 'RUNNING', 'PAUSED')",
                (_now(),),
            )

    def get(self, session_id: str) -> dict | None:
        with self.db.tx() as c:
            row = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return _session_dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict]:
        with self.db.tx() as c:
            rows = c.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [_session_dict(r) for r in rows]

    # ------------------------------------------------------------------ events
    def add_event(
        self, session_id: str, controller: str, decision: Decision, record: SensorRecord | None
    ) -> None:
        with self.db.tx() as c:
            c.execute(
                "INSERT INTO events (session_id, controller, record_index, timestamp, "
                "temperature_c, humidity_pct, occupancy, previous_mode, new_mode, source, "
                "reason, detail, logged_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id, controller, decision.record_index,
                    decision.timestamp.isoformat(),
                    record.temperature_c if record else None,
                    record.humidity_pct if record else None,
                    record.occupancy if record else None,
                    decision.previous_mode.value if decision.previous_mode else None,
                    decision.mode.value, decision.source.value, decision.reason.value,
                    decision.detail, _now(),
                ),
            )

    def events(
        self, session_id: str, controller: str = "PROPOSED", limit: int = 200, offset: int = 0
    ) -> tuple[list[dict], int]:
        with self.db.tx() as c:
            total = c.execute(
                "SELECT COUNT(*) FROM events WHERE session_id = ? AND controller = ?",
                (session_id, controller),
            ).fetchone()[0]
            rows = c.execute(
                "SELECT * FROM events WHERE session_id = ? AND controller = ? "
                "ORDER BY id LIMIT ? OFFSET ?",
                (session_id, controller, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows], total


def _session_dict(row) -> dict:
    d = dict(row)
    d["settings"] = json.loads(d.pop("settings_json"))
    report = d.pop("report_json")
    d["report"] = json.loads(report) if report else None
    return d
