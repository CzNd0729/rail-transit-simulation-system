"""信号系统单元测试（SIG-01 ~ SIG-03 三段式运行模式）。"""

from __future__ import annotations

import math

import pytest

from sim_engine.core.config import SimulationParams
from sim_engine.signaling.three_stage import (
    Phase,
    ThreeStageController,
    TrainSignalState,
)
from sim_engine.track.models import Station
from sim_engine.track.path_service import TrackPathService
from sim_engine.track.models import Track, Segment
from sim_engine.vehicle.models import (
    ControlCommands,
    TrainState,
    VehicleParams,
    TractionCurvePoint,
)


# ── helpers ────────────────────────────────────────────────────────

def _make_vehicle_params() -> VehicleParams:
    return VehicleParams(
        empty_mass=200000.0,
        passenger_capacity=1500,
        max_speed=100.0,
        max_traction_force=400000.0,
        max_brake_force=350000.0,
        davis_a=0.01,
        davis_b=0.0001,
        davis_c_front_area=10.0,
        davis_c_drag_coeff=0.5,
        traction_curve=[
            TractionCurvePoint(0, 1.0),
            TractionCurvePoint(40, 1.0),
            TractionCurvePoint(80, 0.5),
        ],
    )


def _make_track() -> TrackPathService:
    stations = [
        Station(id="ST01", name="A站", chainage=0.0, dwell_time=30.0),
        Station(id="ST02", name="B站", chainage=1000.0, dwell_time=30.0),
    ]
    segments = [
        Segment(
            id="SEC01",
            start_chainage=0.0,
            end_chainage=1000.0,
            gradient=0.0,
            curvature=0.0,
            speed_limit=80.0,
            is_tunnel=False,
        ),
    ]
    return TrackPathService(Track(name="test-line", stations=stations, segments=segments))


def _make_track_uphill() -> TrackPathService:
    """上坡 20‰ 的测试线路。"""
    stations = [
        Station(id="ST01", name="A站", chainage=0.0, dwell_time=30.0),
        Station(id="ST02", name="B站", chainage=1000.0, dwell_time=30.0),
    ]
    segments = [
        Segment(
            id="SEC01",
            start_chainage=0.0,
            end_chainage=1000.0,
            gradient=20.0,
            curvature=0.0,
            speed_limit=80.0,
            is_tunnel=False,
        ),
    ]
    return TrackPathService(Track(name="test-uphill", stations=stations, segments=segments))


def _make_track_downhill() -> TrackPathService:
    """下坡 -20‰ 的测试线路。"""
    stations = [
        Station(id="ST01", name="A站", chainage=0.0, dwell_time=30.0),
        Station(id="ST02", name="B站", chainage=1000.0, dwell_time=30.0),
    ]
    segments = [
        Segment(
            id="SEC01",
            start_chainage=0.0,
            end_chainage=1000.0,
            gradient=-20.0,
            curvature=0.0,
            speed_limit=80.0,
            is_tunnel=False,
        ),
    ]
    return TrackPathService(Track(name="test-downhill", stations=stations, segments=segments))


def _make_sim_params(**overrides) -> SimulationParams:
    d = dict(
        time_step=0.1,
        total_time=600.0,
        speed_multiplier=1.0,
        target_speed_ratio=0.8,
        station_stop_tolerance=1.0,
    )
    d.update(overrides)
    return SimulationParams(**d)


def _make_train(position: float = 0.0, speed: float = 0.0, mass: float = 260000.0) -> TrainState:
    return TrainState(
        position=position,
        speed=speed,
        acceleration=0.0,
        mode="coasting",
        mass=mass,
        passenger_load=0.6,
    )


# ── TrainSignalState ────────────────────────────────────────────────

def test_initial_phase_is_traction():
    state = TrainSignalState()
    assert state.phase == Phase.TRACTION
    assert state.dwell_remaining == 0.0


# ── ThreeStageController 初始化与重置 ────────────────────────────────

def test_controller_initial_state():
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    assert ctrl.signal_state.phase == Phase.TRACTION


def test_controller_reset():
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state = TrainSignalState(phase=Phase.DWELL, dwell_remaining=10.0)
    ctrl.reset()
    assert ctrl.signal_state.phase == Phase.TRACTION
    assert ctrl.signal_state.dwell_remaining == 0.0


# ── SIG-01: 牵引阶段 ────────────────────────────────────────────────

def test_traction_when_below_target_speed():
    """速度低于 target_speed (0.8 × 80 = 64 km/h) 时应输出牵引指令。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(position=10.0, speed=30.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.traction_level == 1.0
    assert cmd.brake_level == 0.0
    assert ctrl.signal_state.phase == Phase.TRACTION


def test_traction_transition_to_coasting():
    """速度达到 target_speed 时切换到惰行。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(position=10.0, speed=64.0)  # = target
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.traction_level == 0.0
    assert cmd.brake_level == 0.0
    assert ctrl.signal_state.phase == Phase.COASTING


# ── SIG-01: 惰行阶段 ────────────────────────────────────────────────

def test_coasting_outputs_neutral():
    """惰行阶段输出补偿牵引力 + phase="coasting" 用于前端工况显示。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(coasting_min_speed=0.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=500.0, speed=60.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    # 制动始终为 0
    assert cmd.brake_level == 0.0
    # 应有少量补偿牵引力，抵消滚动摩擦
    assert cmd.traction_level > 0.0
    assert cmd.traction_level < 0.3
    # phase 应为 "coasting"，确保前端显示惰行而非牵引
    assert cmd.phase == "coasting"


def test_coasting_compensation_uphill_higher():
    """上坡路段惰行补偿应大于平坡。"""
    track = _make_track_uphill()
    ctrl = ThreeStageController(track, _make_vehicle_params(), _make_sim_params(coasting_min_speed=0.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=200.0, speed=50.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.traction_level > 0.05  # 上坡应有可观补偿


def test_coasting_compensation_formula_match():
    """验证惰行补偿数值：级位 ≈ (A+B·v)·mg / (F_max × 曲线比)。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(coasting_min_speed=0.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=300.0, speed=60.0)
    cmd = ctrl.compute_commands(train, dt=0.1)

    # 手动计算预期值
    v_ms = 60.0 / 3.6
    mass = 260000.0
    rolling = (0.01 + 0.0001 * v_ms) * mass * 9.81
    percent = 1.0 + (60 - 40) / (80 - 40) * (0.5 - 1.0)  # = 0.75
    expected = rolling / (400000.0 * percent)
    assert cmd.traction_level == pytest.approx(expected, rel=1e-6)


def test_coasting_compensation_downhill_lower():
    """下坡路段惰行补偿应小于平坡（下坡助力自动减少所需牵引力）。"""
    track = _make_track_downhill()
    ctrl = ThreeStageController(track, _make_vehicle_params(), _make_sim_params(coasting_min_speed=0.0))
    ctrl._state.phase = Phase.COASTING
    # 下坡 -20‰，滚动摩擦 ≈ 30.3kN, 坡度力 ≈ -51.0kN → f_target 接近 0
    train = _make_train(position=200.0, speed=60.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    # 坡度助力足以抵消滚动摩擦，补偿应接近 0
    assert cmd.traction_level == pytest.approx(0.0, abs=0.01)


def test_coasting_compensation_downhill_formula():
    """验证下坡补偿公式：f_target = rolling + gradient_force（gradent 为负）。"""
    ctrl = ThreeStageController(_make_track_downhill(), _make_vehicle_params(), _make_sim_params(coasting_min_speed=0.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=200.0, speed=50.0)
    cmd = ctrl.compute_commands(train, dt=0.1)

    v_ms = 50.0 / 3.6
    mass = 260000.0
    rolling = (0.01 + 0.0001 * v_ms) * mass * 9.81
    gradient_force = mass * 9.81 * (-20.0 / 1000.0)  # 下坡为负
    f_target = rolling + gradient_force

    if f_target <= 0:
        assert cmd.traction_level == 0.0
    else:
        percent = 1.0 + (50 - 40) / (80 - 40) * (0.5 - 1.0)  # = 0.875
        expected = f_target / (400000.0 * percent)
        assert cmd.traction_level == pytest.approx(expected, rel=1e-6)


def test_coasting_min_speed_triggers_traction():
    """惰行速度低于 coasting_min_speed 时应切回牵引。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(coasting_min_speed=30.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=500.0, speed=25.0)  # < 30 km/h
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.phase == Phase.TRACTION
    assert cmd.traction_level == 1.0
    assert cmd.brake_level == 0.0


def test_coasting_min_speed_stays_coasting():
    """惰行速度高于 coasting_min_speed 时继续惰行。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(coasting_min_speed=30.0))
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=500.0, speed=45.0)  # > 30 km/h
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.phase == Phase.COASTING


# ── SIG-02~03: 制动触发与站停 ───────────────────────────────────────

def test_coasting_to_braking_when_near_station():
    """当位置 + 制动距离 ≥ 站台中心时进入制动。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.COASTING
    # 列车高速接近 ST02 (1000m)，制动距离应足够触发
    train = _make_train(position=900.0, speed=60.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    # 计算制动距离：v_ms = 60/3.6 ≈ 16.67, max_decel = 350000/260000 ≈ 1.346
    # brake_dist = (16.67^2)/(2*1.346)*1.1 ≈ 113.6m
    # position + brake_dist = 900 + 113.6 = 1013.6 > 1000 → 应触发制动
    assert cmd.brake_level == 1.0
    assert ctrl.signal_state.phase == Phase.BRAKING


def test_braking_command():
    """制动阶段输出满制动。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.BRAKING
    train = _make_train(position=990.0, speed=10.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.brake_level == 1.0


# ── SIG-02: 站停时间 ────────────────────────────────────────────────

def test_arrival_triggers_dwell():
    """在站台容差内停稳后进入 dwell 阶段。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # next_station_ahead 使用 chainage > position + 0.01，
    # 所以位置需要略小于 1000.0 才能命中 ST02，同时容差 1.0m 仍然满足
    train = _make_train(position=999.5, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.phase == Phase.DWELL
    assert ctrl.signal_state.dwell_remaining == 30.0  # ST02 dwell_time
    assert cmd.traction_level == 0.0


def test_dwell_countdown():
    """dwell 倒计时递减。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state = TrainSignalState(phase=Phase.DWELL, dwell_remaining=5.0)
    train = _make_train(position=1000.0)
    cmd = ctrl.compute_commands(train, dt=0.5)
    assert ctrl.signal_state.dwell_remaining == pytest.approx(4.5)
    assert cmd.traction_level == 0.0


def test_dwell_transition_to_traction_after_expiry():
    """dwell 倒计时结束后切回牵引。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state = TrainSignalState(phase=Phase.DWELL, dwell_remaining=0.1)
    train = _make_train(position=1000.0)
    cmd = ctrl.compute_commands(train, dt=0.2)
    assert ctrl.signal_state.phase == Phase.TRACTION
    assert ctrl.signal_state.dwell_remaining == 0.0


# ── 无下一站时制动停车 ──────────────────────────────────────────────

def test_no_next_station_brakes():
    """没有前方车站时（终点已过），若仍在运动则制动。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # 已过最后一个站
    train = _make_train(position=1100.0, speed=20.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.brake_level == 1.0


def test_no_next_station_stopped_idle():
    """没有前方车站且已停止，输出空指令。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(position=1100.0, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.traction_level == 0.0
    assert cmd.brake_level == 0.0


# ── 中途停住重新牵引 ────────────────────────────────────────────────

def test_stuck_midway_restarts_traction():
    """制动不足导致中途停住时自动切回牵引。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.BRAKING
    # 距 ST02 还有 100m 但速度为 0
    train = _make_train(position=900.0, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.phase == Phase.TRACTION


# ── SIG-03: 制动触发距离计算 ────────────────────────────────────────

def test_brake_trigger_distance_formula():
    """制动触发距离 = v²/(2a) × 1.1（10% 安全余量）。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # 速度 72 km/h = 20 m/s, mass=260000, max_brake=350000
    train = _make_train(speed=72.0, mass=260000.0)
    v_ms = 72.0 / 3.6  # 20.0 m/s
    max_decel = 350000.0 / 260000.0  # ≈ 1.346 m/s²
    expected = (v_ms * v_ms) / (2 * max_decel) * 1.1
    assert ctrl._brake_trigger_distance(train) == pytest.approx(expected)


def test_brake_trigger_distance_zero_speed():
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(speed=0.0, mass=260000.0)
    assert ctrl._brake_trigger_distance(train) == 0.0


def test_brake_trigger_distance_zero_mass():
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(speed=50.0, mass=0.0)
    # mass=0 时 fallback 到 empty_mass=200000
    v_ms = 50.0 / 3.6
    max_decel = 350000.0 / 200000.0
    expected = (v_ms * v_ms) / (2 * max_decel) * 1.1
    assert ctrl._brake_trigger_distance(train) == pytest.approx(expected)


# ── 完整运行流程: 牵引 → 惰行 → 制动 → 站停 → 牵引 ─────────────────

def test_full_cycle_to_station():
    """模拟一列火车从 A 站完整运行到 B 站的过程，至少经历牵引与惰行。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(
        target_speed_ratio=0.5,  # 降低目标速度让测试更快
    ))
    train = _make_train(position=0.0, speed=0.0, mass=260000.0)

    phases_seen: set[str] = set()

    for _ in range(2000):
        cmd = ctrl.compute_commands(train, dt=0.1)
        phases_seen.add(ctrl.signal_state.phase.value)

        # 简单动力学模拟
        if cmd.traction_level > 0:
            accel = 400000 * cmd.traction_level / 260000
        elif cmd.brake_level > 0:
            accel = -350000 * cmd.brake_level / 260000
        else:
            accel = 0.0
        v_ms = train.speed / 3.6
        new_v_ms = max(v_ms + accel * 0.1, 0.0)
        train = _make_train(
            position=train.position + new_v_ms * 0.1,
            speed=new_v_ms * 3.6,
            mass=260000,
        )
        if train.position > 1050.0:
            break

    # 至少经历过牵引和惰行阶段
    assert "traction" in phases_seen
    assert "coasting" in phases_seen
    # 接近 B 站区域
    assert train.position > 500.0


# ── 极低目标速度 ────────────────────────────────────────────────────

def test_low_target_speed_stays_coasting():
    """target_speed_ratio=0 时，牵引后立即进入惰行。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params(
        target_speed_ratio=0.0,
    ))
    train = _make_train(position=10.0, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    # 目标速度=0，车速=0 已满足，应进入惰行
    assert ctrl.signal_state.phase == Phase.COASTING
