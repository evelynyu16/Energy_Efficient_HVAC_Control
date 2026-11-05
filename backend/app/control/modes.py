"""Controller vocabulary shared by the state machine, API and database."""

from __future__ import annotations

from enum import StrEnum


class Mode(StrEnum):
    HEATING = "HEATING"
    COOLING = "COOLING"
    STANDBY = "STANDBY"
    ECO = "ECO"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


# Modes that count as an active heating/cooling command for runtime totals (FR-10).
ACTIVE_MODES = frozenset({Mode.HEATING, Mode.COOLING})

# Modes an operator may select manually (FR-06). DATA_UNAVAILABLE is never selectable.
MANUAL_MODES = frozenset({Mode.HEATING, Mode.COOLING, Mode.STANDBY, Mode.ECO})


class ControlSource(StrEnum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class Reason(StrEnum):
    """Machine-readable reason attached to every mode change (FR-08)."""

    SESSION_START = "SESSION_START"
    BELOW_LOWER_BOUND = "BELOW_LOWER_BOUND"
    ABOVE_UPPER_BOUND = "ABOVE_UPPER_BOUND"
    HEATING_SETPOINT_REACHED = "HEATING_SETPOINT_REACHED"
    COOLING_SETPOINT_REACHED = "COOLING_SETPOINT_REACHED"
    WITHIN_COMFORT_RANGE = "WITHIN_COMFORT_RANGE"
    VACANCY_TIMEOUT = "VACANCY_TIMEOUT"
    REOCCUPIED = "REOCCUPIED"
    OUTSIDE_SCHEDULE = "OUTSIDE_SCHEDULE"
    INSIDE_SCHEDULE = "INSIDE_SCHEDULE"
    INVALID_INPUT = "INVALID_INPUT"
    DATA_GAP = "DATA_GAP"
    DATA_RESUMED = "DATA_RESUMED"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    MANUAL_RELEASED = "MANUAL_RELEASED"
