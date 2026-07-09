"""车辆系统单元测试（覆盖 VHC-01 ~ VHC-08、配置加载）。"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from sim_engine.vehicle import (
    ControlCommands,
    TrackPointParams,
    VehicleSystem,
    load_vehicle_params,
)
from sim_engine.vehicle.config import params_from_dict
from sim_engine.vehicle.models import (
    GRAVITY,
    PERSON_MASS,
    TractionCurvePoint,
    VehicleParams,
)
from sim_engine.vehicle import resistance as R
from sim_engine.vehicle.traction import interpolate_force_percent, traction_force

CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "sim_engine" / "config" / "vehicle.yaml"
)


def make_params(**overrides) -> VehicleParams:
    base = dict(
        empty_mass=200000.0,
        passenger_capacity=1500,
        max_speed=100.0,
        max_traction_force=400000.0,
        max_brake_force=350000.0,
        davis_a=0.01,
        davis_b=0.0001,
        davis_c_front_area=10.0,
        davis_c_drag_coeff=0.5,
        curve_resist_coeff=600.0,
        tunnel_resist_factor=1.2,
        traction_curve=[
            TractionCurvePoint(0, 1.0),
            TractionCurvePoint(40, 1.0),
            TractionCurvePoint(80, 0.5),
            TractionCurvePoint(100, 0.5),
        ],
    )
    base.update(overrides)
    return VehicleParams(**base)


def flat_track(**overrides) -> TrackPointParams:
    data = dict(gradient=0.0, curvature=0.0, speed_limit=80.0, is_tunnel=False)
    data.update(overrides)
    return TrackPointParams(**data)


# --- 质量折算 ---

def test_mass_at_load():
    p = make_params()
    assert p.mass_at_load(0.0) == 200000.0
    assert p.mass_at_load(1.0) == 200000.0 + 1500 * PERSON_MASS
    # 越界钳位
    assert p.mass_at_load(2.0) == p.mass_at_load(1.0)
    assert p.mass_at_load(-1.0) == p.mass_at_load(0.0)


# --- VHC-02 牵引特性曲线 ---

def test_interpolate_force_percent_endpoints_and_middle():
    curve = [TractionCurvePoint(0, 1.0), TractionCurvePoint(40, 1.0), TractionCurvePoint(80, 0.5)]
    assert interpolate_force_percent(curve, 0) == 1.0
    assert interpolate_force_percent(curve, 40) == 1.0
    assert interpolate_force_percent(curve, 80) == 0.5
    # 40~80 之间线性递减，60km/h → 0.75
    assert interpolate_force_percent(curve, 60) == pytest.approx(0.75)
    # 超出范围取端点
    assert interpolate_force_percent(curve, 200) == 0.5
    assert interpolate_force_percent(curve, -10) == 1.0


def test_interpolate_empty_curve_defaults_full():
    assert interpolate_force_percent([], 50) == 1.0


def test_traction_force_scales_with_level():
    curve = [TractionCurvePoint(0, 1.0), TractionCurvePoint(100, 1.0)]
    assert traction_force(curve, 400000, 10, 1.0) == 400000
    assert traction_force(curve, 400000, 10, 0.5) == 200000
    # 级位越界钳位
    assert traction_force(curve, 400000, 10, 2.0) == 400000
    assert traction_force(curve, 400000, 10, -1.0) == 0.0


# --- VHC-03 Davis 阻力 ---

def test_davis_resistance_at_zero_speed():
    p = make_params()
    mass = 260000.0
    expected = p.davis_a * mass * GRAVITY  # v=0，仅滚动阻力常数项
    assert R.davis_resistance(p, mass, 0.0) == pytest.approx(expected)


def test_davis_resistance_increases_with_speed():
    p = make_params()
    mass = 260000.0
    assert R.davis_resistance(p, mass, 80) > R.davis_resistance(p, mass, 20)


# --- VHC-04 坡度阻力 ---

def test_gradient_resistance_sign():
    mass = 260000.0
    up = R.gradient_resistance(mass, 30)
    down = R.gradient_resistance(mass, -30)
    assert up > 0 and down < 0
    assert up == pytest.approx(-down)
    assert up == pytest.approx(mass * GRAVITY * 30 / 1000.0)


# --- VHC-05 弯道阻力 ---

def test_curve_resistance_straight_is_zero():
    assert R.curve_resistance(260000, 0) == 0.0
    assert R.curve_resistance(260000, -5) == 0.0
    assert R.curve_resistance(260000, math.inf) == 0.0


def test_curve_resistance_value():
    mass = 260000.0
    val = R.curve_resistance(mass, 800, 600)
    assert val == pytest.approx(mass * GRAVITY * (600 / 800) / 1000.0)


# --- VHC-06 隧道阻力 ---

def test_tunnel_resistance():
    assert R.tunnel_resistance(1000, False, 1.2) == 0.0
    assert R.tunnel_resistance(1000, True, 1.2) == pytest.approx(200.0)


# --- VHC-01 动力学解算 ---

def test_step_traction_accelerates():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(passenger_load=0.6)
    cmd = ControlCommands(traction_level=1.0)
    result = veh.step(state, cmd, flat_track(), dt=0.1)
    assert result.state.speed > 0
    assert result.state.acceleration > 0
    assert result.state.mode == "traction"
    # 位置随新速度前进
    assert result.state.position > 0


def test_step_newton_second_law_consistency():
    """合力 / 质量 应等于报告的加速度（未触发限速/停车钳位时）。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(passenger_load=0.0)
    cmd = ControlCommands(traction_level=1.0)
    result = veh.step(state, cmd, flat_track(speed_limit=200), dt=0.1)
    assert result.state.acceleration == pytest.approx(
        result.forces.net / state.mass, rel=1e-6
    )


def test_heavier_train_accelerates_slower():
    veh_light = VehicleSystem(make_params())
    light = veh_light.step(
        veh_light.create_initial_state(0.0),
        ControlCommands(traction_level=1.0),
        flat_track(speed_limit=200),
        dt=0.1,
    )
    veh_heavy = VehicleSystem(make_params(empty_mass=300000.0))
    heavy = veh_heavy.step(
        veh_heavy.create_initial_state(0.0),
        ControlCommands(traction_level=1.0),
        flat_track(speed_limit=200),
        dt=0.1,
    )
    assert light.state.acceleration > heavy.state.acceleration


def test_uphill_slower_than_flat():
    veh = VehicleSystem(make_params())
    flat = veh.step(
        veh.create_initial_state(0.0),
        ControlCommands(traction_level=1.0),
        flat_track(gradient=0, speed_limit=200),
        dt=0.1,
    )
    uphill = veh.step(
        veh.create_initial_state(0.0),
        ControlCommands(traction_level=1.0),
        flat_track(gradient=30, speed_limit=200),
        dt=0.1,
    )
    assert uphill.state.acceleration < flat.state.acceleration


# --- VHC-07 限速约束 ---

def test_speed_limit_clamp():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 79.0
    cmd = ControlCommands(traction_level=1.0)
    result = veh.step(state, cmd, flat_track(speed_limit=80), dt=1.0)
    assert result.state.speed <= 80.0 + 1e-9


def test_max_speed_clamp_lower_than_track():
    """车辆 max_speed 低于区段限速时，应以 max_speed 为上限。"""
    veh = VehicleSystem(make_params(max_speed=50.0))
    state = veh.create_initial_state(0.0)
    state.speed = 49.0
    cmd = ControlCommands(traction_level=1.0)
    result = veh.step(state, cmd, flat_track(speed_limit=80), dt=1.0)
    assert result.state.speed <= 50.0 + 1e-9


def test_effective_speed_limit_helper():
    from sim_engine.vehicle.dynamics import effective_speed_limit_kmh

    track = flat_track(speed_limit=80)
    params = make_params(max_speed=100.0)
    assert effective_speed_limit_kmh(track, params) == 80.0

    params_low = make_params(max_speed=50.0)
    assert effective_speed_limit_kmh(track, params_low) == 50.0


# --- VHC-08 停车钳位 ---

def test_braking_does_not_reverse():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 5.0
    cmd = ControlCommands(brake_level=1.0)
    result = veh.step(state, cmd, flat_track(), dt=10.0)
    assert result.state.speed == 0.0
    assert result.state.mode == "braking"


def test_emergency_brake_uses_max_force():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 50.0
    result = veh.step(state, ControlCommands(emergency_brake=True), flat_track(), dt=0.1)
    assert result.forces.brake == veh.params.max_brake_force
    assert result.state.mode == "braking"


def test_coasting_mode():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 50.0
    result = veh.step(state, ControlCommands(), flat_track(), dt=0.1)
    assert result.state.mode == "coasting"
    # 惰行时阻力使列车减速
    assert result.state.speed < 50.0


# --- 配置加载 ---

def test_load_vehicle_params_from_yaml():
    params = load_vehicle_params(CONFIG_PATH)
    assert params.empty_mass == 200000.0
    assert params.passenger_capacity == 1500
    assert len(params.traction_curve) == 4
    assert params.traction_curve[0].force_percent == 1.0


def test_from_config_builds_system():
    veh = VehicleSystem.from_config(str(CONFIG_PATH))
    assert isinstance(veh, VehicleSystem)
    assert veh.params.max_traction_force == 400000.0


def test_params_from_dict_missing_key_raises():
    with pytest.raises(ValueError, match="缺少必填字段"):
        params_from_dict({"empty_mass": 1.0})


def test_params_from_dict_flat_layout():
    data = dict(
        empty_mass=100.0,
        passenger_capacity=10,
        max_speed=80,
        max_traction_force=1000,
        max_brake_force=800,
        davis_a=0.01,
        davis_b=0.0001,
        davis_c_front_area=10,
        davis_c_drag_coeff=0.5,
    )
    p = params_from_dict(data)
    assert p.empty_mass == 100.0
    assert p.traction_curve == []


# ── VHC-09: 能耗预留字段 ────────────────────────────────────────────

def test_energy_fields_reserved():
    """VHC-09：牵引能耗和再生制动电量为预留字段，迭代一中恒为 0。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(passenger_load=0.5)
    assert state.traction_energy == 0.0
    assert state.regen_energy == 0.0
    # 跑几步后仍为 0
    cmd = ControlCommands(traction_level=1.0)
    result = veh.step(state, cmd, flat_track(speed_limit=200), dt=0.1)
    assert result.state.traction_energy == 0.0
    assert result.state.regen_energy == 0.0


# ── VHC-10: 受力分解字段检查 ────────────────────────────────────────

def test_force_breakdown_all_fields():
    """VHC-10：每步输出必须含全部受力分量。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.6)
    result = veh.step(state, ControlCommands(traction_level=1.0), flat_track(), dt=0.1)
    f = result.forces
    for attr in ("traction", "brake", "davis", "gradient", "curve",
                 "tunnel", "resistance_total", "net"):
        assert hasattr(f, attr)
        assert isinstance(getattr(f, attr), float)


def test_force_breakdown_net_consistency():
    """合力 = 牵引力 - 制动力 - 总阻力。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.6)
    result = veh.step(state, ControlCommands(traction_level=0.5, brake_level=0.3),
                      flat_track(gradient=10, is_tunnel=True), dt=0.1)
    f = result.forces
    expected_net = f.traction - f.brake - f.resistance_total
    assert f.net == pytest.approx(expected_net)


def test_force_breakdown_total_consistency():
    """总阻力 = davis + gradient + curve + tunnel。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.6)
    state.speed = 50.0
    result = veh.step(state, ControlCommands(), flat_track(gradient=5, is_tunnel=True, curvature=500), dt=0.1)
    f = result.forces
    expected_total = f.davis + f.gradient + f.curve + f.tunnel
    assert f.resistance_total == pytest.approx(expected_total)


# ── 弯道阻力边界 ────────────────────────────────────────────────────

def test_curve_resistance_none_curvature():
    """curvature=None 时弯道阻力为 0。"""
    mass = 260000.0
    assert R.curve_resistance(mass, None) == 0.0


# ── 零牵引力控车 ────────────────────────────────────────────────────

def test_zero_traction_no_forward_force():
    """traction_level=0 时牵引力为 0。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 10.0
    result = veh.step(state, ControlCommands(traction_level=0.0), flat_track(), dt=0.1)
    assert result.forces.traction == 0.0


# ── 模式判断覆盖 ────────────────────────────────────────────────────

def test_mode_braking_with_nonzero_brake_level():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 30.0
    result = veh.step(state, ControlCommands(brake_level=0.5), flat_track(), dt=0.1)
    assert result.state.mode == "braking"


def test_mode_traction_with_nonzero_traction():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    result = veh.step(state, ControlCommands(traction_level=0.3), flat_track(speed_limit=200), dt=0.1)
    assert result.state.mode == "traction"


def test_mode_coasting_with_zero_commands():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 40.0
    result = veh.step(state, ControlCommands(), flat_track(), dt=0.1)
    assert result.state.mode == "coasting"


# ── 多重钳位顺序 ────────────────────────────────────────────────────

def test_speed_clamp_does_not_produce_negative():
    """限速和停车钳位不应产生负速度。"""
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    state.speed = 5.0  # 初始正向速度
    # 纯制动 + 下坡（负梯度 → 负坡度阻力 = 助力，但 net 仍可能为负）
    cmd = ControlCommands(brake_level=1.0)
    track = flat_track(gradient=-50, speed_limit=80)  # 大下坡
    result = veh.step(state, cmd, track, dt=0.1)
    assert result.state.speed >= 0.0
    assert result.state.position >= state.position  # 不倒退


# ── 极小步长 ────────────────────────────────────────────────────────

def test_tiny_dt_still_valid():
    veh = VehicleSystem(make_params())
    state = veh.create_initial_state(0.0)
    result = veh.step(state, ControlCommands(traction_level=1.0), flat_track(speed_limit=200), dt=0.001)
    assert result.state.position >= 0.0
    assert result.state.speed >= 0.0


# ── 无牵引曲线时默认满载 ─────────────────────────────────────────────

def test_traction_without_curve_uses_full():
    p = make_params()
    p.traction_curve = []
    veh = VehicleSystem(p)
    state = veh.create_initial_state(0.0)
    result = veh.step(state, ControlCommands(traction_level=1.0), flat_track(speed_limit=200), dt=0.1)
    assert result.forces.traction == p.max_traction_force

