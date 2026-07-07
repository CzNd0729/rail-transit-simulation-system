"""牵引特性曲线（VHC-02）。

采用分段线性模型：给定速度，通过折点列表线性插值得到可用牵引力百分比，
再乘以最大牵引力与牵引级位得到实际牵引力。
"""

from __future__ import annotations

from .models import TractionCurvePoint


def interpolate_force_percent(
    curve: list[TractionCurvePoint], speed_kmh: float
) -> float:
    """按速度在牵引特性曲线上线性插值，返回可用牵引力百分比 (0.0~1.0)。

    - 曲线为空时退化为恒定 100%。
    - 速度低于首折点或高于末折点时，分别取端点值（不外推）。
    """
    if not curve:
        return 1.0

    points = sorted(curve, key=lambda p: p.speed)

    if speed_kmh <= points[0].speed:
        return points[0].force_percent
    if speed_kmh >= points[-1].speed:
        return points[-1].force_percent

    for left, right in zip(points, points[1:]):
        if left.speed <= speed_kmh <= right.speed:
            span = right.speed - left.speed
            if span == 0:
                return left.force_percent
            ratio = (speed_kmh - left.speed) / span
            return left.force_percent + ratio * (
                right.force_percent - left.force_percent
            )

    return points[-1].force_percent


def traction_force(
    curve: list[TractionCurvePoint],
    max_traction_force: float,
    speed_kmh: float,
    level: float,
) -> float:
    """计算当前牵引力 (N)。

    :param level: 牵引级位 [0, 1]，会被钳位到合法区间。
    """
    level = min(max(level, 0.0), 1.0)
    percent = interpolate_force_percent(curve, speed_kmh)
    return max_traction_force * percent * level
