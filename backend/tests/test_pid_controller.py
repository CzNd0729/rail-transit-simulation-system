"""PID 控制器单元测试。

覆盖：比例/积分/微分、anti-windup、reset、制动曲线、死区。
"""

from __future__ import annotations

import math

import pytest

from sim_engine.core.config import PidParams
from sim_engine.signaling.pid_controller import PIDController


# ── helpers ────────────────────────────────────────────────────────

def _default_params(**overrides) -> PidParams:
    d = dict(
        kp=0.08,
        ki=0.002,
        kd=0.01,
        integral_max=0.3,
        output_min=-10.0,
        output_max=10.0,
        comfort_decel=0.8,
        deadband_v=0.3,
    )
    d.update(overrides)
    return PidParams(**d)


# ── 比例项 ─────────────────────────────────────────────────────────

def test_proportional_only_positive_error():
    """正误差 → 正输出（需要牵引/加速）。"""
    pid = PIDController(_default_params(ki=0.0, kd=0.0))
    # setpoint > pv → error > 0 → 正输出
    out = pid.compute(setpoint=60.0, pv=40.0, dt=0.1)
    assert out == pytest.approx(0.08 * 20.0)  # kp=0.08, error=20


def test_proportional_only_negative_error():
    """负误差 → 负输出（需要制动/减速）。"""
    # 不覆盖 output_min，使用默认宽范围以验证原始 P 值
    pid = PIDController(_default_params(ki=0.0, kd=0.0))
    out = pid.compute(setpoint=40.0, pv=60.0, dt=0.1)
    assert out == pytest.approx(0.08 * (-20.0))


def test_proportional_output_clamped():
    """输出不超出 [output_min, output_max]。"""
    pid = PIDController(_default_params(ki=0.0, kd=0.0, output_max=0.5, output_min=-0.5))
    # error = 100, kp=0.08 → raw = 8.0, 应钳位到 0.5
    out = pid.compute(setpoint=100.0, pv=0.0, dt=0.1)
    assert out == 0.5


# ── 积分项 ─────────────────────────────────────────────────────────

def test_integral_accumulates():
    """积分项随时间累积。"""
    pid = PIDController(_default_params(kp=0.0, kd=0.0, ki=0.1, integral_max=10.0))
    # error 恒为 10，两步 0.1s → integral = 2*0.1*10 = 2.0，i_term = 0.2
    pid.compute(setpoint=20.0, pv=10.0, dt=0.1)
    out2 = pid.compute(setpoint=20.0, pv=10.0, dt=0.1)
    assert pid.integral == pytest.approx(2.0)
    assert out2 == pytest.approx(0.1 * 2.0)


def test_integral_clamped():
    """积分受 integral_max 钳位（条件积分法：输出饱和时积分不累积）。"""
    pid = PIDController(_default_params(kp=0.0, kd=0.0, ki=1.0, integral_max=0.5))
    # error=100, dt=0.1 → 输出饱和 → 条件积分跳过累积 → integral=0
    pid.compute(setpoint=100.0, pv=0.0, dt=0.1)
    assert pid.integral == pytest.approx(0.0, abs=1e-9)


def test_integral_reset_on_reset():
    """reset() 清空积分和上一步误差。"""
    pid = PIDController(_default_params())
    pid.compute(setpoint=60.0, pv=40.0, dt=0.1)
    pid.compute(setpoint=60.0, pv=40.0, dt=0.1)
    assert pid.integral != 0.0
    pid.reset()
    assert pid.integral == 0.0
    assert pid.prev_error == 0.0


# ── 微分项 ─────────────────────────────────────────────────────────

def test_derivative_dampens():
    """误差缩小时微分项为负（与 P 项抵消，抑制过冲）。"""
    # 先产生正误差，下一步误差缩小 → de/dt < 0
    pid = PIDController(_default_params(ki=0.0, kd=0.5, output_min=-100.0, output_max=100.0))
    pid.compute(setpoint=60.0, pv=20.0, dt=0.1)  # error=40
    # error 从 40 → 20, de/dt = (20-40)/0.1 = -200, d_term = 0.5*(-200) = -100
    out = pid.compute(setpoint=60.0, pv=40.0, dt=0.1)
    p_term = 0.08 * 20.0  # 1.6
    d_term = 0.5 * (20.0 - 40.0) / 0.1  # -100.0
    expected = p_term + d_term
    assert out == pytest.approx(expected)


def test_derivative_in_deadband():
    """误差在死区范围内时微分项为 0。"""
    pid = PIDController(_default_params(ki=0.0, kd=0.5, deadband_v=1.0))
    pid.compute(setpoint=60.0, pv=59.0, dt=0.1)  # error=1.0
    # error=0.5 < deadband_v=1.0 → d_term = 0
    out = pid.compute(setpoint=60.0, pv=59.5, dt=0.1)
    # 只有 P 项
    assert out == pytest.approx(0.08 * 0.5)


# ── Anti-windup ────────────────────────────────────────────────────

def test_anti_windup_back_calculation():
    """输出饱和时积分不累积（条件积分法防止 windup）。"""
    pid = PIDController(_default_params(kp=0.08, ki=0.1, kd=0.0, output_max=0.5, output_min=-0.5))
    # error=60, kp*error=4.8 → 输出钳位到 0.5, integral 应保持 0（条件积分法跳过累积）
    pid.compute(setpoint=60.0, pv=0.0, dt=1.0)
    assert pid.integral == pytest.approx(0.0, abs=1e-9)


# ── 制动曲线 ───────────────────────────────────────────────────────

def test_braking_curve_speed_zero_remaining():
    """剩余距离 ≤ 0 → 目标速度 0。"""
    assert PIDController.braking_curve_speed(0.0, 0.8) == 0.0
    assert PIDController.braking_curve_speed(-5.0, 0.8) == 0.0


def test_braking_curve_speed_formula():
    """v_target = sqrt(2*a*d) × 3.6 km/h。"""
    # a=0.8, d=100 → v_ms = sqrt(160) ≈ 12.649, v_kmh ≈ 45.54
    v = PIDController.braking_curve_speed(100.0, 0.8)
    expected = math.sqrt(2 * 0.8 * 100.0) * 3.6
    assert v == pytest.approx(expected)


def test_braking_curve_speed_decreases_with_distance():
    """剩余距离越小，目标速度越低。"""
    v1 = PIDController.braking_curve_speed(200.0, 0.8)
    v2 = PIDController.braking_curve_speed(100.0, 0.8)
    v3 = PIDController.braking_curve_speed(10.0, 0.8)
    assert v1 > v2 > v3 > 0.0


# ── dt=0 边界 ──────────────────────────────────────────────────────

def test_zero_dt_no_crash():
    """dt=0 时不崩溃，微分项 = 0。"""
    pid = PIDController(_default_params())
    out = pid.compute(setpoint=60.0, pv=40.0, dt=0.0)
    # P 项应正常输出
    assert out == pytest.approx(0.08 * 20.0)


# ── reset 后首次调用 ───────────────────────────────────────────────

def test_first_call_after_reset():
    """reset 后首次调用：积分和微分从零开始。integral_max=0.3 钳位积分。"""
    pid = PIDController(_default_params(ki=0.1, kd=0.0))
    pid.reset()
    out = pid.compute(setpoint=50.0, pv=30.0, dt=0.1)
    # error=20, p_term=1.6; integral=2.0→clamped to 0.3→i_term=0.03
    expected = 1.6 + 0.03
    assert out == pytest.approx(expected)


# ── 牵引 PID 输出范围 ──────────────────────────────────────────────

def test_traction_pid_only_positive():
    """traffic PID 的输出限制在 [0, 1]。"""
    pid = PIDController(_default_params(output_min=0.0, output_max=1.0))
    # 实际速度大于目标（下坡加速超了）→ error 负 → 输出应钳位到 0
    out = pid.compute(setpoint=50.0, pv=60.0, dt=0.1)
    assert out == 0.0


# ── PidParams 默认值 ───────────────────────────────────────────────

def test_pid_params_defaults():
    """验证 PidParams 默认值可用。"""
    p = PidParams()
    assert p.kp == 0.08
    assert p.ki == 0.002
    assert p.kd == 0.01
    assert p.integral_max == 0.3
    assert p.comfort_decel == 0.8
    assert p.deadband_v == 0.3
    assert p.deadband_d == 1.0
    assert p.creep_gain == 0.25
