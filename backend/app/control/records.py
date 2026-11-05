"""Immutable value objects passed between the data layer and the controller."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.control.modes import ControlSource, Mode, Reason


@dataclass(frozen=True, slots=True)
class SensorRecord:
    """One recorded observation. Recorded values are fixed inputs: commands never change them."""

    index: int
    timestamp: datetime
    temperature_c: float | None
    humidity_pct: float | None
    occupancy: int | None
    valid: bool = True
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Decision:
    """The controller output after processing one record or one operator command."""

    timestamp: datetime
    mode: Mode
    previous_mode: Mode | None
    source: ControlSource
    reason: Reason
    detail: str = ""
    record_index: int | None = None

    @property
    def mode_changed(self) -> bool:
        return self.mode is not self.previous_mode
