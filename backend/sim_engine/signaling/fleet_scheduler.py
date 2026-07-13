"""持续派车调度器（时刻表 headway + 始发站容量闸门）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from sim_engine.signaling.models import DispatchConfig, ServiceTimetable


class _ActiveRun(Protocol):
    active: bool
    direction: str

    @property
    def state(self) -> object: ...


@dataclass
class DispatchTickResult:
    dispatched_ids: list[str]
    blocked: bool
    next_departure_time: float


def origin_clearance_ok(
    active_runs: list[_ActiveRun],
    origin_chainage: float,
    direction: str,
    min_clearance_m: float,
) -> bool:
    """同向列车中，距始发点最近一列的净距须 >= min_clearance_m。"""
    same_dir = [
        r for r in active_runs
        if r.active and getattr(r, "direction", r.state.direction) == direction
    ]
    if not same_dir:
        return True
    if direction == "down":
        nearest_ahead = min(r.state.position for r in same_dir)
        return nearest_ahead >= origin_chainage + min_clearance_m
    nearest_ahead = max(r.state.position for r in same_dir)
    return origin_chainage - nearest_ahead >= min_clearance_m


class FleetScheduler:
    """按 headway 持续派车；阻塞时不跳班。"""

    def __init__(self, service: ServiceTimetable, origin_chainage: float = 0.0):
        self._dispatch: DispatchConfig = service.dispatch
        self._origin_chainage = origin_chainage
        self._direction = service.dispatch.initial_direction
        self._next_departure_time = service.dispatch.first_departure_s
        self._train_serial = 0
        self._pattern_index = 0

    @property
    def next_departure_time(self) -> float:
        return self._next_departure_time

    def reset(self) -> None:
        self._next_departure_time = self._dispatch.first_departure_s
        self._train_serial = 0
        self._pattern_index = 0

    def _advance_headway_clock(self) -> None:
        pattern = self._dispatch.headway_pattern_s
        if pattern:
            step = pattern[self._pattern_index % len(pattern)]
            self._pattern_index += 1
        else:
            step = self._dispatch.headway_s
        self._next_departure_time += step

    def tick(
        self,
        elapsed: float,
        active_runs: list[_ActiveRun],
        create_run: Callable[[str, float], object],
    ) -> DispatchTickResult:
        """尝试派发所有到点的列车；阻塞时保留班次不推进时钟。"""
        dispatched_ids: list[str] = []
        blocked = False
        max_active = self._dispatch.max_active_trains

        while elapsed >= self._next_departure_time and len(active_runs) + len(dispatched_ids) < max_active:
            if not origin_clearance_ok(
                active_runs + [_DispatchProbe(self._direction, d) for d in dispatched_ids],
                self._origin_chainage,
                self._direction,
                self._dispatch.min_origin_clearance_m,
            ):
                blocked = True
                break

            self._train_serial += 1
            train_id = f"TRAIN_{self._train_serial:02d}"
            create_run(train_id, self._next_departure_time)
            dispatched_ids.append(train_id)
            self._advance_headway_clock()

        return DispatchTickResult(
            dispatched_ids=dispatched_ids,
            blocked=blocked,
            next_departure_time=self._next_departure_time,
        )


@dataclass
class _DispatchProbe:
    """tick 循环内已派未加入 active_runs 的占位，用于 clearance 检测。"""

    direction: str
    train_id: str
    active: bool = True

    @property
    def state(self) -> object:
        return _ProbeState(0.0)


@dataclass(frozen=True)
class _ProbeState:
    position: float
