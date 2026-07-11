"""信号系统数据模型（ATP/ATS/时刻表）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SafetyStatus(str, Enum):
    NORMAL = "normal"
    EMERGENCY_BRAKE = "emergency_brake"


@dataclass(frozen=True)
class MaProfile:
    train_id: str
    ma_end_chainage: float
    safety_distance: float


@dataclass(frozen=True)
class TimetableEntry:
    station_id: str
    planned_arrival: float
    planned_departure: float


@dataclass
class Timetable:
    train_id: str
    entries: list[TimetableEntry] = field(default_factory=list)

    def planned_arrival(self, station_id: str) -> float | None:
        for e in self.entries:
            if e.station_id == station_id:
                return e.planned_arrival
        return None


@dataclass(frozen=True)
class TimetableDeviation:
    train_id: str
    station_id: str
    delay_arrival: float
    nominal_dwell: float
    adjusted_dwell: float
