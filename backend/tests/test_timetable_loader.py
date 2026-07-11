"""timetable_loader 单元测试。"""

from __future__ import annotations

from pathlib import Path

from sim_engine.signaling.timetable_loader import load_timetable


def test_load_timetable():
    path = Path(__file__).resolve().parents[1] / "sim_engine/config/timetable.yaml"
    tt = load_timetable(path)
    assert tt.train_id == "TRAIN_01"
    assert tt.planned_arrival("ST02") == 90.0
    assert len(tt.entries) == 3


def test_load_timetable_flat_root(tmp_path):
    yaml_text = """
train_id: TRAIN_02
entries:
  - station_id: ST01
    planned_arrival: 0
    planned_departure: 20
"""
    p = tmp_path / "timetable.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    tt = load_timetable(p)
    assert tt.train_id == "TRAIN_02"
    assert tt.entries[0].planned_departure == 20.0
