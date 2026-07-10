"""共享测试 fixtures。"""

from __future__ import annotations

import pytest

from sim_engine.orchestrator import Orchestrator


@pytest.fixture
def orchestrator() -> Orchestrator:
    """返回一个初始化的编排器实例（使用默认配置）。"""
    return Orchestrator.from_config_dir()