"""仿真全局参数加载。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PidParams:
    """PID 控制器参数。"""

    kp: float = 0.08
    """比例增益。"""

    ki: float = 0.002
    """积分增益。"""

    kd: float = 0.01
    """微分增益。"""

    integral_max: float = 0.3
    """积分项输出上限（防止 windup）。"""

    output_min: float = -1.0
    """输出下限（负数=制动，正数=牵引）。"""

    output_max: float = 1.0
    """输出上限。"""

    comfort_decel: float = 0.8
    """制动曲线舒适减速度 (m/s²)，建议为最大减速能力的 60~70%。"""

    deadband_v: float = 0.3
    """速度死区 (km/h)，误差在该范围内时微分项归零避免振荡。"""

    deadband_d: float = 1.0
    """距离死区 (m)，距站台该距离内切换为蠕行模式。"""

    creep_gain: float = 0.25
    """蠕行模式制动力随距离衰减系数。"""

    brake_safety_factor: float = 1.05
    """刹车触发距离安全系数（基于 comfort_decel）。原 1.1 对应紧急减速度，
    现在改为 comfort_decel 后安全余量可降至 1.05。"""


@dataclass
class SimulationParams:
    time_step: float = 0.1
    total_time: float = 600.0
    speed_multiplier: float = 1.0
    target_speed_ratio: float = 0.8
    station_stop_tolerance: float = 1.0
    coasting_min_speed: float = 30.0
    pid: PidParams = field(default_factory=PidParams)


def _load_pid_params(data: dict) -> PidParams:
    pid_data = data.get("pid", {}) or {}
    return PidParams(
        kp=float(pid_data.get("kp", 0.08)),
        ki=float(pid_data.get("ki", 0.002)),
        kd=float(pid_data.get("kd", 0.01)),
        integral_max=float(pid_data.get("integral_max", 0.3)),
        comfort_decel=float(pid_data.get("comfort_decel", 0.8)),
        deadband_v=float(pid_data.get("deadband_v", 0.3)),
        deadband_d=float(pid_data.get("deadband_d", 1.0)),
        creep_gain=float(pid_data.get("creep_gain", 0.25)),
        brake_safety_factor=float(pid_data.get("brake_safety_factor", 1.05)),
    )


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
        coasting_min_speed=float(data.get("coasting_min_speed", 30.0)),
        pid=_load_pid_params(data),
    )
