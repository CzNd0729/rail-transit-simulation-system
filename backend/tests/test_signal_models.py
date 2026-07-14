"""signaling.models 与 SignalConfig 加载测试。"""

from __future__ import annotations

from sim_engine.core.config import load_simulation_params
from sim_engine.signaling.models import (
    SafetyStatus,
    TimetableEntry,
)


def test_safety_status_values():
    assert SafetyStatus.NORMAL.value == "normal"
    assert SafetyStatus.EMERGENCY_BRAKE.value == "emergency_brake"


def test_timetable_entry_fields():
    e = TimetableEntry(station_id="ST02", planned_arrival=120.0, planned_departure=150.0)
    assert e.station_id == "ST02"


def test_load_signal_config_from_yaml(tmp_path):
    # 写入 signal.yaml（独立信号配置文件）
    signal_yaml = """
signal:
  mode: atp_ato
  atp:
    safety_distance: 300
    overspeed_margin: 0.05
  ats:
    dwell_adjust_mode: recover
    min_dwell_time: 15
    max_dwell_time: 300
  following:
    min_interval: 500
"""
    sp = tmp_path / "signal.yaml"
    sp.write_text(signal_yaml, encoding="utf-8")

    # 写入最小 simulation.yaml（只含仿真器自身参数）
    sim_yaml = """
simulation:
  time_step: 0.1
  total_time: 600.0
"""
    p = tmp_path / "simulation.yaml"
    p.write_text(sim_yaml, encoding="utf-8")

    params = load_simulation_params(p)
    assert params.signal.mode == "atp_ato"
    assert params.signal.atp.safety_distance == 300.0
    assert params.signal.ats.dwell_adjust_mode == "recover"
    assert params.signal.following_min_interval == 500.0


# ── 存车线缓冲区数据模型测试 ──
from sim_engine.signaling.models import BufferSlot, DispatchOrigin


def test_buffer_slot_defaults():
    slot = BufferSlot(
        vehicle_id="VEH_001",
        previous_train_id="D01",
        total_trips=1,
        total_mileage=5000.0,
        passenger_load=0.6,
        state=None,
        arrival_time=2000.0,
    )
    assert slot.vehicle_id == "VEH_001"
    assert slot.total_trips == 1
    assert slot.total_mileage == 5000.0


def test_dispatch_origin_buffer_capacity():
    origin = DispatchOrigin(
        origin_station="ST01",
        origin_chainage=0.0,
        initial_direction="down",
        trip_leg_names=("down", "up"),
    )
    assert origin.buffer_capacity == 1


def test_train_run_vehicle_id():
    from sim_engine.orchestrator import TrainRun

    run = TrainRun(
        train_id="D01",
        state=None,
        signaling=None,
        ats=None,
        manual_driver=None,
    )
    assert run.vehicle_id == ""
    assert run.total_trips == 0
    assert run.total_mileage == 0.0
