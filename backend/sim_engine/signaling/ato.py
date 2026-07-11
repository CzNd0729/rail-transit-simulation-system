"""ATO 自动驾驶控制器（SIG-05）：制动曲线 + P 微调。"""

from __future__ import annotations

from sim_engine.signaling.pid_controller import PIDController


class ATOController:
    """制动阶段 PID 微调，牵引/惰行仍由 ThreeStageController 阶段机负责。"""

    def __init__(self, kp_brake: float, comfort_decel: float):
        self._comfort_decel = comfort_decel
        self._pid = PIDController(kp=kp_brake)

    def target_speed_on_curve(self, remaining_m: float) -> float:
        return PIDController.braking_curve_speed(remaining_m, self._comfort_decel)

    def compute_brake_level(self, speed_kmh: float, remaining_m: float) -> float:
        """前馈 v²/2d + P 微调，输出 [0,1] 制动级位。"""
        v_target = self.target_speed_on_curve(remaining_m)
        if v_target <= 0.01:
            return 1.0
        ff = min(1.0, max(0.0, (speed_kmh - v_target) / max(v_target, 1.0)))
        error = (speed_kmh - v_target) / max(v_target, 1.0)
        trim = self._pid.compute(error)
        return min(1.0, max(0.0, ff + trim))

    def compute_trim(self, speed_kmh: float, remaining_m: float) -> float:
        """P 微调量，叠加在前馈制动级位上。"""
        v_target = self.target_speed_on_curve(remaining_m)
        if v_target > 1.0:
            error = (speed_kmh - v_target) / v_target
        else:
            error = 0.0
        return self._pid.compute(error)

    def reset(self) -> None:
        self._pid.reset()
