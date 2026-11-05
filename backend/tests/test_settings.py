import pytest
from pydantic import ValidationError

from app.control.settings import ControlSettings


def test_defaults_match_srs():
    s = ControlSettings()
    assert (s.lower_bound_c, s.upper_bound_c, s.hysteresis_c) == (20.0, 24.0, 0.5)
    assert s.min_mode_duration_s == 300 and s.vacancy_delay_s == 600
    assert s.heating_stop_c == 20.5 and s.cooling_stop_c == 23.5


@pytest.mark.parametrize("kwargs", [
    {"lower_bound_c": 24, "upper_bound_c": 24},
    {"lower_bound_c": 25, "upper_bound_c": 24},
    {"min_mode_duration_s": -1},
    {"vacancy_delay_s": -5},
    {"hysteresis_c": 2.0},          # == half of 4-degree band
    {"hysteresis_c": 2.5},
])
def test_invalid_settings_rejected(kwargs):
    with pytest.raises(ValidationError):
        ControlSettings(**kwargs)


def test_hysteresis_just_below_half_band_accepted():
    assert ControlSettings(hysteresis_c=1.99).hysteresis_c == 1.99
