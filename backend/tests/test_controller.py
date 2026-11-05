from app.control.controller import Controller, Policy
from app.control.modes import ControlSource, Mode, Reason
from app.control.settings import ControlSettings
from tests.helpers import T0, rec

S = ControlSettings()


def run(ctrl, records):
    return [ctrl.step(r) for r in records]


def test_first_record_heats_when_cold_and_occupied():
    d = Controller(S).step(rec(0, temp=19.0))
    assert d.mode is Mode.HEATING and d.reason is Reason.SESSION_START


def test_min_mode_duration_holds_thermostat_transition():
    c = Controller(S)
    run(c, [rec(0, temp=19.0)])                       # HEATING at t=0
    assert c.step(rec(2, temp=21.0)).mode is Mode.HEATING   # 2 min < 5 min hold
    assert c.step(rec(5, temp=21.0)).mode is Mode.STANDBY   # hold satisfied


def test_heating_and_cooling_never_simultaneous():
    c = Controller(S)
    seen = set()
    for m in range(120):
        d = c.step(rec(m, temp=19 if (m // 10) % 2 else 25))
        assert d.mode in {Mode.HEATING, Mode.COOLING, Mode.STANDBY}  # one mode at a time
        seen.add(d.mode)
    assert {Mode.HEATING, Mode.COOLING} <= seen


def test_vacancy_delay_enters_eco_and_bypasses_hold():
    c = Controller(S)
    c.step(rec(0, temp=19.0, occ=1))                  # HEATING
    for m in range(1, 10):
        assert c.step(rec(m, temp=19.0, occ=0)).mode is Mode.HEATING
    d = c.step(rec(11, temp=19.0, occ=0))             # 10 min vacant since t=1
    assert d.mode is Mode.ECO and d.reason is Reason.VACANCY_TIMEOUT


def test_reoccupancy_resumes_thermostat_immediately():
    c = Controller(S)
    for m in range(0, 12):
        c.step(rec(m, temp=22.0, occ=0))
    assert c.mode is Mode.ECO
    d = c.step(rec(12, temp=19.0, occ=1))
    assert d.mode is Mode.HEATING and d.reason is Reason.REOCCUPIED


def test_brief_vacancy_resets_timer():
    c = Controller(S)
    for m in range(0, 9):
        c.step(rec(m, occ=0))
    c.step(rec(9, occ=1))
    for m in range(10, 19):
        assert c.step(rec(m, occ=0)).mode is not Mode.ECO


def test_manual_override_persists_until_auto():
    c = Controller(S)
    c.step(rec(0, temp=22.0))
    d = c.set_manual(Mode.COOLING, T0, "operator test")
    assert d.mode is Mode.COOLING and d.source is ControlSource.MANUAL
    for m in range(1, 30):  # including long vacancy
        assert c.step(rec(m, temp=19.0, occ=0)).mode is Mode.COOLING
    d = c.release_manual(T0)
    assert d.source is ControlSource.AUTO and d.mode is Mode.ECO
    assert d.reason is Reason.MANUAL_RELEASED


def test_invalid_input_overrides_manual_then_recovers():
    c = Controller(S)
    c.step(rec(0, temp=22.0))
    c.set_manual(Mode.HEATING, T0)
    d = c.step(rec(1, valid=False))
    assert d.mode is Mode.DATA_UNAVAILABLE and d.reason is Reason.INVALID_INPUT
    assert c.step(rec(2, temp=22.0)).mode is Mode.HEATING


def test_gap_over_five_minutes_is_data_unavailable():
    c = Controller(S)
    c.step(rec(0, temp=22.0))
    assert c.step(rec(5, temp=22.0)).mode is Mode.STANDBY       # exactly 5 min: not a gap
    d = c.step(rec(10.5, temp=22.0))                            # 5.5 min gap
    assert d.mode is Mode.DATA_UNAVAILABLE and d.reason is Reason.DATA_GAP
    d = c.step(rec(11.5, temp=19.0))
    assert d.mode is Mode.HEATING and d.reason is Reason.DATA_RESUMED


def test_baseline_schedule_ignores_occupancy():
    c = Controller(S, Policy.SCHEDULE)
    assert c.step(rec(0, temp=19.0, occ=0)).mode is Mode.HEATING   # 09:00 inside window
    late = rec(9 * 60 + 1, temp=19.0, occ=1)                        # 18:01 outside window
    assert c.step(late).mode is Mode.DATA_UNAVAILABLE              # gap first
    assert c.step(rec(9 * 60 + 2, temp=19.0, occ=1)).mode is Mode.ECO


def test_replay_is_deterministic():
    records = [rec(m, temp=19 + (m % 50) / 7, occ=int((m // 15) % 2)) for m in range(300)]

    def trace():
        c = Controller(S)
        return [(d.mode, d.reason, d.detail) for d in run(c, records)]

    assert trace() == trace()
