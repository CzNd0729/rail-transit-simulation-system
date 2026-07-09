"""P-only 微调控制器。

前馈制动方案中，PID 只做微调修正，不再作为主控。
去除 I/D/deadband/anti-windup，只用 P 项。
"""

from __future__ import annotations

import math


class PIDController:
    """P-only 控制器，用于制动阶段的微调修正。

    用法::

        pid = PIDController(kp=0.02)
        trim = pid.compute(error)   # error = v_actual - v_target
        brake_level = clamp(ff + trim, 0, 1)
    """

    def __init__(self, kp: float):
        self.kp = kp

    def compute(self, error: float) -> float:
        """计算 P 修正量。

        Args:
            error: 归一化误差（无量纲），如 (v_actual - v_target) / v_target。

        Returns:
            P 修正量，范围 [-kp, kp]。
        """
        return self.kp * error

    def reset(self) -> None:
        """P-only 控制器无状态，无需 reset。"""

    @staticmethod
    def braking_curve_speed(remaining_m: float, comfort_decel: float) -> float:
        """计算制动曲线上当前点的目标速度 (km/h)。

        ``v = sqrt(2 * a * d)``
        """
        if remaining_m <= 0.0:
            return 0.0
        v_ms = math.sqrt(2 * comfort_decel * remaining_m)
        return v_ms * 3.6