"""FleetScheduler 持续派车测试。"""

from __future__ import annotations

from dataclasses import dataclass

from sim_engine.signaling.fleet_scheduler import FleetScheduler, origin_clearance_ok
from sim_engine.signaling.models import DispatchConfig, ServiceTimetable, TimetableLegTemplate
from sim_engine.signaling.timetable_loader import load_service_timetable
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "sim_engine" / "config"


@dataclass
class _FakeState:
    position: float
    direction: str


@dataclass
class _FakeRun:
    active: bool
    direction: str
    state: _FakeState


def test_origin_clearance_empty_line():
    assert origin_clearance_ok([], 0.0, "down", 500.0) is True


def test_origin_clearance_blocked_down():
    runs = [_FakeRun(True, "down", _FakeState(300.0, "down"))]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is False


def test_origin_clearance_ok_down():
    runs = [_FakeRun(True, "down", _FakeState(600.0, "down"))]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is True


def test_scheduler_dispatches_on_headway():
    svc = load_service_timetable(CONFIG / "timetable.yaml")
    sched = FleetScheduler(svc)
    created: list[tuple[str, float]] = []

    def create(train_id: str, spawn_time: float) -> None:
        created.append((train_id, spawn_time))

    r1 = sched.tick(0.0, [], create)
    assert r1.dispatched_ids == ["TRAIN_01"]
    assert created == [("TRAIN_01", 0.0)]
    assert sched.next_departure_time == 150.0

    r2 = sched.tick(150.0, [], create)
    assert r2.dispatched_ids == ["TRAIN_02"]
    assert created[1] == ("TRAIN_02", 150.0)


def test_scheduler_holds_when_blocked_then_catches_up():
    svc = ServiceTimetable(
        line_name="test",
        turnback_time_s=150.0,
        turnback_switch_down="SW04",
        turnback_switch_up="SW01",
        dispatch=DispatchConfig(headway_s=150.0, min_origin_clearance_m=500.0),
        leg_templates={},
    )
    sched = FleetScheduler(svc)
    created: list[tuple[str, float]] = []

    def create(train_id: str, spawn_time: float) -> None:
        created.append((train_id, spawn_time))

    sched.tick(0.0, [], create)
    blocked_runs = [_FakeRun(True, "down", _FakeState(300.0, "down"))]
    r_block = sched.tick(150.0, blocked_runs, create)
    assert r_block.dispatched_ids == []
    assert r_block.blocked is True
    assert sched.next_departure_time == 150.0

    clear_runs = [_FakeRun(True, "down", _FakeState(600.0, "down"))]
    r_resume = sched.tick(200.0, clear_runs, create)
    assert r_resume.dispatched_ids == ["TRAIN_02"]
    assert created[1] == ("TRAIN_02", 150.0)
    assert sched.next_departure_time == 300.0
