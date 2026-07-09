"""P-only 控制器单元测试。

覆盖：比例项、制动曲线、边界条件。
"""

from __future__ import annotations

import math

import pytest

from sim_engine.core.config import PidParams
from sim_engine.signaling.pid_controller import PIDController


# ── P-only compute ─────────────────────────────────────────────────

def test_p_only_compute():
    """error → kp × error。"""
    pid = PIDController(kp=0.02)
    assert pid.compute(0.5) == pytest.approx(0.01)
    assert pid.compute(-0.5) == pytest.approx(-0.01)


def test_p_only_zero_error():
    """误差为 0 时输出 0。"""
    pid = PIDController(kp=0.02)
    assert pid.compute(0.0) == 0.0


def test_p_only_reset_noop():
    """reset 不报错（P-only 无状态）。"""
    pid = PIDController(kp=0.02)
    pid.compute(0.5)
    pid.reset()  # 不应报错
    assert pid.compute(0.3) == pytest.approx(0.006)


# ── 制动曲线 ───────────────────────────────────────────────────────

def test_braking_curve_speed_zero_remaining():
    assert PIDController.braking_curve_speed(0.0, 0.8) == 0.0
    assert PIDController.braking_curve_speed(-5.0, 0.8) == 0.0


def test_braking_curve_speed_formula():
    v = PIDController.braking_curve_speed(100.0, 0.8)
    expected = math.sqrt(2 * 0.8 * 100.0) * 3.6
    assert v == pytest.approx(expected)


def test_braking_curve_speed_decreases_with_distance():
    v1 = PIDController.braking_curve_speed(200.0, 0.8)
    v2 = PIDController.braking_curve_speed(100.0, 0.8)
    v3 = PIDController.braking_curve_speed(10.0, 0.8)
    assert v1 > v2 > v3 > 0.0


# ── PidParams 默认值 ───────────────────────────────────────────────

def test_pid_params_defaults():
    p = PidParams()
    assert p.comfort_decel == 0.8
    assert p.kp_brake == 0.02
    assert p.creep_gain == 0.25
    assert p.deadband_d == 1.0
    assert p.brake_safety_factor == 1.02