"""Controller settings and their validation rules (FR-05, FR-07)."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field, model_validator


class ControlSettings(BaseModel):
    """Demonstration assumptions, not regulatory limits. All durations use dataset time."""

    model_config = {"frozen": True}

    lower_bound_c: float = Field(20.0, description="Heat below this temperature (deg C)")
    upper_bound_c: float = Field(24.0, description="Cool above this temperature (deg C)")
    hysteresis_c: float = Field(0.5, description="Heating stops at lower+h, cooling at upper-h")
    min_mode_duration_s: int = Field(300, description="Minimum time in a thermostat mode")
    vacancy_delay_s: int = Field(600, description="Continuous vacancy before Eco")
    baseline_start: time = Field(time(8, 0), description="Fixed schedule start (daily)")
    baseline_end: time = Field(time(18, 0), description="Fixed schedule end (daily)")

    @model_validator(mode="after")
    def _validate(self) -> ControlSettings:
        errors: list[str] = []
        if self.lower_bound_c >= self.upper_bound_c:
            errors.append("lower_bound_c must be less than upper_bound_c")
        if self.min_mode_duration_s < 0:
            errors.append("min_mode_duration_s must not be negative")
        if self.vacancy_delay_s < 0:
            errors.append("vacancy_delay_s must not be negative")
        if self.hysteresis_c < 0:
            errors.append("hysteresis_c must not be negative")
        elif (
            self.lower_bound_c < self.upper_bound_c
            and self.hysteresis_c >= (self.upper_bound_c - self.lower_bound_c) / 2
        ):
            errors.append("hysteresis_c must be less than half the comfort-band width")
        if self.baseline_start >= self.baseline_end:
            errors.append("baseline_start must be earlier than baseline_end")
        if errors:
            raise ValueError("; ".join(errors))
        return self

    @property
    def heating_stop_c(self) -> float:
        return self.lower_bound_c + self.hysteresis_c

    @property
    def cooling_stop_c(self) -> float:
        return self.upper_bound_c - self.hysteresis_c
