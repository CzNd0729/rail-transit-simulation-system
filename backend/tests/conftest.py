"""共享测试 fixtures。"""

from __future__ import annotations

import pytest

from sim_engine.orchestrator import Orchestrator


@pytest.fixture
def orchestrator() -> Orchestrator:
    """返回一个初始化的编排器实例（单车回归隔离）。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.sim_params.train_count = 1
    orch.reset()
    return orch