import pytest

from app.control.modes import Mode
from app.control.settings import ControlSettings
from app.control.thermostat import thermostat_decision

S = ControlSettings()


@pytest.mark.parametrize("current,temp,expected", [
    (Mode.STANDBY, 19.99, Mode.HEATING),
    (Mode.STANDBY, 20.0, Mode.STANDBY),     # boundary is not "below"
    (Mode.STANDBY, 24.0, Mode.STANDBY),
    (Mode.STANDBY, 24.01, Mode.COOLING),
    (Mode.HEATING, 20.49, Mode.HEATING),    # hysteresis keeps heating
    (Mode.HEATING, 20.5, Mode.STANDBY),     # heating stops at 20.5
    (Mode.COOLING, 23.51, Mode.COOLING),
    (Mode.COOLING, 23.5, Mode.STANDBY),     # cooling stops at 23.5
])
def test_hysteresis_boundaries(current, temp, expected):
    assert thermostat_decision(current, temp, S)[0] is expected
