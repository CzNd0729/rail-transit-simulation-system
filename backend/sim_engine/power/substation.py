"""变电所模型（PWR-03）。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Substation:
    """牵引变电所。

    简单整流外特性模型：输出端电压随负载电流线性跌落。
    """

    id: str
    """变电所唯一标识。"""

    name: str
    """变电所名称（前端展示用）。"""

    chainage: float
    """变电所所在公里标 (m)。"""

    rated_voltage: float = 1500.0
    """额定直流输出空载电压 (V)。"""

    rated_power: float = 5000.0
    """额定容量 (kW)。"""

    output_current: float = 0.0
    """当前输出电流 (A)。"""

    output_power: float = 0.0
    """当前输出功率 (kW)。"""


@dataclass
class SubstationState:
    """变电所当前运行状态（用于 snapshot 序列化）。"""

    id: str
    name: str
    chainage: float
    rated_voltage: float
    rated_power: float
    output_current: float
    output_power: float
