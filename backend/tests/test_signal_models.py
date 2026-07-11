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
    yaml_text = """
simulation:
  signal_mode: atp_ato
  atp:
    safety_distance: 300
    overspeed_margin: 0.05
  ats:
    dwell_adjust_mode: extend
    min_dwell_time: 15
    max_dwell_time: 300
  following:
    min_interval: 500
"""
    p = tmp_path / "simulation.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    params = load_simulation_params(p)
    assert params.signal.mode == "atp_ato"
    assert params.signal.atp.safety_distance == 300.0
    assert params.signal.ats.dwell_adjust_mode == "extend"
    assert params.signal.following_min_interval == 500.0
