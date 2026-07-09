"""PID 闭环控制器。

提供标准 PID + anti-windup + 死区处理，用于牵引与制动阶段的平滑控车。
"""

from __future__ import annotations

from sim_engine.core.config import PidParams


class PIDController:
    """标准 PID 控制器，带 anti-windup 和死区。

    用法::

        pid = PIDController(params)
        for each step:
            output = pid.compute(setpoint, actual_value, dt)
    """

    def __init__(self, params: PidParams):
        self._p = params
        self.reset()

    # -- 属性（便于测试验证） -------------------------------------------

    @property
    def integral(self) -> float:
        """当前积分累积值。"""
        return self._integral

    @property
    def prev_error(self) -> float:
        """上一步误差。"""
        return self._prev_error

    # -- 核心方法 --------------------------------------------------------

    def compute(self, setpoint: float, pv: float, dt: float) -> float:
        """计算控制输出。

        Args:
            setpoint: 目标值（如目标速度 km/h）。
            pv: 过程变量 / 实际测量值（如实际速度 km/h）。
            dt: 距上次调用的时间步长 (s)。

        Returns:
            控制量，范围 [output_min, output_max]，正=牵引，负=制动。
        """
        error = setpoint - pv

        # --- 比例项 ---
        p_term = self._p.kp * error

        # --- 微分项：死区边缘去振 ---
        if abs(error) <= self._p.deadband_v:
            d_term = 0.0
        elif dt > 0:
            d_term = self._p.kd * (error - self._prev_error) / dt
        else:
            d_term = 0.0

        # --- 积分项 + anti-windup：条件积分法 ---
        # 先计算不含积分增量的临时输出，若已饱和则不累积积分
        raw_no_i = p_term + d_term
        tentative = raw_no_i + self._p.ki * (self._integral + error * dt)

        if self._p.output_min < tentative < self._p.output_max:
            # 未饱和，正常累积积分
            self._integral += error * dt
        # 饱和时不累积（条件积分 anti-windup）

        self._integral = self._clamp(
            self._integral, -self._p.integral_max, self._p.integral_max
        )
        i_term = self._p.ki * self._integral

        # --- 合成输出 ---
        raw = p_term + i_term + d_term
        output = self._clamp(raw, self._p.output_min, self._p.output_max)

        self._prev_error = error
        return output

    def reset(self) -> None:
        """复位积分与微分记忆（阶段切换时调用）。"""
        self._integral = 0.0
        self._prev_error = 0.0

    # -- 制动曲线 --------------------------------------------------------

    @staticmethod
    def braking_curve_speed(remaining_m: float, comfort_decel: float) -> float:
        """计算制动曲线上当前点的目标速度 (km/h)。

        ``v = sqrt(2 * a * d)``

        Args:
            remaining_m: 距站台中心剩余距离 (m)，≤0 时返回 0。
            comfort_decel: 舒适减速度 (m/s²)。
        """
        if remaining_m <= 0.0:
            return 0.0
        v_ms = (2 * comfort_decel * remaining_m) ** 0.5
        return v_ms * 3.6

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        if value < lo:
            return lo
        if value > hi:
            return hi
        return value
