"""车辆系统 I/O 数据类型定义。

本模块是车辆系统对外的类型契约：轨道 / 信号 / 编排器等其他子系统通过
import 这里的 dataclass 与车辆系统交互。所有对外速度单位统一为 km/h，
内部动力学解算换算为 m/s。
"""

from __future__ import annotations

from dataclasses import dataclass, field

GRAVITY = 9.81
"""重力加速度 (m/s^2)。"""

AIR_DENSITY = 1.225
"""空气密度 (kg/m^3)。"""

PERSON_MASS = 60.0
"""单名乘客平均质量 (kg)，用于按载客率折算总质量。"""


@dataclass(frozen=True)
class TractionCurvePoint:
    """牵引特性曲线折点。"""

    speed: float
    """速度 (km/h)。"""

    force_percent: float
    """该速度下可用牵引力占最大牵引力的比例 (0.0 ~ 1.0)。"""


@dataclass
class VehicleParams:
    """车辆固有参数。

    Davis 系数 A、B 已归一化（乘以 m·g 前的无量纲系数）。空气阻力项单独
    由迎风面积与风阻系数计算。
    """

    empty_mass: float
    """空车质量 (kg)。"""

    passenger_capacity: int
    """满员载客人数。"""

    max_speed: float
    """构造速度 (km/h)。"""

    max_traction_force: float
    """最大牵引力 (N)。"""

    max_brake_force: float
    """最大制动力 (N)。"""

    davis_a: float
    """Davis 公式 A 系数（归一化，滚动阻力）。"""

    davis_b: float
    """Davis 公式 B 系数（归一化，线性项，按 m/s 计）。"""

    davis_c_front_area: float
    """迎风面积 (m^2)。"""

    davis_c_drag_coeff: float
    """空气阻力系数 Cd。"""

    curve_resist_coeff: float = 600.0
    """弯道阻力经验系数 k（‰·m），r_c(‰) = k / R。"""

    tunnel_resist_factor: float = 1.2
    """隧道空气阻力加成系数（>1 表示隧道内阻力增大）。"""

    traction_curve: list[TractionCurvePoint] = field(default_factory=list)
    """牵引特性曲线折点，按速度升序排列。"""

    regeneration_efficiency: float = 0.3
    """再生制动效率（VHC-09 预留，迭代一暂不参与计算）。"""

    length: float = 120.0
    """列车长度 (m)。"""

    def mass_at_load(self, passenger_load: float) -> float:
        """按载客率 (0.0~1.0) 折算列车总质量 (kg)。"""
        load = min(max(passenger_load, 0.0), 1.0)
        return self.empty_mass + load * self.passenger_capacity * PERSON_MASS


@dataclass
class ControlCommands:
    """来自信号系统的控车指令。"""

    traction_level: float = 0.0
    """牵引级位 [0, 1]。"""

    brake_level: float = 0.0
    """常用制动级位 [0, 1]。"""

    emergency_brake: bool = False
    """紧急制动标志（触发时按最大制动力）。"""


@dataclass
class TrackPointParams:
    """车辆系统所需的当前位置线路参数（来自轨道系统）。"""

    gradient: float = 0.0
    """坡度 (‰，上坡为正)。"""

    curvature: float = 0.0
    """曲线半径 (m)，直线取 0（或极大值），表示无弯道阻力。"""

    speed_limit: float = 80.0
    """区段限速 (km/h)。"""

    is_tunnel: bool = False
    """是否处于隧道内。"""


@dataclass
class TrainState:
    """列车运行状态。"""

    position: float = 0.0
    """当前公里标 (m)。"""

    speed: float = 0.0
    """当前速度 (km/h)。"""

    acceleration: float = 0.0
    """当前加速度 (m/s^2)。"""

    mode: str = "coasting"
    """当前工况：``traction`` / ``coasting`` / ``braking``。"""

    mass: float = 0.0
    """当前总质量 (kg)。"""

    passenger_load: float = 0.0
    """当前载客率 (0.0~1.0)。"""

    traction_energy: float = 0.0
    """累计牵引能耗 (J)。VHC-09 预留，迭代一恒为 0。"""

    regen_energy: float = 0.0
    """累计再生制动电量 (J)。VHC-09 预留，迭代一恒为 0。"""


@dataclass
class ForceBreakdown:
    """单步受力分解（供 VHC-10 记录与前端阻力分解图使用），单位均为 N。"""

    traction: float = 0.0
    """牵引力。"""

    brake: float = 0.0
    """制动力。"""

    davis: float = 0.0
    """Davis 基本阻力。"""

    gradient: float = 0.0
    """坡度附加阻力（下坡为负）。"""

    curve: float = 0.0
    """弯道附加阻力。"""

    tunnel: float = 0.0
    """隧道附加空气阻力。"""

    resistance_total: float = 0.0
    """总阻力（davis + gradient + curve + tunnel）。"""

    net: float = 0.0
    """合力（traction - brake - resistance_total）。"""


@dataclass
class StepResult:
    """一个仿真步的解算结果。"""

    state: TrainState
    """更新后的列车状态。"""

    forces: ForceBreakdown
    """本步受力分解。"""
