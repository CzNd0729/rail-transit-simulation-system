"""多车追踪间隔（SIG-07 占位，迭代三实现）。"""

from __future__ import annotations


def tracking_gap(front_pos: float, rear_pos: float, direction: str) -> float:
    """同向追踪间隔 (m)：前方列车在前、后方列车在后时的净距。"""
    if direction == "up":
        return rear_pos - front_pos
    return front_pos - rear_pos


def is_interval_safe(
    front_pos: float,
    rear_pos: float,
    min_interval: float,
    *,
    direction: str = "down",
) -> bool:
    """判断追踪间隔是否满足最小安全距离。

    参数 front/rear 为同向运行时的前方/后方列车 chainage。
    下行：front > rear；上行：front < rear。
    """
    return tracking_gap(front_pos, rear_pos, direction) >= min_interval
