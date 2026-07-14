"""简单欧姆压降计算（PWR-02）。

多列车独立变电所分配模型：每列车匹配最近变电所，按变电所聚合输出功率与电流，
网压取所有列车中最差情况。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .substation import Substation, SubstationState

#: 允许的最低受电弓端电压 (V)，低于此值触发欠压告警。
MIN_PANTOGRAPH_VOLTAGE = 1000.0


@dataclass
class PowerNetwork:
    """直流牵引供电网络。"""

    substations: list[Substation] = field(default_factory=list)
    """变电所列表，按公里标升序排列。"""

    contact_line_resistance: float = 0.02
    """接触网单位长度电阻 (Ω/km)。"""

    rail_resistance: float = 0.01
    """钢轨单位长度电阻 (Ω/km)。"""


@dataclass
class PowerFlowResult:
    """单步潮流计算结果。"""

    pantograph_voltage: float
    """列车受电弓端电压 (V)（所有列车中最差值）。"""

    current: float
    """总取流 (A)，正值=牵引取电，负值=再生回馈。"""

    voltage_drop: float
    """网压跌落 (V)，空载电压 - 受电弓端电压（最差情况）。"""

    supplying_substation_id: str = ""
    """当前供电变电所 ID（负载最大的变电所）。"""

    substation_states: list[SubstationState] = field(default_factory=list)
    """所有变电所当前状态快照（输出按列车聚合）。"""

    undervoltage_warning: bool = False
    """是否触发欠压告警（受电弓端电压 < 1000V）。"""


def _find_nearest_substation(
    substations: list[Substation], chainage: float
) -> Substation | None:
    """找到离给定公里标最近的变电所。"""
    if not substations:
        return None
    return min(substations, key=lambda s: abs(s.chainage - chainage))


def calculate(
    network: PowerNetwork,
    train_demands: list[dict],
    nominal_voltage: float = 1500.0,
) -> PowerFlowResult:
    """执行多列车简化潮流计算。

    每列车独立匹配最近变电所，按变电所聚合输出功率与电流。

    Args:
        network: 供电网络参数。
        train_demands: 列车需求列表，每项为 {"position": float, "power": float}。
            position: 列车公里标 (m)。
            power: 列车需求功率 (W)，牵引为正，制动再生为负。
        nominal_voltage: 额定网压 (V)，用于估算电流。

    Returns:
        PowerFlowResult：最差受电弓端电压、聚合后的变电所状态等。
    """
    substations = network.substations

    # ── 无变电所配置时返回默认固定网压 ──
    if not substations:
        return PowerFlowResult(
            pantograph_voltage=nominal_voltage,
            current=0.0,
            voltage_drop=0.0,
            substation_states=[],
        )

    if not train_demands:
        return PowerFlowResult(
            pantograph_voltage=nominal_voltage,
            current=0.0,
            voltage_drop=0.0,
            substation_states=[],
        )

    r_per_km = network.contact_line_resistance + network.rail_resistance

    # 按变电所聚合
    sub_total_power: dict[str, float] = defaultdict(float)
    sub_total_current: dict[str, float] = defaultdict(float)
    min_voltage = nominal_voltage
    undervoltage = False
    total_current = 0.0

    for td in train_demands:
        pos = td["position"]
        power = td["power"]

        nearest = _find_nearest_substation(substations, pos)
        if nearest is None:
            continue

        distance_km = abs(pos - nearest.chainage) / 1000.0
        loop_resistance = r_per_km * distance_km

        if nominal_voltage > 0 and power > 0:
            current = power / nominal_voltage
        else:
            current = 0.0

        voltage_drop = current * loop_resistance
        raw_voltage = nominal_voltage - voltage_drop
        if raw_voltage < MIN_PANTOGRAPH_VOLTAGE:
            undervoltage = True
        panto_voltage = max(raw_voltage, MIN_PANTOGRAPH_VOLTAGE)

        if panto_voltage < min_voltage:
            min_voltage = panto_voltage

        sub_power_kw = panto_voltage * current / 1000.0
        if sub_power_kw > nearest.rated_power:
            sub_power_kw = nearest.rated_power

        sub_total_power[nearest.id] += sub_power_kw
        sub_total_current[nearest.id] += current
        total_current += current

    # 钳位超出额定容量的变电所
    for s in substations:
        if sub_total_power[s.id] > s.rated_power:
            sub_total_power[s.id] = s.rated_power

    # 找到负载最大的变电所作为 supplying_substation_id
    max_sub_id = ""
    max_sub_power = 0.0
    for s in substations:
        if sub_total_power[s.id] > max_sub_power:
            max_sub_power = sub_total_power[s.id]
            max_sub_id = s.id

    # 构建变电所状态快照
    states: list[SubstationState] = []
    for s in substations:
        states.append(
            SubstationState(
                id=s.id,
                name=s.name,
                chainage=s.chainage,
                rated_voltage=s.rated_voltage,
                rated_power=s.rated_power,
                output_current=sub_total_current.get(s.id, 0.0),
                output_power=sub_total_power.get(s.id, 0.0),
            )
        )

    worst_drop = nominal_voltage - min_voltage

    return PowerFlowResult(
        pantograph_voltage=min_voltage,
        current=total_current,
        voltage_drop=worst_drop,
        supplying_substation_id=max_sub_id,
        substation_states=states,
        undervoltage_warning=undervoltage,
    )
