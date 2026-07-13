"""FleetScheduler 持续派车测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sim_engine.signaling.fleet_scheduler import FleetScheduler, origin_clearance_ok
from sim_engine.signaling.models import DispatchConfig, ServiceTimetable
from sim_engine.signaling.timetable_loader import load_service_timetable

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


def _single_origin_service() -> ServiceTimetable:
    return ServiceTimetable(
        line_name="test",
        turnback_time_s=150.0,
        turnback_switch_down="SW04",
        turnback_switch_up="SW01",
        dispatch=DispatchConfig(
            mode="continuous",
            headway_s=150.0,
            min_origin_clearance_m=500.0,
        ),
        leg_templates={},
    )


def test_origin_clearance_empty_line():
    assert origin_clearance_ok([], 0.0, "down", 500.0) is True


def test_origin_clearance_blocked_down():
    runs = [_FakeRun(True, "down", _FakeState(300.0, "down"))]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is False


def test_origin_clearance_ok_down():
    runs = [_FakeRun(True, "down", _FakeState(600.0, "down"))]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is True


def test_origin_clearance_blocked_up():
    runs = [_FakeRun(True, "up", _FakeState(18300.0, "up"))]
    assert origin_clearance_ok(runs, 18600.0, "up", 500.0) is False


def test_scheduler_dispatches_on_headway():
    svc = _single_origin_service()
    sched = FleetScheduler(svc)
    created: list[tuple[str, float, str]] = []

    def create(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_legs: tuple[str, ...],
        start_pos: float,
    ) -> None:
        created.append((train_id, spawn_time, direction))

    r1 = sched.tick(0.0, [], create)
    assert r1.dispatched_ids == ["TRAIN_01"]
    assert created == [("TRAIN_01", 0.0, "down")]
    assert sched.next_departure_time == 150.0

    r2 = sched.tick(150.0, [], create)
    assert r2.dispatched_ids == ["TRAIN_02"]
    assert created[1] == ("TRAIN_02", 150.0, "down")


def test_scheduler_dual_origin_at_zero():
    svc = load_service_timetable(
        CONFIG / "timetable.yaml",
        {"ST01": 0.0, "ST24": 18600.0},
    )
    sched = FleetScheduler(svc, {"ST01": 0.0, "ST24": 18600.0})
    created: list[str] = []

    def create(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_legs: tuple[str, ...],
        start_pos: float,
    ) -> None:
        created.append(train_id)

    r = sched.tick(0.0, [], create)
    assert set(r.dispatched_ids) == {"TRAIN_D01", "TRAIN_U01"}
    assert len(created) == 2


def test_scheduler_holds_when_blocked_then_catches_up():
    svc = _single_origin_service()
    sched = FleetScheduler(svc)
    created: list[tuple[str, float]] = []

    def create(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_legs: tuple[str, ...],
        start_pos: float,
    ) -> None:
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
