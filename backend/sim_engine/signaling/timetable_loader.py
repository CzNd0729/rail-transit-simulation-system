"""时刻表 YAML 加载。"""

from __future__ import annotations

from pathlib import Path

import yaml

from sim_engine.signaling.models import Timetable, TimetableEntry


def load_timetable(path: str | Path) -> Timetable:
    with Path(path).open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    root = data.get("timetable", data)
    entries = [
        TimetableEntry(
            station_id=str(e["station_id"]),
            planned_arrival=float(e["planned_arrival"]),
            planned_departure=float(e["planned_departure"]),
        )
        for e in root.get("entries", [])
    ]
    return Timetable(train_id=str(root.get("train_id", "TRAIN_01")), entries=entries)
