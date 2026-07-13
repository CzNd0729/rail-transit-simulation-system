"""持续派车集成测试。"""

from __future__ import annotations

from dataclasses import replace

from sim_engine.orchestrator import Orchestrator
from sim_engine.signaling.models import DispatchConfig


def _as_fixed(orch: Orchestrator) -> None:
    assert orch._service_timetable is not None
    orch._service_timetable = replace(
        orch._service_timetable,
        dispatch=replace(orch._service_timetable.dispatch, mode="fixed"),
    )
    orch._fleet_scheduler = None
    orch._turnback = None
    orch.reset()


def test_continuous_first_train_at_zero():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert snap is not None
    assert snap["data"]["trains"][0]["id"] == "TRAIN_01"
    assert snap["data"]["trains"][0]["direction"] == "down"


def test_continuous_second_train_held_then_dispatched():
    """第二班在 150s 到点；若始发未清空则阻塞，清空后按 150s 班次补发。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    train02 = None
    for _ in range(20000):
        orch.step_once()
        for run in orch.trains:
            if run.train_id == "TRAIN_02":
                train02 = run
                break
        if train02 is not None:
            break
    assert train02 is not None
    assert train02.spawn_time == 150.0


def test_continuous_dispatch_count_grows():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 600.0
    orch.reset()
    orch.start()
    for _ in range(6000):
        orch.step_once()
    assert len(orch.trains) >= 4


def test_fixed_mode_train_count_fallback():
    orch = Orchestrator.from_config_dir()
    _as_fixed(orch)
    orch.sim_params.train_count = 1
    orch.sim_params.bidirectional = False
    orch.start()
    snap = orch.step_once()
    assert snap is not None
    assert len(snap["data"]["trains"]) == 1
