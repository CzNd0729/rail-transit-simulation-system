"""核心模块单元测试（SimulationClock / SimulationParams / RunState）。"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sim_engine.core.clock import RunState, SimulationClock
from sim_engine.core.config import SimulationParams, load_simulation_params


# ── RunState ─────────────────────────────────────────────────────────

def test_run_state_values():
    assert RunState.IDLE == "idle"
    assert RunState.RUNNING == "running"
    assert RunState.PAUSED == "paused"
    assert RunState.STOPPED == "stopped"


def test_run_state_is_str_enum():
    assert isinstance(RunState.IDLE, str)


def test_run_state_from_string():
    assert RunState("running") == RunState.RUNNING
    assert RunState("idle") == RunState.IDLE


# ── SimulationClock ─────────────────────────────────────────────────

def test_clock_defaults():
    clock = SimulationClock()
    assert clock.time_step == 0.1
    assert clock.elapsed == 0.0
    assert clock.speed_multiplier == 1.0


def test_clock_custom_params():
    clock = SimulationClock(time_step=0.05, speed_multiplier=5.0)
    assert clock.time_step == 0.05
    assert clock.speed_multiplier == 5.0


def test_tick_advances_elapsed():
    clock = SimulationClock(time_step=0.1)
    for i in range(1, 6):
        assert clock.tick() == pytest.approx(i * 0.1)
    assert clock.elapsed == pytest.approx(0.5)


def test_tick_returns_elapsed():
    clock = SimulationClock(time_step=0.25)
    result = clock.tick()
    assert result == clock.elapsed == pytest.approx(0.25)


def test_reset_zeroes_elapsed():
    clock = SimulationClock(time_step=0.1)
    clock.tick()
    clock.tick()
    assert clock.elapsed > 0
    clock.reset()
    assert clock.elapsed == 0.0


def test_reset_preserves_time_step():
    clock = SimulationClock(time_step=0.2)
    clock.tick()
    clock.reset()
    assert clock.time_step == 0.2
    assert clock.speed_multiplier == 1.0


def test_many_ticks():
    clock = SimulationClock(time_step=0.01)
    for _ in range(1000):
        clock.tick()
    assert clock.elapsed == pytest.approx(10.0)


def test_speed_multiplier_not_affect_elapsed():
    """倍率不影响 elapsed，只影响实时等待。"""
    clock = SimulationClock(time_step=0.1, speed_multiplier=10.0)
    clock.tick()
    assert clock.elapsed == 0.1


# ── SimulationParams ─────────────────────────────────────────────────

def test_simulation_params_defaults():
    p = SimulationParams()
    assert p.time_step == 0.1
    assert p.total_time == 600.0
    assert p.speed_multiplier == 1.0
    assert p.target_speed_ratio == 0.8
    assert p.station_stop_tolerance == 1.0


def test_simulation_params_custom():
    p = SimulationParams(
        time_step=0.05,
        total_time=1200.0,
        target_speed_ratio=0.9,
        station_stop_tolerance=2.0,
    )
    assert p.time_step == 0.05
    assert p.total_time == 1200.0
    assert p.target_speed_ratio == 0.9
    assert p.station_stop_tolerance == 2.0


# ── load_simulation_params ───────────────────────────────────────────

def test_load_from_yaml():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fp:
        fp.write(
            "simulation:\n"
            "  time_step: 0.2\n"
            "  total_time: 300.0\n"
            "  speed_multiplier: 2.0\n"
            "  target_speed_ratio: 0.7\n"
            "  station_stop_tolerance: 1.5\n"
        )
        tmp = fp.name
    try:
        p = load_simulation_params(tmp)
        assert p.time_step == 0.2
        assert p.total_time == 300.0
        assert p.speed_multiplier == 2.0
        assert p.target_speed_ratio == 0.7
        assert p.station_stop_tolerance == 1.5
    finally:
        Path(tmp).unlink()


def test_load_from_yaml_flat_format():
    """支持直接顶层字段，无需 simulation: 包裹。"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fp:
        fp.write("time_step: 0.05\ntotal_time: 100.0\n")
        tmp = fp.name
    try:
        p = load_simulation_params(tmp)
        assert p.time_step == 0.05
        assert p.total_time == 100.0
    finally:
        Path(tmp).unlink()


def test_load_from_empty_yaml_uses_defaults():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fp:
        fp.write("")
        tmp = fp.name
    try:
        p = load_simulation_params(tmp)
        assert p.time_step == 0.1
        assert p.total_time == 600.0
    finally:
        Path(tmp).unlink()


def test_load_with_partial_fields():
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fp:
        fp.write("simulation:\n  time_step: 0.01\n")
        tmp = fp.name
    try:
        p = load_simulation_params(tmp)
        assert p.time_step == 0.01
        assert p.total_time == 600.0  # default
    finally:
        Path(tmp).unlink()
