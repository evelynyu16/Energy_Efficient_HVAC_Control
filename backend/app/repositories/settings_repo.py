"""Persisted controller settings and their change history (FR-07)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from app.control.settings import ControlSettings
from app.db import Database


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self) -> ControlSettings:
        with self.db.tx() as c:
            row = c.execute("SELECT json FROM settings WHERE id = 1").fetchone()
        return ControlSettings.model_validate_json(row["json"]) if row else ControlSettings()

    def save(self, new: ControlSettings) -> list[dict]:
        """Persist `new` and record one change row per modified field. Returns the changes."""
        old = self.get()
        old_d, new_d = old.model_dump(mode="json"), new.model_dump(mode="json")
        changes = [
            {"field": k, "old_value": old_d[k], "new_value": new_d[k]}
            for k in new_d if old_d.get(k) != new_d[k]
        ]
        now = _now()
        with self.db.tx() as c:
            c.execute(
                "INSERT INTO settings (id, json, updated_at) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET json = excluded.json, "
                "updated_at = excluded.updated_at",
                (new.model_dump_json(), now),
            )
            c.executemany(
                "INSERT INTO settings_changes (changed_at, field, old_value, new_value) "
                "VALUES (?, ?, ?, ?)",
                [(now, ch["field"], json.dumps(ch["old_value"]), json.dumps(ch["new_value"]))
                 for ch in changes],
            )
        return changes

    def changes(self, limit: int = 100) -> list[dict]:
        with self.db.tx() as c:
            rows = c.execute(
                "SELECT * FROM settings_changes ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {**dict(r), "old_value": json.loads(r["old_value"]),
             "new_value": json.loads(r["new_value"])}
            for r in rows
        ]
