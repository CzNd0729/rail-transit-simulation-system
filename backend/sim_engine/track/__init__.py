"""轨道系统（MVP 最小实现）：一维路径 + 位置查询（TRK-01 ~ TRK-04）。"""

from .config import load_track
from .models import Segment, Station, Track
from .path_service import TrackPathService

__all__ = ["Segment", "Station", "Track", "TrackPathService", "load_track"]
