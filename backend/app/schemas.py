"""Pydantic request/response models for the REST API (JSON contract with the frontend).

Keep frontend/src/api/types.ts in sync with this file.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.control.modes import ControlSource, Mode, Reason
from app.control.records import Decision, SensorRecord
from app.services.playback import Frame, SimulationSession


class RecordOut(BaseModel):
    index: int
    timestamp: datetime
    temperature_c: float | None
    humidity_pct: float | None
    occupancy: int | None
    valid: bool
    error: str | None

    @classmethod
    def of(cls, r: SensorRecord) -> RecordOut:
        return cls(index=r.index, timestamp=r.timestamp, temperature_c=r.temperature_c,
                   humidity_pct=r.humidity_pct, occupancy=r.occupancy, valid=r.valid,
                   error=r.error)


class DecisionOut(BaseModel):
    timestamp: datetime
    mode: Mode
    previous_mode: Mode | None
    source: ControlSource
    reason: Reason
    detail: str

    @classmethod
    def of(cls, d: Decision) -> DecisionOut:
        return cls(timestamp=d.timestamp, mode=d.mode, previous_mode=d.previous_mode,
                   source=d.source, reason=d.reason, detail=d.detail)


class FrameOut(BaseModel):
    record: RecordOut
    proposed: DecisionOut
    baseline: DecisionOut

    @classmethod
    def of(cls, f: Frame) -> FrameOut:
        return cls(record=RecordOut.of(f.record), proposed=DecisionOut.of(f.proposed),
                   baseline=DecisionOut.of(f.baseline))


class SessionStateOut(BaseModel):
    session_id: str
    status: str
    cursor: int
    total_records: int
    dataset_label: str
    settings: dict
    manual_mode: Mode | None
    control_source: ControlSource
    current: FrameOut | None

    @classmethod
    def of(cls, s: SimulationSession) -> SessionStateOut:
        return cls(
            session_id=s.id, status=s.status.value, cursor=s.cursor, total_records=s.total,
            dataset_label=s.dataset.label, settings=s.settings.model_dump(mode="json"),
            manual_mode=s.proposed.manual_mode, control_source=s.proposed.source,
            current=FrameOut.of(s.last_frame) if s.last_frame else None,
        )


class StepRequest(BaseModel):
    count: int = Field(1, ge=1, le=500)


class StepResponse(BaseModel):
    frames: list[FrameOut]
    state: SessionStateOut


class ManualRequest(BaseModel):
    mode: Mode
    reason: str = Field("", max_length=500, description="Operator's reason, stored in the log")


class AutoRequest(BaseModel):
    reason: str = Field("", max_length=500)


class EventOut(BaseModel):
    id: int
    session_id: str
    controller: str
    record_index: int | None
    timestamp: str
    temperature_c: float | None
    humidity_pct: float | None
    occupancy: int | None
    previous_mode: str | None
    new_mode: str
    source: str
    reason: str
    detail: str
    logged_at: str


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
