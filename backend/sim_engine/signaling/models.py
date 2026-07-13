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

    def with_absolute_times(self, base_elapsed: float) -> Timetable:
        """将 leg 内相对时刻平移为仿真绝对时刻。"""
        return Timetable(
            train_id=self.train_id,
            entries=[
                TimetableEntry(
                    station_id=e.station_id,
                    planned_arrival=e.planned_arrival + base_elapsed,
                    planned_departure=e.planned_departure + base_elapsed,
                )
                for e in self.entries
            ],
        )


@dataclass(frozen=True)
class TimetableLegTemplate:
    name: str
    direction: str
    terminal_station: str
    entries: list[TimetableEntry]


@dataclass(frozen=True)
class DispatchOrigin:
    """单端持续派车配置。"""

    origin_station: str
    origin_chainage: float
    initial_direction: str
    trip_leg_names: tuple[str, ...]
    train_id_prefix: str = ""
    first_departure_s: float = 0.0
    headway_s: float = 150.0
    headway_pattern_s: tuple[float, ...] = ()


@dataclass(frozen=True)
class DispatchConfig:
    mode: str = "continuous"
    origin_station: str = "ST01"
    initial_direction: str = "down"
    first_departure_s: float = 0.0
    headway_s: float = 150.0
    headway_pattern_s: tuple[float, ...] = ()
    max_active_trains: int = 40
    min_origin_clearance_m: float = 500.0
    origins: tuple[DispatchOrigin, ...] = ()


@dataclass(frozen=True)
class ServiceTimetable:
    line_name: str
    turnback_time_s: float
    turnback_switch_down: str
    turnback_switch_up: str
    dispatch: DispatchConfig
    leg_templates: dict[str, TimetableLegTemplate]
    trip_leg_names: tuple[str, ...] = ("down", "up")


@dataclass(frozen=True)
class TimetableDeviation:
    train_id: str
    station_id: str
    delay_arrival: float
    nominal_dwell: float
    adjusted_dwell: float
