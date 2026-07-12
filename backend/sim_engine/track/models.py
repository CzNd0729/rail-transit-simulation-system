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
class Switch:
    """道岔（TRK-06）。

    支持单开和交叉渡线两种类型，具有定位/反位/转换中三种状态，
    转换时延用于模拟机械切换过程。
    """

    id: str                          # 道岔 ID，如 SW01
    chainage: float                  # 道岔中心公里标 (m)
    switch_type: str                 # "single" / "crossover"
    normal_direction: str            # 定位方向，如 "main"
    reverse_direction: str           # 反位方向，如 "siding"
    lateral_speed_limit: float = 30.0  # 侧向限速 (km/h)
    state: str = "normal"            # "normal" / "reverse" / "transitioning"
    transition_time: float = 3.0     # 转换时延 (s)
    transition_elapsed: float = 0.0  # 已转换时间 (s)

    _target_state: str = field(default="normal", repr=False)

    def __post_init__(self) -> None:
        if self._target_state not in ("normal", "reverse"):
            object.__setattr__(self, "_target_state", self.state)


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
    switches: list[Switch] = field(default_factory=list)
    lines: list[TrackLine] = field(default_factory=list)

    @property
    def total_length(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_chainage for s in self.segments)
