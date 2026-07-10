"""ManualDriveController 单元测试。"""

from __future__ import annotations

import pytest

from sim_engine.signaling.manual_drive import ManualDriveController
from sim_engine.vehicle.models import ControlCommands


class TestManualDriveController:
    """紧急制动开关 + get_commands 叠加逻辑。"""

    def test_eb_activated_overrides_commands(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, brake_level=0.0)

        ctrl.set_emergency_brake(True)
        result = ctrl.get_commands(base)

        assert result.emergency_brake is True
        assert result.traction_level == 0.0
        assert result.brake_level == 0.0

    def test_eb_deactivated_passthrough(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, brake_level=0.0)

        ctrl.set_emergency_brake(True)
        ctrl.set_emergency_brake(False)
        result = ctrl.get_commands(base)

        assert result is base  # 返回同一对象，未修改

    def test_eb_initial_state_is_false(self):
        ctrl = ManualDriveController()
        assert ctrl.emergency_brake is False

    def test_eb_preserves_phase(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, phase="coasting")

        ctrl.set_emergency_brake(True)
        result = ctrl.get_commands(base)

        assert result.phase == "coasting"

    def test_eb_toggle_twice(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=0.5, brake_level=0.3)

        ctrl.set_emergency_brake(True)
        r1 = ctrl.get_commands(base)
        assert r1.emergency_brake is True

        ctrl.set_emergency_brake(False)
        r2 = ctrl.get_commands(base)
        assert r2 is base


# --- 编排器集成测试 ---


class TestOrchestratorEBIntegration:
    """验证手动紧急制动在编排器层面的完整链路。"""

    def test_eb_activates_max_brake_force(self, orchestrator):
        """EB 激活后一步 → 制动力 = max_brake_force，速度下降。"""
        orch = orchestrator
        orch.start()

        # 先跑几步让列车有速度
        for _ in range(50):
            orch.step_once()
        assert orch.train_state.speed > 1.0
        speed_before = orch.train_state.speed

        # 触发紧急制动
        orch.set_emergency_brake(True)
        result = orch.step_once()

        assert result is not None
        assert result["data"]["signaling"]["controlCommands"][0]["emergencyBrake"] is True
        assert result["data"]["trains"][0]["brakeForce"] == 260000.0  # max_brake_force
        assert result["data"]["trains"][0]["speed"] < speed_before  # 制动后速度下降

    def test_eb_clears_on_reset(self, orchestrator):
        """reset() 后紧急制动状态清除。"""
        orch = orchestrator
        orch.set_emergency_brake(True)
        assert orch.manual_driver.emergency_brake is True

        orch.reset()
        assert orch.manual_driver.emergency_brake is False