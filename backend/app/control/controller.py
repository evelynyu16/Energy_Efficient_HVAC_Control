"""Deterministic HVAC controller state machine (FR-04, FR-05, FR-06, FR-11).

Rule priority, highest first:
  1. Invalid record or data gap      -> DATA_UNAVAILABLE (no command, bypasses hold)
  2. Manual override                 -> operator-selected mode (bypasses hold)
  3. Policy idle condition           -> ECO (bypasses hold)
        occupancy policy: continuous vacancy >= vacancy_delay_s
        schedule policy:  timestamp outside the daily baseline window
  4. Thermostat with hysteresis      -> HEATING / COOLING / STANDBY,
                                        subject to min_mode_duration_s
Leaving ECO or DATA_UNAVAILABLE also bypasses the hold timer.

All timing uses dataset timestamps; the wall clock is never consulted, so replaying identical
records and settings yields identical decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.config import MAX_GAP_SECONDS
from app.control.modes import MANUAL_MODES, ControlSource, Mode, Reason
from app.control.records import Decision, SensorRecord
from app.control.settings import ControlSettings
from app.control.thermostat import thermostat_decision

THERMOSTAT_MODES = frozenset({Mode.HEATING, Mode.COOLING, Mode.STANDBY})


class Policy(StrEnum):
    OCCUPANCY = "OCCUPANCY"  # proposed occupancy-aware controller
    SCHEDULE = "SCHEDULE"  # fixed-schedule baseline (ignores occupancy, never overridden)


@dataclass
class _State:
    mode: Mode | None = None
    mode_since: datetime | None = None
    source: ControlSource = ControlSource.AUTO
    manual_mode: Mode | None = None
    vacancy_since: datetime | None = None
    last_timestamp: datetime | None = None
    last_record: SensorRecord | None = None
    data_unavailable: bool = False


class Controller:
    def __init__(self, settings: ControlSettings, policy: Policy = Policy.OCCUPANCY) -> None:
        self.settings = settings
        self.policy = policy
        self._s = _State()

    # ------------------------------------------------------------------ public read-only state
    @property
    def mode(self) -> Mode | None:
        return self._s.mode

    @property
    def source(self) -> ControlSource:
        return self._s.source

    @property
    def manual_mode(self) -> Mode | None:
        return self._s.manual_mode

    # ------------------------------------------------------------------ record processing
    def step(self, record: SensorRecord) -> Decision:
        s = self._s
        gap = (
            s.last_timestamp is not None
            and (record.timestamp - s.last_timestamp).total_seconds() > MAX_GAP_SECONDS
        )
        gap_s = (record.timestamp - s.last_timestamp).total_seconds() if gap else 0.0
        s.last_timestamp = record.timestamp
        s.last_record = record

        # 1. Invalid input / data gap take precedence over every other rule.
        if not record.valid:
            s.vacancy_since = None
            s.data_unavailable = True
            return self._transition(
                record.timestamp, Mode.DATA_UNAVAILABLE, Reason.INVALID_INPUT,
                record.error or "invalid record", record.index,
            )
        if gap:
            # Continuity is broken: vacancy must be re-observed from this record onward.
            s.vacancy_since = record.timestamp if record.occupancy == 0 else None
            s.data_unavailable = True
            return self._transition(
                record.timestamp, Mode.DATA_UNAVAILABLE, Reason.DATA_GAP,
                f"gap of {gap_s / 60:.1f} min exceeds {MAX_GAP_SECONDS // 60} min",
                record.index,
            )

        self._track_vacancy(record)
        return self._evaluate(record)

    # ------------------------------------------------------------------ operator commands
    def set_manual(self, mode: Mode, at: datetime, note: str = "") -> Decision:
        if mode not in MANUAL_MODES:
            raise ValueError(f"{mode} cannot be selected manually")
        if self.policy is not Policy.OCCUPANCY:
            raise ValueError("the baseline controller does not accept manual commands")
        s = self._s
        s.source = ControlSource.MANUAL
        s.manual_mode = mode
        idx = s.last_record.index if s.last_record else None
        if s.data_unavailable:
            # Invalid-data handling outranks manual commands; the override applies on recovery.
            return self._transition(
                at, Mode.DATA_UNAVAILABLE, Reason.MANUAL_OVERRIDE,
                _join(f"manual {mode} pending valid data", note), idx,
            )
        return self._transition(at, mode, Reason.MANUAL_OVERRIDE, note, idx)

    def release_manual(self, at: datetime, note: str = "") -> Decision:
        s = self._s
        s.source = ControlSource.AUTO
        s.manual_mode = None
        idx = s.last_record.index if s.last_record else None
        if s.data_unavailable or s.last_record is None:
            mode = s.mode or Mode.STANDBY
            return self._transition(at, mode, Reason.MANUAL_RELEASED, note, idx)
        decision = self._evaluate(s.last_record, at=at, bypass_hold=True)
        # Re-label so the log shows the operator action that triggered the re-evaluation.
        return self._relabel(decision, Reason.MANUAL_RELEASED, _join(decision.detail, note))

    # ------------------------------------------------------------------ internals
    def _track_vacancy(self, record: SensorRecord) -> None:
        s = self._s
        if record.occupancy == 0:
            if s.vacancy_since is None:
                s.vacancy_since = record.timestamp
        else:
            s.vacancy_since = None

    def _idle_condition(self, record: SensorRecord) -> tuple[bool, Reason, str]:
        st = self.settings
        if self.policy is Policy.OCCUPANCY:
            s = self._s
            if s.vacancy_since is None:
                return False, Reason.REOCCUPIED, ""
            vacant_s = (record.timestamp - s.vacancy_since).total_seconds()
            if vacant_s >= st.vacancy_delay_s:
                return True, Reason.VACANCY_TIMEOUT, f"unoccupied for {vacant_s / 60:.1f} min"
            return False, Reason.REOCCUPIED, ""
        t = record.timestamp.time()
        inside = st.baseline_start <= t < st.baseline_end
        window = f"{st.baseline_start:%H:%M}-{st.baseline_end:%H:%M}"
        if inside:
            return False, Reason.INSIDE_SCHEDULE, f"inside schedule {window}"
        return True, Reason.OUTSIDE_SCHEDULE, f"outside schedule {window}"

    def _evaluate(
        self, record: SensorRecord, at: datetime | None = None, bypass_hold: bool = False
    ) -> Decision:
        s = self._s
        at = at or record.timestamp
        recovering = s.data_unavailable
        s.data_unavailable = False

        # 2. Manual override.
        if s.source is ControlSource.MANUAL and s.manual_mode is not None:
            detail = "valid data resumed" if recovering else ""
            return self._transition(at, s.manual_mode, Reason.MANUAL_OVERRIDE, detail, record.index)

        # 3. Policy idle condition (vacancy or outside schedule) -> ECO.
        idle, idle_reason, idle_detail = self._idle_condition(record)
        if idle:
            return self._transition(at, Mode.ECO, idle_reason, idle_detail, record.index)

        # 4. Thermostat.
        assert record.temperature_c is not None  # guaranteed for valid records
        base = s.mode if s.mode in THERMOSTAT_MODES else Mode.STANDBY
        wanted, reason = thermostat_decision(base, record.temperature_c, self.settings)
        detail = f"{record.temperature_c:.2f} C"

        leaving_special = s.mode not in THERMOSTAT_MODES  # None, ECO or DATA_UNAVAILABLE
        if leaving_special:
            if recovering:
                reason, detail = Reason.DATA_RESUMED, f"{reason.value}; {detail}"
            elif s.mode is Mode.ECO:
                reason, detail = idle_reason, f"{reason.value}; {detail}"
            elif s.mode is None:
                reason, detail = Reason.SESSION_START, f"{reason.value}; {detail}"
            return self._transition(at, wanted, reason, detail, record.index)

        if wanted is not s.mode and not bypass_hold and s.mode_since is not None:
            held_s = (at - s.mode_since).total_seconds()
            if held_s < self.settings.min_mode_duration_s:
                # Minimum mode duration not reached: keep current mode, no log entry.
                return Decision(at, s.mode, s.mode, s.source, reason,
                                f"held {held_s:.0f}s < {self.settings.min_mode_duration_s}s",
                                record.index)
        return self._transition(at, wanted, reason, detail, record.index)

    def _transition(
        self, at: datetime, mode: Mode, reason: Reason, detail: str,
        record_index: int | None,
    ) -> Decision:
        s = self._s
        previous = s.mode
        if mode is not previous:
            s.mode = mode
            s.mode_since = at
        return Decision(at, mode, previous, s.source, reason, detail, record_index)

    @staticmethod
    def _relabel(d: Decision, reason: Reason, detail: str) -> Decision:
        return Decision(d.timestamp, d.mode, d.previous_mode, d.source, reason, detail,
                        d.record_index)


def _join(*parts: str) -> str:
    return "; ".join(p for p in parts if p)

