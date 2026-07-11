"""简单欧姆压降计算（PWR-02）。

单变电所供电模型：计算列车受电弓端电压 = 变电所空载电压 - I × R。
"""

from __future__ import annotations

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
    """列车受电弓端电压 (V)。"""

    current: float
    """列车取流 (A)，正值=牵引取电，负值=再生回馈。"""

    voltage_drop: float
    """网压跌落 (V)，空载电压 - 受电弓端电压。"""

    supplying_substation_id: str = ""
    """当前供电变电所 ID。"""

    substation_states: list[SubstationState] = field(default_factory=list)
    """所有变电所当前状态快照。"""

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
    train_position: float,
    power_demand: float,
    nominal_voltage: float = 1500.0,
) -> PowerFlowResult:
    """执行单步简化潮流计算。

    Args:
        network: 供电网络参数。
        train_position: 列车当前公里标 (m)。
        power_demand: 列车需求功率 (W)，牵引为正，制动再生为负（不模拟回馈网络吸收）。
        nominal_voltage: 额定网压 (V)，用于估算电流。

    Returns:
        PowerFlowResult：受电弓端电压、电流、变电所状态等。
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

    nearest = _find_nearest_substation(substations, train_position)

    if nearest is None:
        return PowerFlowResult(
            pantograph_voltage=nominal_voltage,
            current=0.0,
            voltage_drop=0.0,
            substation_states=[],
        )

    # 距离 (km)
    distance_km = abs(train_position - nearest.chainage) / 1000.0

    # 回路总电阻：接触网 + 钢轨
    r_per_km = network.contact_line_resistance + network.rail_resistance
    loop_resistance = r_per_km * distance_km

    # 列车电流估算 (A)
    if nominal_voltage > 0:
        current = power_demand / nominal_voltage
    else:
        current = 0.0

    # 网压跌落
    voltage_drop = current * loop_resistance
    pantograph_voltage = nominal_voltage - voltage_drop

    # 欠压钳位
    undervoltage_warning = pantograph_voltage < MIN_PANTOGRAPH_VOLTAGE
    pantograph_voltage = max(pantograph_voltage, MIN_PANTOGRAPH_VOLTAGE)

    # 变电所负担
    sub_power_kw = pantograph_voltage * current / 1000.0  # kW
    if sub_power_kw > nearest.rated_power:
        sub_power_kw = nearest.rated_power

    # 构建变电所状态快照
    states: list[SubstationState] = []
    for s in substations:
        if s.id == nearest.id:
            states.append(
                SubstationState(
                    id=s.id,
                    name=s.name,
                    chainage=s.chainage,
                    rated_voltage=s.rated_voltage,
                    rated_power=s.rated_power,
                    output_current=current if current > 0 else 0.0,
                    output_power=sub_power_kw if current > 0 else 0.0,
                )
            )
        else:
            states.append(
                SubstationState(
                    id=s.id,
                    name=s.name,
                    chainage=s.chainage,
                    rated_voltage=s.rated_voltage,
                    rated_power=s.rated_power,
                    output_current=0.0,
                    output_power=0.0,
                )
            )

    return PowerFlowResult(
        pantograph_voltage=pantograph_voltage,
        current=current,
        voltage_drop=voltage_drop,
        supplying_substation_id=nearest.id,
        substation_states=states,
        undervoltage_warning=undervoltage_warning,
    )
