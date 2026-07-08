"""编排器与车辆系统集成测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from sim_engine.core.clock import RunState
from sim_engine.orchestrator import Orchestrator, CONFIG_DIR
from sim_engine.track.path_service import TrackPathService
from sim_engine.track.config import load_track

TRACK_YAML = CONFIG_DIR / "track.yaml"


def test_orchestrator_from_config():
    orch = Orchestrator.from_config_dir()
    assert orch.vehicle is not None
    assert orch.track is not None
    assert orch.clock.time_step == 0.1


def test_single_step_advances_train():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    snap = orch.step_once()
    assert snap is not None
    assert snap["type"] == "simulation_snapshot"
    assert orch.train_state is not None
    assert orch.train_state.speed >= 0


def test_run_advances_position():
    orch = Orchestrator.from_config_dir()
    orch.start()
    for _ in range(100):
        orch.step_once()
    assert orch.train_state.position > 0


def test_snapshot_has_vehicle_fields():
    orch = Orchestrator.from_config_dir()
    orch.start()
    snap = orch.step_once()
    train = snap["data"]["trains"][0]
    for key in ("position", "speed", "acceleration", "mode", "tractionForce", "brakeForce"):
        assert key in train


def test_recorder_buffer_grows():
    orch = Orchestrator.from_config_dir()
    orch.start()
    for _ in range(10):
        orch.step_once()
    assert len(orch.recorder.buffer) == 10


def test_pause_and_resume():
    orch = Orchestrator.from_config_dir()
    orch.start()
    orch.step_once()
    orch.pause()
    assert orch.run_state == RunState.PAUSED
    orch.resume()
    assert orch.run_state == RunState.RUNNING


def test_snapshot_callback():
    orch = Orchestrator.from_config_dir()
    received = []
    orch.set_snapshot_callback(lambda s: received.append(s))
    orch.start()
    orch.step_once()
    assert len(received) == 1
    assert received[0]["type"] == "simulation_snapshot"


def test_csv_export(tmp_path):
    orch = Orchestrator.from_config_dir()
    orch.start()
    for _ in range(5):
        orch.step_once()
    out = tmp_path / "run.csv"
    orch.recorder.export_csv(out)
    text = out.read_text(encoding="utf-8")
    assert "time,position,speed" in text
    assert text.count("\n") >= 6


def test_track_next_station():
    track = TrackPathService(load_track(TRACK_YAML))
    nxt = track.next_station_ahead(0.0)
    assert nxt is not None
    assert nxt.id == "ST02"


def test_full_run_reaches_near_terminal():
    """列车应能运行到接近 C 站（不要求精确对标，集成级验证）。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 2000  # 放宽时间上限
    orch.start()
    summary = orch.run_until(max_steps=15000)
    assert summary["steps"] > 100
    assert orch.train_state.position > 2500


# ── 停止/重置状态 ────────────────────────────────────────────────────

def test_stop_transitions_to_stopped():
    orch = Orchestrator.from_config_dir()
    orch.start()
    orch.step_once()
    orch.stop()
    assert orch.run_state == RunState.STOPPED


def test_reset_clears_state():
    orch = Orchestrator.from_config_dir()
    orch.start()
    for _ in range(10):
        orch.step_once()
    orch.reset()
    assert orch.clock.elapsed == 0.0
    assert len(orch.recorder.buffer) == 0
    assert orch.train_state is not None
    assert orch.train_state.position == 0.0
    assert orch.train_state.speed == 0.0


def test_stop_then_reset():
    orch = Orchestrator.from_config_dir()
    orch.start()
    orch.step_once()
    orch.stop()
    assert orch.run_state == RunState.STOPPED
    orch.reset()
    assert orch.run_state == RunState.IDLE


# ── 速度倍率 ────────────────────────────────────────────────────────

def test_speed_multiplier_setting():
    orch = Orchestrator.from_config_dir()
    orch.clock.speed_multiplier = 10.0
    assert orch.clock.speed_multiplier == 10.0


# ── 空步进 ──────────────────────────────────────────────────────────

def test_step_once_initializes_if_no_state():
    orch = Orchestrator.from_config_dir()
    orch.train_state = None
    snap = orch.step_once()
    # 应自动初始化
    assert snap is not None
    assert orch.train_state is not None
    assert orch.clock.elapsed > 0


# ── 终点自动停止 ────────────────────────────────────────────────────

def test_run_until_stops_at_time_limit():
    """超时自动停止。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 1.0  # 1 秒超时
    orch.start()
    summary = orch.run_until()
    assert orch.run_state == RunState.STOPPED
    assert orch.clock.elapsed >= 1.0


# ── 多次重置复用 ────────────────────────────────────────────────────

def test_multiple_runs_with_reset():
    """重置后能重新运行。"""
    orch = Orchestrator.from_config_dir()
    for _ in range(3):
        orch.reset()
        orch.start()
        for _ in range(20):
            orch.step_once()
        assert orch.train_state.position > 0
        orch.stop()
