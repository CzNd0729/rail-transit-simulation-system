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
class Track:
    name: str
    stations: list[Station] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)

    @property
    def total_length(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_chainage for s in self.segments)
