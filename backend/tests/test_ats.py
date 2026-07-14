"""ATSController 单元测试（recover 默认 + extend 兼容）。"""

from __future__ import annotations

from sim_engine.core.config import AtsConfig
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.models import Timetable, TimetableEntry


def _tt():
    return Timetable("TRAIN_01", [
        TimetableEntry("ST02", planned_arrival=100.0, planned_departure=130.0),
    ])


def test_planned_departure_lookup():
    tt = _tt()
    assert tt.planned_departure("ST02") == 130.0
    assert tt.planned_departure("ST99") is None


def test_on_time_dwell_unchanged():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover"), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=100.0)
    assert adjusted == 30.0
    assert dev is not None
    assert dev.delay_arrival == 0.0


def test_late_shortens_dwell_recover():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", min_dwell_time=15.0), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 15.0
    assert dev.delay_arrival == 30.0


def test_late_clamped_by_min_dwell():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", min_dwell_time=15.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=200.0)
    assert adjusted == 15.0


def test_early_holds_to_planned_departure():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", max_dwell_time=300.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=80.0)
    # planned_departure - actual = 50，未超 nominal+margin(60)
    assert adjusted == 50.0


def test_early_hold_capped_by_margin():
    ats = ATSController(
        AtsConfig(dwell_adjust_mode="recover", early_hold_margin=30.0, max_dwell_time=300.0),
        _tt(),
    )
    # planned_dep - arrival = 80 > nominal(30) + margin(30)
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=50.0)
    assert adjusted == 60.0


def test_extend_mode_still_adds_delay():
    ats = ATSController(AtsConfig(dwell_adjust_mode="extend"), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 60.0


def test_unknown_station_returns_nominal():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover"), _tt())
    adjusted, dev = ats.adjust_dwell("ST99", nominal_dwell=25.0, actual_arrival=100.0)
    assert adjusted == 25.0
    assert dev is None
