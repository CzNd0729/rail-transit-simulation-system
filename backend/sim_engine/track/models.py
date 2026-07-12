"""轨道数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Station:
    id: str
    name: str
    chainage: float
    dwell_time: float = 30.0
    platform_half_length: float = 15.0


@dataclass
class Segment:
    id: str
    start_chainage: float
    end_chainage: float
    gradient: float = 0.0
    curvature: float = 0.0
    speed_limit: float = 80.0
    is_tunnel: bool = False

    @property
    def length(self) -> float:
        return self.end_chainage - self.start_chainage


@dataclass
class TrackCircuit:
    """轨道电路区段（TRK-07）。

    每相邻两个站台之间为一个轨道电路区段，
    用于检测列车占用/出清状态。
    """

    id: str
    start_chainage: float
    end_chainage: float
    direction: str = "down"  # "up" / "down" / "both"
    occupied: bool = False

    @property
    def length(self) -> float:
        return self.end_chainage - self.start_chainage


@dataclass
class TrackLine:
    """单方向线路（TRK-05）。

    为未来上行/下行双线预留，
    当前 MVP 仅使用一条下行线路。
    """

    direction: str  # "up" / "down"
    stations: list[Station] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    track_circuits: list[TrackCircuit] = field(default_factory=list)


@dataclass
class Track:
    name: str
    direction: str = "down"
    stations: list[Station] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    circuits: list[TrackCircuit] = field(default_factory=list)
    lines: list[TrackLine] = field(default_factory=list)

    @property
    def total_length(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_chainage for s in self.segments)
