from app.control.modes import ControlSource, Mode, Reason
from app.control.records import Decision
from app.control.runtime import RuntimeAccumulator
from tests.helpers import rec


def dec(mode, source=ControlSource.AUTO):
    return Decision(rec(0).timestamp, mode, None, source, Reason.SESSION_START)


def test_counts_heating_and_cooling_and_reduction():
    acc = RuntimeAccumulator()
    acc.add_interval(rec(0), rec(1), dec(Mode.HEATING), dec(Mode.HEATING))
    acc.add_interval(rec(1), rec(2), dec(Mode.ECO), dec(Mode.COOLING))
    assert acc.proposed.active_s == 60 and acc.baseline.active_s == 120
    assert acc.reduction_pct == 50.0


def test_reduction_is_none_when_baseline_zero():
    acc = RuntimeAccumulator()
    acc.add_interval(rec(0), rec(1), dec(Mode.STANDBY), dec(Mode.STANDBY))
    assert acc.reduction_pct is None


def test_gaps_invalid_and_manual_are_excluded():
    acc = RuntimeAccumulator()
    acc.add_interval(rec(0), rec(6), dec(Mode.HEATING), dec(Mode.HEATING))
    acc.add_interval(rec(6), rec(7, valid=False), dec(Mode.HEATING), dec(Mode.HEATING))
    acc.add_interval(rec(7), rec(8), dec(Mode.HEATING, ControlSource.MANUAL),
                     dec(Mode.HEATING))
    assert acc.excluded_gap_s == 360
    assert acc.excluded_invalid_s == 60
    assert acc.excluded_manual_s == 60
    assert acc.proposed.active_s == 0 and acc.baseline.active_s == 0
