"""仿真全局参数加载。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SimulationParams:
    time_step: float = 0.1
    total_time: float = 600.0
    speed_multiplier: float = 1.0
    target_speed_ratio: float = 0.8
    station_stop_tolerance: float = 1.0


def load_simulation_params(path: str | Path) -> SimulationParams:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    if "simulation" in data:
        data = data["simulation"]
    return SimulationParams(
        time_step=float(data.get("time_step", 0.1)),
        total_time=float(data.get("total_time", 600.0)),
        speed_multiplier=float(data.get("speed_multiplier", 1.0)),
        target_speed_ratio=float(data.get("target_speed_ratio", 0.8)),
        station_stop_tolerance=float(data.get("station_stop_tolerance", 1.0)),
    )
