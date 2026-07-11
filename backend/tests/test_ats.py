"""ATSController 单元测试（策略 B）。"""

from __future__ import annotations

from sim_engine.core.config import AtsConfig
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.models import Timetable, TimetableEntry


def _tt():
    return Timetable("TRAIN_01", [
        TimetableEntry("ST02", planned_arrival=100.0, planned_departure=130.0),
    ])


def test_on_time_dwell_unchanged():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=100.0)
    assert adjusted == 30.0
    assert dev is not None
    assert dev.delay_arrival == 0.0


def test_late_extends_dwell():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 60.0
    assert dev.delay_arrival == 30.0


def test_early_does_not_shorten():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=80.0)
    assert adjusted == 30.0


def test_clamped_by_max_dwell():
    ats = ATSController(AtsConfig(max_dwell_time=45.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=200.0)
    assert adjusted == 45.0


def test_unknown_station_returns_nominal():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, dev = ats.adjust_dwell("ST99", nominal_dwell=25.0, actual_arrival=100.0)
    assert adjusted == 25.0
    assert dev is None
