from __future__ import annotations

from datetime import datetime, timedelta

from app.control.records import SensorRecord

T0 = datetime(2015, 2, 4, 9, 0)


def rec(minute: float, temp: float = 22.0, occ: int = 1, hum: float = 30.0,
        valid: bool = True, index: int | None = None) -> SensorRecord:
    return SensorRecord(
        index=index if index is not None else int(minute),
        timestamp=T0 + timedelta(minutes=minute),
        temperature_c=temp, humidity_pct=hum, occupancy=occ,
        valid=valid, error=None if valid else "invalid for test",
    )
