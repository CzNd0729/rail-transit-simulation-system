"""再生制动能量统计（PWR-04）。

单车独立统计，按固定效率计算再生电量，不模拟多车就近吸收。
"""

from __future__ import annotations


def calculate_regen_power(
    brake_force: float, speed_ms: float, efficiency: float = 0.3
) -> float:
    """计算再生制动功率 (W)。

    Args:
        brake_force: 当前施加的制动力 (N)。
        speed_ms: 当前速度 (m/s)。
        efficiency: 再生制动效率系数，默认 0.3。

    Returns:
        回收功率 (W)，即电功率输出。
    """
    if brake_force <= 0 or speed_ms <= 0:
        return 0.0
    return brake_force * speed_ms * efficiency


def calculate_traction_power(traction_force: float, speed_ms: float) -> float:
    """计算牵引消耗功率 (W)。

    Args:
        traction_force: 当前牵引力 (N)。
        speed_ms: 当前速度 (m/s)。

    Returns:
        消耗功率 (W)。
    """
    if traction_force <= 0 or speed_ms <= 0:
        return 0.0
    return traction_force * speed_ms
