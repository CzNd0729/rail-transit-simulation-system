"""共享测试 fixtures。"""

from __future__ import annotations

from pathlib import Path

import pytest

from sim_engine.orchestrator import Orchestrator
from sim_engine.signaling.timetable_loader import load_service_timetable

LEGACY_TIMETABLE = (
    Path(__file__).resolve().parents[1] / "sim_engine" / "config" / "timetable_legacy.yaml"
)


def use_fixed_legacy_timetable(orch: Orchestrator) -> None:
    """切换为 fixed + 三站 legacy 时刻表（回归测试用）。"""
    orch._timetable_path = LEGACY_TIMETABLE
    orch._service_timetable = load_service_timetable(LEGACY_TIMETABLE)
    orch._fleet_scheduler = None
    orch._turnback = None
    orch.reset()


@pytest.fixture
def orchestrator() -> Orchestrator:
    """返回 fixed legacy 单车编排器（回归隔离）。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.bidirectional = False
    orch.sim_params.train_count = 1
    use_fixed_legacy_timetable(orch)
    return orch
