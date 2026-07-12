"""轨道区段占用检测器（TRK-07 / TRK-10 / TRK-11）。

每仿真步根据所有列车位置更新轨道电路区段占用状态，
供信号系统和前端轨道视图使用。
"""

from __future__ import annotations

from .models import TrackCircuit


class OccupancyDetector:
    """轨道区段占用/出清检测器。

    检测逻辑（TRK-11）：
    1. 每步开始时清空所有区段占用状态
    2. 遍历所有列车位置，判断所在区段
    3. 标记对应区段为占用
    """

    def __init__(self, circuits: list[TrackCircuit]):
        self._circuits: list[TrackCircuit] = [
            TrackCircuit(
                id=c.id,
                start_chainage=c.start_chainage,
                end_chainage=c.end_chainage,
                direction=c.direction,
                occupied=False,
            )
            for c in circuits
        ]

    # ── TRK-11: 批量更新占用 ──────────────────────────────

    def update(self, train_positions: dict[str, float]) -> None:
        """根据所有列车位置更新占用状态。

        Args:
            train_positions: {train_id: chainage} 映射
        """
        # 清空所有区段
        for c in self._circuits:
            c.occupied = False

        # 标记占用
        for position in train_positions.values():
            tc = self._circuit_at(position)
            if tc is not None:
                tc.occupied = True

    # ── TRK-10: 单区段占用查询 ────────────────────────────

    def query_circuit(self, chainage: float) -> TrackCircuit | None:
        """给定公里标，返回所在轨道电路区段（TRK-10）。"""
        return self._circuit_at(chainage)

    def is_occupied(self, chainage: float) -> bool:
        """给定公里标，返回该位置所在区段是否被占用。"""
        tc = self._circuit_at(chainage)
        return tc.occupied if tc else False

    # ── 状态快照 ──────────────────────────────────────────

    def state(self) -> list[TrackCircuit]:
        """返回当前所有区段的占用状态副本。"""
        return [
            TrackCircuit(
                id=c.id,
                start_chainage=c.start_chainage,
                end_chainage=c.end_chainage,
                direction=c.direction,
                occupied=c.occupied,
            )
            for c in self._circuits
        ]

    def occupancy_list(self) -> list[dict]:
        """返回轻量级占用列表，供 snapshot 序列化。

        格式与 API 文档 附录 B 对齐，并包含链程信息供前端直接渲染：
            {"circuitId": "TC01", "startChainage": 0, "endChainage": 1100,
             "direction": "down", "occupied": true}
        """
        return [
            {
                "circuitId": c.id,
                "startChainage": c.start_chainage,
                "endChainage": c.end_chainage,
                "direction": c.direction,
                "occupied": c.occupied,
            }
            for c in self._circuits
        ]

    # ── 内部 ──────────────────────────────────────────────

    def _circuit_at(self, chainage: float) -> TrackCircuit | None:
        for c in self._circuits:
            if c.start_chainage <= chainage <= c.end_chainage:
                return c
        # 边界外处理：小于最小起点取第一个，大于最大终点取最后一个
        if self._circuits:
            if chainage < self._circuits[0].start_chainage:
                return self._circuits[0]
            return self._circuits[-1]
        return None
