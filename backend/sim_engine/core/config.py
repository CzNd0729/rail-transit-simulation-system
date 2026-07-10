"""仿真全局参数加载。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SubstationConfig:
    """变电所配置项（配置文件反序列化用）。"""

    id: str = ""
    name: str = ""
    chainage: float = 0.0
    rated_voltage: float = 1500.0
    rated_power: float = 5000.0


@dataclass
class PowerConfig:
    """供电系统配置。"""

    mode: str = "fixed"
    """供电模式："fixed"=固定网压 / "simple_ohm"=欧姆压降。"""

    substations: list[SubstationConfig] = field(default_factory=list)
    """变电所列表。"""

    contact_line_resistance: float = 0.02
    """接触网电阻率 (Ω/km)。"""

    rail_resistance: float = 0.01
    """钢轨电阻率 (Ω/km)。"""


@dataclass
class PidParams:
    """前馈制动参数（原 PID 参数已精简）。"""

    comfort_decel: float = 0.8
    """制动曲线舒适减速度 (m/s²)，前馈核心参数。"""

    kp_brake: float = 0.02
    """制动 P 微调增益（归一化误差 → 制动级位修正量）。"""

    creep_gain: float = 0.25
    """蠕行模式制动力随距离衰减系数。"""

    deadband_d: float = 1.0
    """蠕行触发距离 (m)，距站台该距离内且低速时切换蠕行。"""

    brake_safety_factor: float = 1.02
    """刹车触发距离安全系数。前馈响应快，不再需要大的安全余量。"""

    max_jerk: float = 0.75
    """冲击率上限 (m/s³)，用于牵引/制动级位斜率限制。"""


@dataclass
class SimulationParams:
    time_step: float = 0.1
    total_time: float = 600.0
    speed_multiplier: float = 1.0
    target_speed_ratio: float = 0.8
    station_stop_tolerance: float = 1.0
    coasting_min_speed: float = 30.0
    pid: PidParams = field(default_factory=PidParams)
    power: PowerConfig = field(default_factory=PowerConfig)


def _load_pid_params(data: dict) -> PidParams:
    pid_data = data.get("pid", {}) or {}
    return PidParams(
        comfort_decel=float(pid_data.get("comfort_decel", 0.8)),
        kp_brake=float(pid_data.get("kp_brake", 0.02)),
        creep_gain=float(pid_data.get("creep_gain", 0.25)),
        deadband_d=float(pid_data.get("deadband_d", 1.0)),
        brake_safety_factor=float(pid_data.get("brake_safety_factor", 1.02)),
        max_jerk=float(pid_data.get("max_jerk", 0.75)),
    )


def _load_power_params(data: dict) -> PowerConfig:
    power_data = data.get("power", {}) or {}
    substations = []
    for s in power_data.get("substations", []) or []:
        substations.append(
            SubstationConfig(
                id=str(s.get("id", "")),
                name=str(s.get("name", "")),
                chainage=float(s.get("chainage", 0)),
                rated_voltage=float(s.get("rated_voltage", 1500)),
                rated_power=float(s.get("rated_power", 5000)),
            )
        )
    return PowerConfig(
        mode=str(power_data.get("mode", "fixed")),
        substations=substations,
        contact_line_resistance=float(power_data.get("contact_line_resistance", 0.02)),
        rail_resistance=float(power_data.get("rail_resistance", 0.01)),
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
        power=_load_power_params(data),
    )
