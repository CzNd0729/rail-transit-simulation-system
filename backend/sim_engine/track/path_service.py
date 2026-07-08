"""位置查询服务（TRK-02 ~ TRK-04）。"""

from __future__ import annotations

from sim_engine.vehicle.models import TrackPointParams

from .models import Segment, Station, Track


class TrackPathService:
    """一维公里标路径查询。"""

    def __init__(self, track: Track):
        self.track = track
        self._stations = sorted(track.stations, key=lambda s: s.chainage)

    def query_at(self, chainage: float) -> TrackPointParams:
        """给定公里标，返回线路参数。"""
        seg = self._segment_at(chainage)
        if seg is None:
            return TrackPointParams()
        return TrackPointParams(
            gradient=seg.gradient,
            curvature=seg.curvature,
            speed_limit=seg.speed_limit,
            is_tunnel=seg.is_tunnel,
        )

    def next_station_ahead(self, chainage: float) -> Station | None:
        """前方最近车站（严格大于当前位置）。"""
        for st in self._stations:
            if st.chainage > chainage + 0.01:
                return st
        return None

    def station_at(self, chainage: float, half_length: float = 15.0) -> Station | None:
        """判断是否在站台范围内。"""
        for st in self._stations:
            if abs(chainage - st.chainage) <= half_length:
                return st
        return None

    def _segment_at(self, chainage: float) -> Segment | None:
        for seg in self.track.segments:
            if seg.start_chainage <= chainage <= seg.end_chainage:
                return seg
        if self.track.segments:
            if chainage < self.track.segments[0].start_chainage:
                return self.track.segments[0]
            return self.track.segments[-1]
        return None
