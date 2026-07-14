"""仿真全局参数加载。

simulation.yaml 只包含仿真器自身参数，子模块配置从同目录独立的 YAML 文件加载：
- pid.yaml     → 制动/控车参数
- power.yaml   → 供电系统配置
- signal.yaml  → 信号系统配置
"""

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
class AtpConfig:
    safety_distance: float = 300.0
    overspeed_margin: float = 0.05


@dataclass
class AtsConfig:
    dwell_adjust_mode: str = "recover"
    min_dwell_time: float = 15.0
    max_dwell_time: float = 300.0


@dataclass
class SignalConfig:
    mode: str = "three_stage"
    atp: AtpConfig = field(default_factory=AtpConfig)
    ats: AtsConfig = field(default_factory=AtsConfig)
    following_min_interval: float = 500.0


@dataclass
class ExternalInterfaceConfig:
    """[已弃用] 外部系统接口配置 — 外部系统接入方案已废弃。"""

    enabled: bool = False
    """是否启用外部接口（已弃用）。"""
    use_real_hardware: bool = False
    """True=连接真实硬件, False=使用内置模拟数据（已弃用）。"""

    plc_device_ip: str = "192.168.100.123"
    plc_deploy_ip: str = "192.168.200.102"
    plc_port: int = 8001
    plc_port_b: int = 8002
    plc_port_c: int = 8003

    network_screen_device_ip: str = "192.168.100.121"
    network_screen_deploy_ip: str = "192.168.200.102"
    network_screen_port: int = 8888

    signal_screen_device_ip: str = "192.168.100.122"
    signal_screen_deploy_ip: str = "192.168.200.102"
    signal_screen_port: int = 9999

    udp_vehicle_model_ip: str = "192.168.200.110"
    udp_vehicle_model_port: int = 23001
    udp_platform_ip: str = "192.168.200.102"
    udp_platform_port: int = 23002


@dataclass
class SimulationParams:
    time_step: float = 0.1
    total_time: float = 600.0
    speed_multiplier: float = 1.0
    target_speed_ratio: float = 0.8
    station_stop_tolerance: float = 1.0
    coasting_min_speed: float = 30.0
    train_count: int = 1
    """每个运行方向上的列车数（双向时上下行各 train_count 列）。"""
    departure_interval: float = 120.0
    """同方向发车间隔 (s)。"""
    dwell_time_override: float | None = None
    """运行时覆盖的默认站停时间 (s)；None 时使用各站 dwell_time。"""
    bidirectional: bool = False
    """True 时同时仿真上行与下行各 train_count 列车。"""
    pid: PidParams = field(default_factory=PidParams)
    power: PowerConfig = field(default_factory=PowerConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    external: ExternalInterfaceConfig = field(default_factory=ExternalInterfaceConfig)  # DEPRECATED

    def total_train_count(self) -> int:
        """编排器应创建的列车总数。"""
        return self.train_count * (2 if self.bidirectional else 1)


# ── 子模块配置文件加载器 ────────────────────────────────────────────


def _try_load_yaml(path: Path) -> dict:
    """尝试加载 YAML 文件，文件不存在时返回空 dict。"""
    if path.exists():
        with path.open("r", encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}
    return {}


def load_pid_params(config_dir: str | Path) -> PidParams:
    """从 pid.yaml 加载制动控车参数。

    Args:
        config_dir: 配置文件所在目录。

    Returns:
        PidParams，文件缺失时返回默认值。
    """
    config_dir = Path(config_dir)
    data = _try_load_yaml(config_dir / "pid.yaml")
    pid_data = data.get("pid", data) or {}
    return PidParams(
        comfort_decel=float(pid_data.get("comfort_decel", 0.8)),
        kp_brake=float(pid_data.get("kp_brake", 0.02)),
        creep_gain=float(pid_data.get("creep_gain", 0.25)),
        deadband_d=float(pid_data.get("deadband_d", 1.0)),
        brake_safety_factor=float(pid_data.get("brake_safety_factor", 1.02)),
        max_jerk=float(pid_data.get("max_jerk", 0.75)),
    )


def load_power_params(config_dir: str | Path) -> PowerConfig:
    """从 power.yaml 加载供电系统配置。

    Args:
        config_dir: 配置文件所在目录。

    Returns:
        PowerConfig，文件缺失时返回默认值。
    """
    config_dir = Path(config_dir)
    data = _try_load_yaml(config_dir / "power.yaml")
    power_data = data.get("power", data) or {}
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


def load_signal_params(config_dir: str | Path) -> SignalConfig:
    """从 signal.yaml 加载信号系统配置。

    Args:
        config_dir: 配置文件所在目录。

    Returns:
        SignalConfig，文件缺失时返回默认值。
    """
    config_dir = Path(config_dir)
    data = _try_load_yaml(config_dir / "signal.yaml")
    sig_data = data.get("signal", data) or {}
    atp_data = sig_data.get("atp", {}) or {}
    ats_data = sig_data.get("ats", {}) or {}
    following_data = sig_data.get("following", {}) or {}
    return SignalConfig(
        mode=str(sig_data.get("mode", "three_stage")),
        atp=AtpConfig(
            safety_distance=float(atp_data.get("safety_distance", 300.0)),
            overspeed_margin=float(atp_data.get("overspeed_margin", 0.05)),
        ),
        ats=AtsConfig(
            dwell_adjust_mode=str(ats_data.get("dwell_adjust_mode", "recover")),
            min_dwell_time=float(ats_data.get("min_dwell_time", 15.0)),
            max_dwell_time=float(ats_data.get("max_dwell_time", 300.0)),
        ),
        following_min_interval=float(following_data.get("min_interval", 500.0)),
    )


# ── 主入口 ───────────────────────────────────────────────────────────


def load_simulation_params(path: str | Path) -> SimulationParams:
    """从 simulation.yaml 加载仿真全局参数，同时自动加载同目录的子模块配置。

    Args:
        path: simulation.yaml 文件路径。

    Returns:
        SimulationParams，包含 pid/power/signal 子配置。
    """
    path = Path(path)
    config_dir = path.parent

    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    if "simulation" in data:
        data = data["simulation"]

    # 从同目录独立文件加载子模块配置
    pid = load_pid_params(config_dir)
    power = load_power_params(config_dir)
    signal = load_signal_params(config_dir)

    # 加载外部接口配置（DEPRECATED）
    ext = data.get("external_interface", {}) or {}
    external = ExternalInterfaceConfig(
        enabled=bool(ext.get("enabled", False)),
        use_real_hardware=bool(ext.get("use_real_hardware", False)),
        plc_device_ip=str(ext.get("plc", {}).get("device_ip", "192.168.100.123")),
        plc_deploy_ip=str(ext.get("plc", {}).get("deploy_ip", "192.168.200.102")),
        plc_port=int(ext.get("plc", {}).get("port", 8001)),
        plc_port_b=int(ext.get("plc", {}).get("port_b", 8002)),
        plc_port_c=int(ext.get("plc", {}).get("port_c", 8003)),
        network_screen_device_ip=str(ext.get("network_screen", {}).get("device_ip", "192.168.100.121")),
        network_screen_deploy_ip=str(ext.get("network_screen", {}).get("deploy_ip", "192.168.200.102")),
        network_screen_port=int(ext.get("network_screen", {}).get("port", 8888)),
        signal_screen_device_ip=str(ext.get("signal_screen", {}).get("device_ip", "192.168.100.122")),
        signal_screen_deploy_ip=str(ext.get("signal_screen", {}).get("deploy_ip", "192.168.200.102")),
        signal_screen_port=int(ext.get("signal_screen", {}).get("port", 9999)),
        udp_vehicle_model_ip=str(ext.get("udp", {}).get("vehicle_model_ip", "192.168.200.110")),
        udp_vehicle_model_port=int(ext.get("udp", {}).get("vehicle_model_port", 23001)),
        udp_platform_ip=str(ext.get("udp", {}).get("platform_ip", "192.168.200.102")),
        udp_platform_port=int(ext.get("udp", {}).get("platform_port", 23002)),
    )

    return SimulationParams(
        time_step=float(data.get("time_step", 0.1)),
        total_time=float(data.get("total_time", 600.0)),
        speed_multiplier=float(data.get("speed_multiplier", 1.0)),
        target_speed_ratio=float(data.get("target_speed_ratio", 0.8)),
        station_stop_tolerance=float(data.get("station_stop_tolerance", 1.0)),
        coasting_min_speed=float(data.get("coasting_min_speed", 30.0)),
        train_count=int(data.get("train_count", 1)),
        departure_interval=float(data.get("departure_interval", 120.0)),
        bidirectional=bool(data.get("bidirectional", False)),
        pid=pid,
        power=power,
        signal=signal,
        external=external,  # DEPRECATED
    )
