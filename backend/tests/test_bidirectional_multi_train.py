"""双向多车编排测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_bidirectional_creates_six_trains():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = True
    orch.sim_params.train_count = 3
    orch.reset()

    assert len(orch.trains) == 6
    down_ids = [t.train_id for t in orch.trains if t.direction == "down"]
    up_ids = [t.train_id for t in orch.trains if t.direction == "up"]
    assert down_ids == ["TRAIN_D01", "TRAIN_D02", "TRAIN_D03"]
    assert up_ids == ["TRAIN_U01", "TRAIN_U02", "TRAIN_U03"]


def test_bidirectional_first_train_per_direction_active():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = True
    orch.sim_params.train_count = 3
    orch.reset()

    down = [t for t in orch.trains if t.direction == "down"]
    up = [t for t in orch.trains if t.direction == "up"]
    assert down[0].active is True
    assert all(not t.active for t in down[1:])
    assert up[0].active is True
    assert all(not t.active for t in up[1:])


def test_bidirectional_snapshot_has_both_directions():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = True
    orch.sim_params.train_count = 3
    orch.reset()
    orch.start()
    snap = orch.step_once()
    directions = {t["direction"] for t in snap["data"]["trains"]}
    assert directions == {"down", "up"}
