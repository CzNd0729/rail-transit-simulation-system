"""多车步进与 snapshot 输出测试。"""

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


def test_delayed_spawn_adds_second_train_to_snapshot():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.sim_params.train_count = 2
    orch.sim_params.departure_interval = 2.0
    _as_fixed(orch)
    orch.start()
    snap = None
    for _ in range(25):
        snap = orch.step_once()
    assert snap is not None
    train_ids = [t["id"] for t in snap["data"]["trains"]]
    assert "TRAIN_01" in train_ids
    assert "TRAIN_02" in train_ids
    assert len(train_ids) == 2


def test_multi_train_timetable_offset_by_spawn():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.sim_params.train_count = 3
    orch.sim_params.departure_interval = 120.0
    _as_fixed(orch)
    assert orch.trains[2].ats._timetable.planned_arrival("ST02") == 114.0 + 240.0


def test_multi_train_third_train_progresses_past_st02():
    """TRAIN_03 不应因 ATS 全局时刻表误判而在 ST02 长期停站。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.sim_params.train_count = 3
    orch.sim_params.departure_interval = 120.0
    _as_fixed(orch)
    orch.start()
    for _ in range(12000):
        orch.step_once()
    assert orch.trains[2].state.position > 2000.0


def test_snapshot_includes_train_direction():
    orch = Orchestrator.from_config_dir()
    _as_fixed(orch)
    orch.sim_params.bidirectional = False
    orch.start()
    snap = orch.step_once()
    assert snap["data"]["trains"][0]["direction"] == "up"


def test_single_train_count_one_unchanged_snapshot_shape(orchestrator):
    orch = orchestrator
    _as_fixed(orch)
    orch.sim_params.train_count = 1
    orch.start()
    snap = orch.step_once()
    assert len(snap["data"]["trains"]) == 1
    assert len(snap["data"]["signaling"]["controlCommands"]) == 1
