"""手动驾驶控制器（迭代一仅实现紧急制动，迭代三扩展完整手动驾驶）。"""

from __future__ import annotations

from dataclasses import dataclass

from sim_engine.vehicle.models import ControlCommands


@dataclass
class ManualDriveController:
    """在自动信号指令之上叠加手动控制指令。

    紧急制动优先级最高——触发时覆盖所有信号输出。
    """

    emergency_brake: bool = False

    def set_emergency_brake(self, active: bool) -> None:
        """设置/解除紧急制动（锁定式，需手动解除）。"""
        self.emergency_brake = active

    def get_commands(self, base_cmd: ControlCommands) -> ControlCommands:
        """在自动信号指令上叠加手动指令。

        当紧急制动激活时，强制覆盖：
        - emergency_brake = True
        - traction_level = 0（牵引归零）
        - brake_level = 0（让 dynamics.py 的 emergency_brake 分支用 max_brake_force）
        """
        if not self.emergency_brake:
            return base_cmd
        return ControlCommands(
            traction_level=0.0,
            brake_level=0.0,
            emergency_brake=True,
            phase=base_cmd.phase,
        )