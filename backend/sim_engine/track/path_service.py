"""位置查询服务（TRK-02 ~ TRK-04）。"""

from __future__ import annotations

from sim_engine.vehicle.models import TrackPointParams

from .models import Segment, Station, Track


class TrackPathService:
    """一维公里标路径查询。"""

    def __init__(self, track: Track):
        self.track = track
        self._stations = sorted(track.stations, key=lambda s: s.chainage)
        self._station_map = {s.id: s for s in track.stations}

    # ── TRK-02: 给定公里标 → 线路参数 ────────────────────────────────

    def query_at(self, chainage: float) -> TrackPointParams:
        """给定公里标，返回坡度、曲率、限速、隧道标识（TRK-02）。"""
        seg = self._segment_at(chainage)
        if seg is None:
            return TrackPointParams()
        return TrackPointParams(
            gradient=seg.gradient,
            curvature=seg.curvature,
            speed_limit=seg.speed_limit,
            is_tunnel=seg.is_tunnel,
        )

    # ── TRK-03: 给定车站 ID → 站台中心公里标 ─────────────────────────

    def get_station_by_id(self, station_id: str) -> Station | None:
        """根据车站 ID 返回 Station 对象（TRK-03）。

        返回 None 表示未找到该 ID 对应的车站。
        """
        return self._station_map.get(station_id)

    def get_station_chainage(self, station_id: str) -> float | None:
        """给定车站 ID，返回站台中心公里标（TRK-03）。

        返回 None 表示未找到该车站。
        """
        st = self._station_map.get(station_id)
        return st.chainage if st else None

    def find_station(self, name: str) -> Station | None:
        """按名称查找车站（辅助方法，用于更方便的查询）。"""
        for st in self._stations:
            if st.name == name:
                return st
        return None

    # ── TRK-04: 站台范围判断 ────────────────────────────────────────

    def station_at(self, chainage: float, half_length: float = 15.0) -> Station | None:
        """判断公里标是否在站台范围内，返回匹配的车站（TRK-04）。"""
        for st in self._stations:
            if abs(chainage - st.chainage) <= half_length:
                return st
        return None

    # ── 辅助查询 ────────────────────────────────────────────────────

    def next_station_ahead(self, chainage: float) -> Station | None:
        """前方最近车站（严格大于当前位置）。"""
        for st in self._stations:
            if st.chainage > chainage + 0.01:
                return st
        return None

    # ── 内部 ────────────────────────────────────────────────────────

    def _segment_at(self, chainage: float) -> Segment | None:
        for seg in self.track.segments:
            if seg.start_chainage <= chainage <= seg.end_chainage:
                return seg
        if self.track.segments:
            if chainage < self.track.segments[0].start_chainage:
                return self.track.segments[0]
            return self.track.segments[-1]
        return None
