"""Timetable v2 数据模型与加载测试。"""

from __future__ import annotations

from pathlib import Path

from sim_engine.signaling.models import DispatchConfig, Timetable, TimetableEntry

CONFIG = Path(__file__).resolve().parents[1] / "sim_engine" / "config"


def test_dispatch_config_defaults():
    cfg = DispatchConfig()
    assert cfg.mode == "continuous"
    assert cfg.headway_s == 150.0
    assert cfg.min_origin_clearance_m == 500.0


def test_timetable_absolute_offset():
    tt = Timetable(
        train_id="TRAIN_01",
        entries=[
            TimetableEntry("ST01", planned_arrival=0.0, planned_departure=35.0),
            TimetableEntry("ST02", planned_arrival=114.0, planned_departure=139.0),
        ],
    )
    abs_tt = tt.with_absolute_times(300.0)
    assert abs_tt.planned_arrival("ST01") == 300.0
    assert abs_tt.planned_arrival("ST02") == 414.0


def test_load_peak_service_timetable():
    from sim_engine.signaling.timetable_loader import load_service_timetable

    svc = load_service_timetable(CONFIG / "timetable.yaml")
    assert svc.dispatch.mode == "continuous"
    assert svc.dispatch.headway_s == 150.0
    assert "down" in svc.leg_templates
    assert len(svc.leg_templates["down"].entries) == 24


def test_materialize_trip_legs():
    from sim_engine.signaling.timetable_loader import (
        load_service_timetable,
        materialize_trip_timetables,
    )

    svc = load_service_timetable(CONFIG / "timetable.yaml")
    legs = materialize_trip_timetables(svc, "TRAIN_01")
    assert len(legs) == 2
    assert legs[0].planned_arrival("ST24") == 1995.0
    assert legs[1].entries[0].station_id == "ST24"
