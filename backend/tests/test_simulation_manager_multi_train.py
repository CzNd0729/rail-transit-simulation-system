"""SimulationManager 多车 API 测试。"""

from __future__ import annotations

import pytest

from sim_engine.services.simulation_manager import SimulationManager
from sim_engine.ws.manager import WebSocketConnectionManager


@pytest.fixture
def manager():
    return SimulationManager(WebSocketConnectionManager())


def test_get_status_train_count(manager):
    manager.orchestrator.sim_params.train_count = 3
    status = manager.get_status()
    assert status["trainCount"] == 3


def test_get_params_departure_interval(manager):
    manager.orchestrator.sim_params.departure_interval = 90.0
    params = manager.get_params()
    assert params["signal"]["departureInterval"] == 90.0


def test_all_trains_finished_requires_full_fleet(manager):
    orch = manager.orchestrator
    orch.sim_params.train_count = 2
    orch.reset()
    assert SimulationManager._all_trains_finished(orch) is False
    orch.trains[0].active = True
    orch.trains[1].active = True
    direction = orch.trains[0].state.direction
    total = orch.track.track.total_length
    terminal = 0.0 if direction == "up" else total - 1.0
    orch.trains[0].state.position = terminal
    orch.trains[0].state.speed = 0.0
    assert SimulationManager._all_trains_finished(orch) is False
    orch.trains[1].state.position = terminal
    orch.trains[1].state.speed = 0.0
    assert SimulationManager._all_trains_finished(orch) is True
