"""供电系统单元测试（PWR-01~PWR-04）。"""

from __future__ import annotations

import math

import pytest

from sim_engine.power.load_flow import (
    MIN_PANTOGRAPH_VOLTAGE,
    PowerFlowResult,
    PowerNetwork,
    calculate,
)
from sim_engine.power.regeneration import (
    calculate_regen_power,
    calculate_traction_power,
)
from sim_engine.power.static_power import PANTOGRAPH_VOLTAGE, get_pantograph_voltage
from sim_engine.power.substation import Substation


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


# ── PWR-03: 变电所数据模型 ─────────────────────────────────────────

def test_substation_defaults():
    s = Substation(id="S1", name="测试变电所", chainage=500.0)
    assert s.id == "S1"
    assert s.name == "测试变电所"
    assert s.chainage == 500.0
    assert s.rated_voltage == 1500.0
    assert s.rated_power == 5000.0
    assert s.output_current == 0.0
    assert s.output_power == 0.0


def test_substation_custom_ratings():
    s = Substation(id="S2", name="高容量站", chainage=1000.0, rated_voltage=750.0, rated_power=10000.0)
    assert s.rated_voltage == 750.0
    assert s.rated_power == 10000.0


# ── PWR-02: 欧姆压降计算 ───────────────────────────────────────────

def _make_network(chainages: list[float]):
    """快速构建测试用供电网络。"""
    subs = [Substation(id=f"S{i}", name=f"站{i}", chainage=c) for i, c in enumerate(chainages)]
    return PowerNetwork(substations=subs, contact_line_resistance=0.02, rail_resistance=0.01)


def test_calculate_no_substations_returns_nominal():
    """无变电所时返回额定网压，电流为 0（无供电来源）。"""
    network = PowerNetwork(substations=[])
    result = calculate(network, train_position=500.0, power_demand=100000.0)
    assert result.pantograph_voltage == 1500.0
    assert result.current == 0.0  # 无变电所不计算取流
    assert result.voltage_drop == 0.0


def test_calculate_at_substation_zero_drop():
    """列车正好在变电所处，距离为 0，无压降。"""
    network = _make_network([0.0, 3200.0])
    result = calculate(network, train_position=0.0, power_demand=150000.0)
    assert result.pantograph_voltage == 1500.0
    assert result.voltage_drop == pytest.approx(0.0)
    assert result.supplying_substation_id == "S0"


def test_calculate_midpoint_voltage_drop():
    """列车在两变电所中间位置，验证欧姆压降公式。"""
    network = _make_network([0.0, 3200.0])
    # 列车在 1600m，离最近变电所 1600m = 1.6km
    # R_total = (0.02 + 0.01) × 1.6 = 0.048 Ω
    # P = 300000W, I = 300000 / 1500 = 200A
    # ΔV = 200 × 0.048 = 9.6V
    result = calculate(network, train_position=1600.0, power_demand=300000.0)
    assert result.pantograph_voltage == pytest.approx(1500.0 - 9.6)
    assert result.voltage_drop == pytest.approx(9.6)


def test_calculate_finds_nearest_substation():
    """列车离中间变电所最近时应选择该站供电。"""
    # 三座变电所：0m, 1500m, 3200m
    network = _make_network([0.0, 1500.0, 3200.0])
    # 列车在 1600m，最近变电所是 S1 (1500m)，距离 100m = 0.1km
    result = calculate(network, train_position=1600.0, power_demand=150000.0)
    assert result.supplying_substation_id == "S1"
    # R = 0.03 × 0.1 = 0.003, I = 100A, ΔV = 0.3V
    assert result.voltage_drop == pytest.approx(0.3)


def test_calculate_undervoltage_clamp():
    """网压不低于最低限值 1000V。"""
    # 使用极远的变电所距离和大功率使压降极大
    subs = [Substation(id="S0", name="远站", chainage=0.0)]
    network = PowerNetwork(substations=subs, contact_line_resistance=0.5, rail_resistance=0.5)
    # 距离 10km, R = 1.0 × 10 = 10Ω, I 很大时压降极大
    result = calculate(network, train_position=10000.0, power_demand=100000.0)
    # I = 100000 / 1500 ≈ 66.67, ΔV = 66.67 × 10 = 666.7
    # V_panto = 1500 - 666.7 = 833.3, 应钳位到 1000
    assert result.pantograph_voltage == MIN_PANTOGRAPH_VOLTAGE
    assert result.undervoltage_warning is True


def test_calculate_no_undervoltage_for_normal_case():
    """正常工况不应触发欠压告警。"""
    network = _make_network([0.0, 3200.0])
    result = calculate(network, train_position=500.0, power_demand=50000.0)
    assert result.undervoltage_warning is False
    assert result.pantograph_voltage > MIN_PANTOGRAPH_VOLTAGE


def test_calculate_zero_power_demand():
    """功率需求为 0 时无电流无压降。"""
    network = _make_network([0.0, 3200.0])
    result = calculate(network, train_position=800.0, power_demand=0.0)
    assert result.current == 0.0
    assert result.voltage_drop == 0.0
    assert result.pantograph_voltage == 1500.0


def test_calculate_substation_states():
    """验证变电所状态快照正确。"""
    network = _make_network([0.0, 1600.0, 3200.0])
    result = calculate(network, train_position=800.0, power_demand=150000.0)
    # 最近变电所 S0 (0m)，距离 800m = 0.8km
    # R = 0.03 × 0.8 = 0.024Ω, I = 100A, ΔV = 2.4V, V_panto = 1497.6V
    # 消耗功率 = 1497.6 × 100 / 1000 = 149.76kW
    # S0 应有输出，S1 和 S2 应为 0
    assert len(result.substation_states) == 3
    s0 = next(s for s in result.substation_states if s.id == "S0")
    assert s0.output_current > 0
    assert s0.output_power > 0

    s1 = next(s for s in result.substation_states if s.id == "S1")
    assert s1.output_current == 0.0
    assert s1.output_power == 0.0

    s2 = next(s for s in result.substation_states if s.id == "S2")
    assert s2.output_current == 0.0
    assert s2.output_power == 0.0


# ── PWR-04: 再生制动统计 ────────────────────────────────────────────

def test_regen_power_normal():
    """正常制动工况下再生功率计算。"""
    # F_brake = 50000N, v = 10 m/s, η = 0.3
    # P_regen = 50000 × 10 × 0.3 = 150000W
    assert calculate_regen_power(50000.0, 10.0, 0.3) == 150000.0


def test_regen_power_zero_force():
    """制动力为 0 时再生功率为 0。"""
    assert calculate_regen_power(0.0, 10.0) == 0.0


def test_regen_power_zero_speed():
    """速度为 0 时再生功率为 0（静止列车不回收能量）。"""
    assert calculate_regen_power(50000.0, 0.0) == 0.0


def test_regen_power_negative_force():
    """负制动力（异常输入）应返回 0。"""
    assert calculate_regen_power(-1000.0, 10.0) == 0.0


def test_regen_power_custom_efficiency():
    """可自定义再生效率。"""
    assert calculate_regen_power(100000.0, 20.0, 0.5) == 1_000_000.0


def test_traction_power_normal():
    """牵引功率计算。"""
    assert calculate_traction_power(100000.0, 15.0) == 1_500_000.0


def test_traction_power_zero():
    """零牵引力/零速度返回 0。"""
    assert calculate_traction_power(0.0, 10.0) == 0.0
    assert calculate_traction_power(50000.0, 0.0) == 0.0


# ── PowerNetwork 数据类 ─────────────────────────────────────────────

def test_power_network_defaults():
    network = PowerNetwork()
    assert network.substations == []
    assert network.contact_line_resistance == 0.02
    assert network.rail_resistance == 0.01


def test_power_network_custom():
    subs = [Substation(id="S0", name="x", chainage=0.0)]
    network = PowerNetwork(substations=subs, contact_line_resistance=0.05, rail_resistance=0.02)
    assert len(network.substations) == 1
    assert network.contact_line_resistance == 0.05
    assert network.rail_resistance == 0.02
