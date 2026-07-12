"""TrainRun 初始化与向后兼容属性测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_orchestrator_creates_multiple_train_runs():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 3
    orch.reset()
    assert len(orch.trains) == 3
    assert orch.trains[0].train_id == "TRAIN_01"
    assert orch.trains[1].train_id == "TRAIN_02"
    assert orch.trains[0].active is True
    assert orch.trains[1].active is False
    assert orch.trains[1].spawn_time == orch.sim_params.departure_interval


def test_backward_compat_train_state_property():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    assert orch.train_state is orch.trains[0].state
    orch.train_state.speed = 42.0
    assert orch.trains[0].state.speed == 42.0
