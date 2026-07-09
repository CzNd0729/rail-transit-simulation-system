"""数据记录与快照模块单元测试（ENG-REC-01~03, build_simulation_snapshot）。"""

from __future__ import annotations

import csv
import io
from pathlib import Path
import math
import tempfile

import pytest

from sim_engine.core.clock import SimulationClock
from sim_engine.core.config import SimulationParams
from sim_engine.data.recorder import DataRecorder, StepRecord
from sim_engine.data.snapshot import build_simulation_snapshot
from sim_engine.vehicle.models import (
    ForceBreakdown,
    TrainState,
    TrackPointParams,
)


# ── StepRecord ───────────────────────────────────────────────────────

def test_step_record_defaults():
    r = StepRecord(
        time=1.0,
        position=100.0,
        speed=50.0,
        acceleration=0.5,
        jerk=0.0,
        mode="traction",
        traction_force=10000.0,
        brake_force=0.0,
        total_resistance=5000.0,
    )
    assert r.time == 1.0
    assert r.position == 100.0
    assert r.speed == 50.0
    assert r.acceleration == 0.5
    assert r.mode == "traction"
    assert r.traction_force == 10000.0
    assert r.brake_force == 0.0
    assert r.total_resistance == 5000.0


# ── DataRecorder 基本操作 ────────────────────────────────────────────

def test_recorder_empty_buffer():
    r = DataRecorder()
    assert len(r.buffer) == 0


def test_record_appends():
    r = DataRecorder()
    r.record(StepRecord(0.1, 0.0, 0.0, 0.0, 0.0, "coasting", 0.0, 0.0, 0.0))
    r.record(StepRecord(0.2, 5.0, 10.0, 1.0, 0.0, "traction", 50000.0, 0.0, 2000.0))
    assert len(r.buffer) == 2
    assert r.buffer[1].speed == 10.0


def test_clear_empties_buffer():
    r = DataRecorder()
    r.record(StepRecord(0.1, 0.0, 0.0, 0.0, 0.0, "coasting", 0.0, 0.0, 0.0))
    assert len(r.buffer) == 1
    r.clear()
    assert len(r.buffer) == 0


# ── DataRecorder.summary() ──────────────────────────────────────────

def test_summary_empty():
    r = DataRecorder()
    s = r.summary()
    assert s == {"steps": 0, "total_time": 0.0, "avg_speed": 0.0, "max_speed": 0.0}


def test_summary_single_record():
    r = DataRecorder()
    r.record(StepRecord(0.1, 2.0, 30.0, 0.5, 0.0, "traction", 40000.0, 0.0, 5000.0))
    s = r.summary()
    assert s["steps"] == 1
    assert s["total_time"] == 0.1
    assert s["avg_speed"] == 30.0
    assert s["max_speed"] == 30.0


def test_summary_multiple_records():
    r = DataRecorder()
    for i in range(5):
        r.record(StepRecord(
            time=i * 0.1,
            position=i * 5.0,
            speed=10.0 + i * 10.0,  # 10, 20, 30, 40, 50
            acceleration=1.0,
            jerk=0.0,
            mode="traction",
            traction_force=40000.0,
            brake_force=0.0,
            total_resistance=5000.0,
        ))
    s = r.summary()
    assert s["steps"] == 5
    assert s["total_time"] == 0.4
    assert s["avg_speed"] == pytest.approx(30.0)
    assert s["max_speed"] == 50.0


# ── DataRecorder.export_csv() ────────────────────────────────────────

def test_export_csv_header():
    r = DataRecorder()
    r.record(StepRecord(0.1, 2.0, 30.0, 0.5, 0.0, "traction", 40000.0, 0.0, 5000.0))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    ) as fp:
        tmp = fp.name
    try:
        r.export_csv(tmp)
        content = Path(tmp).read_text(encoding="utf-8")
        assert "time,position,speed,mode,acceleration" in content
        assert "traction_force,brake_force,total_resistance" in content
    finally:
        Path(tmp).unlink()


def test_export_csv_rows():
    r = DataRecorder()
    r.record(StepRecord(0.1, 2.0, 30.0, 0.5, 0.0, "traction", 40000.0, 0.0, 5000.0))
    r.record(StepRecord(0.2, 5.0, 35.0, 0.3, 0.0, "traction", 38000.0, 0.0, 4800.0))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    ) as fp:
        tmp = fp.name
    try:
        r.export_csv(tmp)
        content = Path(tmp).read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows
        assert "30.0" in lines[1]
        assert "35.0" in lines[2]
    finally:
        Path(tmp).unlink()


def test_export_csv_empty_buffer():
    r = DataRecorder()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    ) as fp:
        tmp = fp.name
    try:
        r.export_csv(tmp)
        content = Path(tmp).read_text(encoding="utf-8")
        # 只有 header，没有数据行
        assert "time,position" in content
        lines = content.strip().split("\n")
        assert len(lines) == 1
    finally:
        Path(tmp).unlink()


# ── build_simulation_snapshot ────────────────────────────────────────

def test_snapshot_basic_structure():
    clock = SimulationClock(time_step=0.1, elapsed=5.0, speed_multiplier=2.0)
    sim_params = SimulationParams()
    state = TrainState(
        position=100.0, speed=50.0, acceleration=0.5,
        mode="traction", mass=260000.0, passenger_load=0.6,
    )
    forces = ForceBreakdown(
        traction=100000.0, brake=0.0, davis=5000.0,
        gradient=0.0, curve=0.0, tunnel=0.0,
        resistance_total=5000.0, net=95000.0,
    )
    snap = build_simulation_snapshot(clock, sim_params, "TRAIN_01", state, forces)
    assert snap["type"] == "simulation_snapshot"
    assert snap["timestamp"] == 5.0
    assert "data" in snap
    assert "trains" in snap["data"]
    assert len(snap["data"]["trains"]) == 1


def test_snapshot_train_fields():
    clock = SimulationClock(elapsed=10.0)
    sim_params = SimulationParams()
    state = TrainState(
        position=200.0, speed=60.0, acceleration=0.3,
        mode="coasting", mass=250000.0, passenger_load=0.5,
    )
    forces = ForceBreakdown(
        traction=0.0, brake=0.0, davis=4000.0,
        gradient=1000.0, curve=0.0, tunnel=0.0,
        resistance_total=5000.0, net=-5000.0,
    )
    snap = build_simulation_snapshot(clock, sim_params, "TRAIN_02", state, forces)
    train = snap["data"]["trains"][0]
    assert train["id"] == "TRAIN_02"
    assert train["position"] == 200.0
    assert train["speed"] == 60.0
    assert train["acceleration"] == 0.3
    assert train["jerk"] == 0.0
    assert train["mode"] == "coasting"
    assert train["mass"] == 250000.0
    assert train["pantographVoltage"] == 1500.0
    assert train["doorStatus"] == "closed"


def test_snapshot_stopped_display_mode():
    """速度接近 0 时 mode 显示为 stopped。"""
    clock = SimulationClock()
    sim_params = SimulationParams()
    state = TrainState(
        position=500.0, speed=0.0, acceleration=0.0,
        mode="braking", mass=260000.0, passenger_load=0.6,
    )
    forces = ForceBreakdown(brake=350000.0)
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces)
    assert snap["data"]["trains"][0]["mode"] == "stopped"


def test_snapshot_has_power_section():
    clock = SimulationClock()
    sim_params = SimulationParams()
    state = TrainState(mass=260000.0)
    forces = ForceBreakdown()
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces)
    pwr = snap["data"]["power"]
    assert "substations" in pwr
    assert "voltageProfile" in pwr
    assert "totalConsumption" in pwr
    assert "totalRegeneration" in pwr


def test_snapshot_has_signaling_section():
    clock = SimulationClock()
    sim_params = SimulationParams()
    state = TrainState(mass=260000.0)
    forces = ForceBreakdown()
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces)
    sig = snap["data"]["signaling"]
    assert "controlCommands" in sig
    assert len(sig["controlCommands"]) == 1


def test_snapshot_custom_pantograph_voltage():
    clock = SimulationClock()
    sim_params = SimulationParams()
    state = TrainState(mass=260000.0)
    forces = ForceBreakdown()
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces, pantograph_voltage=1800.0)
    assert snap["data"]["trains"][0]["pantographVoltage"] == 1800.0


def test_snapshot_clock_fields():
    clock = SimulationClock(elapsed=123.45, speed_multiplier=5.0)
    sim_params = SimulationParams()
    state = TrainState(mass=260000.0)
    forces = ForceBreakdown()
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces)
    c = snap["data"]["clock"]
    assert c["elapsed"] == 123.45
    assert c["speedMultiplier"] == 5.0


def test_snapshot_passenger_count():
    clock = SimulationClock()
    sim_params = SimulationParams()
    state = TrainState(mass=260000.0, passenger_load=0.8)
    forces = ForceBreakdown()
    snap = build_simulation_snapshot(clock, sim_params, "T1", state, forces)
    # passengerCount = int(0.8 * 1500) = 1200
    assert snap["data"]["trains"][0]["passengerCount"] == 1200
