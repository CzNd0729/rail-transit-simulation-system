"""SIG-07 追踪间隔 enforcement 测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator
from tests.conftest import use_fixed_legacy_timetable


def test_interval_violation_triggers_eb_on_following_train():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.vehicle.params.direction = "down"
    orch.sim_params.train_count = 2
    orch.sim_params.departure_interval = 0.0
    orch.sim_params.signal.following_min_interval = 500.0
    use_fixed_legacy_timetable(orch)
    orch.trains[0].active = True
    orch.trains[1].active = True
    orch.trains[0].state.position = 2000.0
    orch.trains[0].state.direction = "down"
    orch.trains[1].state.direction = "down"
    orch.trains[0].state.speed = 40.0
    orch.trains[1].state.position = 1600.0  # 间隔 400m < 500m
    orch.trains[1].state.speed = 40.0
    orch.start()
    snap = orch.step_once()
    cmds = {c["trainId"]: c for c in snap["data"]["signaling"]["controlCommands"]}
    assert cmds["TRAIN_02"]["emergencyBrake"] is True
    intervals = snap["data"]["signaling"]["trainIntervals"]
    assert any(i["trainId"] == "TRAIN_02" and i["safe"] is False for i in intervals)


def test_single_train_no_train_intervals(orchestrator):
    orch = orchestrator
    orch.sim_params.train_count = 1
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert snap["data"]["signaling"].get("trainIntervals", []) == []
