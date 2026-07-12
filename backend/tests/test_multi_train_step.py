"""多车步进与 snapshot 输出测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_delayed_spawn_adds_second_train_to_snapshot():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 2
    orch.sim_params.departure_interval = 2.0
    orch.reset()
    orch.start()
    snap = None
    for _ in range(25):
        snap = orch.step_once()
    assert snap is not None
    train_ids = [t["id"] for t in snap["data"]["trains"]]
    assert "TRAIN_01" in train_ids
    assert "TRAIN_02" in train_ids
    assert len(train_ids) == 2


def test_single_train_count_one_unchanged_snapshot_shape(orchestrator):
    orch = orchestrator
    orch.sim_params.train_count = 1
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert len(snap["data"]["trains"]) == 1
    assert len(snap["data"]["signaling"]["controlCommands"]) == 1
