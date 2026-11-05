"""Simulation session engine: drives playback, both controllers, logging and runtime totals.

Playback is pull-based: the client calls `step(n)` while the session is RUNNING. Pausing simply
rejects further steps, so progression stops deterministically (FR-02). Reset = end the current
session and create a new one; earlier sessions and their events stay in the database.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from app.control.controller import Controller, Policy
from app.control.modes import Mode
from app.control.records import Decision, SensorRecord
from app.control.runtime import RuntimeAccumulator
from app.control.settings import ControlSettings
from app.data.loader import Dataset
from app.repositories.session_repo import SessionRepository


class SessionStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ENDED = "ENDED"
    COMPLETED = "COMPLETED"  # reached the last record


class PlaybackError(Exception):
    """Raised for commands that are not allowed in the session's current status."""


@dataclass
class Frame:
    """What the dashboard needs to render one processed record."""

    record: SensorRecord
    proposed: Decision
    baseline: Decision


@dataclass
class SimulationSession:
    id: str
    dataset: Dataset
    settings: ControlSettings
    proposed: Controller
    baseline: Controller
    status: SessionStatus = SessionStatus.READY
    cursor: int = 0  # index of the next record to process
    runtime: RuntimeAccumulator = field(default_factory=RuntimeAccumulator)
    last_frame: Frame | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def total(self) -> int:
        return len(self.dataset.records)


class PlaybackService:
    def __init__(self, repo: SessionRepository) -> None:
        self.repo = repo
        self._sessions: dict[str, SimulationSession] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ lifecycle
    def create(self, dataset: Dataset, settings: ControlSettings) -> SimulationSession:
        session = SimulationSession(
            id=uuid.uuid4().hex[:12],
            dataset=dataset,
            settings=settings,
            proposed=Controller(settings, Policy.OCCUPANCY),
            baseline=Controller(settings, Policy.SCHEDULE),
        )
        self.repo.create(session.id, dataset.label, settings.model_dump_json(), session.total)
        with self._lock:
            for other in self._sessions.values():
                if other.status in (SessionStatus.READY, SessionStatus.RUNNING,
                                    SessionStatus.PAUSED):
                    self._finish(other, SessionStatus.ENDED)
            self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> SimulationSession | None:
        return self._sessions.get(session_id)

    def play(self, s: SimulationSession) -> None:
        with s.lock:
            self._require(s, SessionStatus.READY, SessionStatus.PAUSED, SessionStatus.RUNNING)
            s.status = SessionStatus.RUNNING
            self.repo.update_progress(s.id, s.status, s.cursor)

    def pause(self, s: SimulationSession) -> None:
        with s.lock:
            self._require(s, SessionStatus.RUNNING, SessionStatus.PAUSED)
            s.status = SessionStatus.PAUSED
            self.repo.update_progress(s.id, s.status, s.cursor)

    def end(self, s: SimulationSession) -> dict:
        with s.lock:
            if s.status not in (SessionStatus.ENDED, SessionStatus.COMPLETED):
                self._finish(s, SessionStatus.ENDED)
            return self.report(s)

    # ------------------------------------------------------------------ playback
    def step(self, s: SimulationSession, count: int = 1) -> list[Frame]:
        with s.lock:
            self._require(s, SessionStatus.RUNNING)
            frames: list[Frame] = []
            for _ in range(count):
                if s.cursor >= s.total:
                    break
                frames.append(self._process(s, s.dataset.records[s.cursor]))
                s.cursor += 1
            if s.cursor >= s.total:
                self._finish(s, SessionStatus.COMPLETED)
            else:
                self.repo.update_progress(s.id, s.status, s.cursor)
            return frames

    def _process(self, s: SimulationSession, record: SensorRecord) -> Frame:
        prev = s.last_frame
        if prev is not None:
            # Close the previous interval using the decisions in force since the last record
            # (including any manual command issued after it).
            s.runtime.add_interval(prev.record, record, prev.proposed, prev.baseline)
        proposed = s.proposed.step(record)
        baseline = s.baseline.step(record)
        if proposed.mode_changed:
            self.repo.add_event(s.id, "PROPOSED", proposed, record)
        if baseline.mode_changed:
            self.repo.add_event(s.id, "BASELINE", baseline, record)
        s.last_frame = Frame(record, proposed, baseline)
        return s.last_frame

    # ------------------------------------------------------------------ manual control
    def set_manual(self, s: SimulationSession, mode: Mode, note: str) -> Decision:
        with s.lock:
            self._require_live(s)
            at = self._dataset_now(s)
            decision = s.proposed.set_manual(mode, at, note)
            return self._apply_command(s, decision)

    def release_manual(self, s: SimulationSession, note: str) -> Decision:
        with s.lock:
            self._require_live(s)
            at = self._dataset_now(s)
            decision = s.proposed.release_manual(at, note)
            return self._apply_command(s, decision)

    def _apply_command(self, s: SimulationSession, decision: Decision) -> Decision:
        record = s.last_frame.record if s.last_frame else None
        self.repo.add_event(s.id, "PROPOSED", decision, record)  # operator actions always logged
        if s.last_frame is not None:
            s.last_frame = Frame(s.last_frame.record, decision, s.last_frame.baseline)
        return decision

    def _dataset_now(self, s: SimulationSession):
        if s.last_frame is not None:
            return s.last_frame.record.timestamp
        if s.dataset.records:
            return s.dataset.records[0].timestamp
        raise PlaybackError("dataset is empty")

    # ------------------------------------------------------------------ reporting
    def report(self, s: SimulationSession) -> dict:
        r = s.runtime
        return {
            "session_id": s.id,
            "status": s.status.value,
            "records_processed": s.cursor,
            "total_records": s.total,
            "proposed": {"heating_s": r.proposed.heating_s, "cooling_s": r.proposed.cooling_s,
                         "active_s": r.proposed.active_s},
            "baseline": {"heating_s": r.baseline.heating_s, "cooling_s": r.baseline.cooling_s,
                         "active_s": r.baseline.active_s},
            "counted_s": r.counted_s,
            "excluded_gap_s": r.excluded_gap_s,
            "excluded_invalid_s": r.excluded_invalid_s,
            "excluded_manual_s": r.excluded_manual_s,
            "reduction_pct": r.reduction_pct,
            "disclaimer": "Runtime is a proxy for commanded heating/cooling time in a simulation; "
                          "it is not measured energy savings.",
        }

    # ------------------------------------------------------------------ helpers
    def _finish(self, s: SimulationSession, status: SessionStatus) -> None:
        s.status = status
        self.repo.finish(s.id, status, s.cursor, self.report(s))

    @staticmethod
    def _require(s: SimulationSession, *allowed: SessionStatus) -> None:
        if s.status not in allowed:
            names = ", ".join(a.value for a in allowed)
            raise PlaybackError(f"session is {s.status.value}; requires one of: {names}")

    def _require_live(self, s: SimulationSession) -> None:
        self._require(s, SessionStatus.READY, SessionStatus.RUNNING, SessionStatus.PAUSED)

