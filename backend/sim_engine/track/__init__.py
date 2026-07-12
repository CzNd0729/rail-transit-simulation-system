"""轨道系统（MVP 最小实现）：一维路径 + 位置查询（TRK-01 ~ TRK-04）。"""

from .config import load_track
from .models import Segment, Station, Switch, Track, TrackCircuit, TrackLine
from .occupancy import OccupancyDetector
from .path_service import TrackPathService
from .switch import SwitchManager

__all__ = [
    "Segment",
    "Station",
    "Switch",
    "Track",
    "TrackCircuit",
    "TrackLine",
    "TrackPathService",
    "OccupancyDetector",
    "SwitchManager",
    "load_track",
]
