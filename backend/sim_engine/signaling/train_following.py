"""多车追踪间隔（SIG-07 占位，迭代三实现）。"""

from __future__ import annotations


def is_interval_safe(following_pos: float, leading_pos: float, min_interval: float) -> bool:
    """判断追踪间隔是否满足最小安全距离。"""
    return (following_pos - leading_pos) >= min_interval
