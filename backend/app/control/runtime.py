"""Runtime proxy comparison between the proposed and baseline controllers (FR-09, FR-10).

The command chosen after record i is assumed to hold over the interval [t_i, t_{i+1}).
An interval counts only when both endpoint records are valid and the gap is <= MAX_GAP_SECONDS.
Intervals in which the proposed controller is under manual override are excluded from BOTH
totals. Runtime is a proxy for commanded operation, not measured energy.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import MAX_GAP_SECONDS
from app.control.modes import ControlSource, Mode
from app.control.records import Decision, SensorRecord


@dataclass
class ModeTotals:
    heating_s: float = 0.0
    cooling_s: float = 0.0

    @property
    def active_s(self) -> float:
        return self.heating_s + self.cooling_s

    def add(self, mode: Mode, seconds: float) -> None:
        if mode is Mode.HEATING:
            self.heating_s += seconds
        elif mode is Mode.COOLING:
            self.cooling_s += seconds


@dataclass
class RuntimeAccumulator:
    proposed: ModeTotals = field(default_factory=ModeTotals)
    baseline: ModeTotals = field(default_factory=ModeTotals)
    counted_s: float = 0.0
    excluded_gap_s: float = 0.0
    excluded_invalid_s: float = 0.0
    excluded_manual_s: float = 0.0

    def add_interval(
        self,
        start: SensorRecord,
        end: SensorRecord,
        proposed: Decision,
        baseline: Decision,
    ) -> None:
        """Attribute [start.timestamp, end.timestamp) using the decisions taken at `start`."""
        dt = (end.timestamp - start.timestamp).total_seconds()
        if dt <= 0:
            return
        if dt > MAX_GAP_SECONDS:
            self.excluded_gap_s += dt
        elif not (start.valid and end.valid):
            self.excluded_invalid_s += dt
        elif proposed.source is ControlSource.MANUAL:
            self.excluded_manual_s += dt
        else:
            self.counted_s += dt
            self.proposed.add(proposed.mode, dt)
            self.baseline.add(baseline.mode, dt)

    @property
    def reduction_pct(self) -> float | None:
        """(baseline - proposed) / baseline * 100, or None (shown as N/A) if baseline is zero."""
        b = self.baseline.active_s
        if b == 0:
            return None
        return (b - self.proposed.active_s) / b * 100.0
