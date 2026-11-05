"""Pure thermostat rule with hysteresis (FR-04, FR-05). No timers, no occupancy."""

from __future__ import annotations

from app.control.modes import Mode, Reason
from app.control.settings import ControlSettings


def thermostat_decision(
    current: Mode, temperature_c: float, settings: ControlSettings
) -> tuple[Mode, Reason]:
    """Return the mode the thermostat wants given the current mode and temperature.

    - HEATING continues until temperature >= lower + hysteresis.
    - COOLING continues until temperature <= upper - hysteresis.
    - Otherwise: heat below lower bound, cool above upper bound, else standby.
    Heating and cooling can never both be requested: the result is a single mode.
    """
    if current is Mode.HEATING:
        if temperature_c < settings.heating_stop_c:
            return Mode.HEATING, Reason.BELOW_LOWER_BOUND
        return _fresh(temperature_c, settings, stop_reason=Reason.HEATING_SETPOINT_REACHED)
    if current is Mode.COOLING:
        if temperature_c > settings.cooling_stop_c:
            return Mode.COOLING, Reason.ABOVE_UPPER_BOUND
        return _fresh(temperature_c, settings, stop_reason=Reason.COOLING_SETPOINT_REACHED)
    return _fresh(temperature_c, settings, stop_reason=Reason.WITHIN_COMFORT_RANGE)


def _fresh(
    temperature_c: float, settings: ControlSettings, stop_reason: Reason
) -> tuple[Mode, Reason]:
    if temperature_c < settings.lower_bound_c:
        return Mode.HEATING, Reason.BELOW_LOWER_BOUND
    if temperature_c > settings.upper_bound_c:
        return Mode.COOLING, Reason.ABOVE_UPPER_BOUND
    return Mode.STANDBY, stop_reason
