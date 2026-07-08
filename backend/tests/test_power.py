"""供电系统单元测试（PWR-01 固定网压）。"""

from __future__ import annotations

from sim_engine.power.static_power import get_pantograph_voltage, PANTOGRAPH_VOLTAGE


# ── PWR-01: 固定网压 DC 1500V ──────────────────────────────────────

def test_pantograph_voltage_is_1500v():
    assert get_pantograph_voltage() == 1500.0


def test_pantograph_voltage_constant():
    """多次调用始终返回相同值。"""
    for _ in range(10):
        assert get_pantograph_voltage() == 1500.0


def test_pantograph_voltage_matches_constant():
    """返回值与模块常量一致。"""
    assert get_pantograph_voltage() == PANTOGRAPH_VOLTAGE


def test_pantograph_voltage_is_float():
    assert isinstance(get_pantograph_voltage(), float)


def test_pantograph_voltage_positive():
    assert get_pantograph_voltage() > 0
