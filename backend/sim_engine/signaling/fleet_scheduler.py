"""持续派车调度器（时刻表 headway + 始发站容量闸门）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from sim_engine.signaling.models import DispatchConfig, DispatchOrigin, ServiceTimetable


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


def _run_direction(run: object) -> str:
    direction = getattr(run, "direction", None)
    if direction is not None:
        return str(direction)
    return str(getattr(run.state, "direction", ""))


def _run_position(run: object) -> float:
    return float(run.state.position)


def origin_clearance_ok(
    active_runs: list[_ActiveRun],
    origin_chainage: float,
    direction: str,
    min_clearance_m: float,
) -> bool:
    """同向列车中，距始发点最近一列的净距须 >= min_clearance_m。"""
    same_dir = [
        r for r in active_runs
        if getattr(r, "active", True) and _run_direction(r) == direction
    ]
    if not same_dir:
        return True
    if direction == "down":
        nearest_ahead = min(_run_position(r) for r in same_dir)
        return nearest_ahead >= origin_chainage + min_clearance_m
    nearest_ahead = max(_run_position(r) for r in same_dir)
    return origin_chainage - nearest_ahead >= min_clearance_m


def resolve_dispatch_origins(
    dispatch: DispatchConfig,
    trip_leg_names: tuple[str, ...],
    station_chainages: dict[str, float],
) -> tuple[DispatchOrigin, ...]:
    """将 dispatch 解析为派车端列表（兼容单端 legacy 字段）。"""
    if dispatch.origins:
        return dispatch.origins
    chainage = station_chainages.get(dispatch.origin_station, 0.0)
    return (
        DispatchOrigin(
            origin_station=dispatch.origin_station,
            origin_chainage=chainage,
            initial_direction=dispatch.initial_direction,
            trip_leg_names=trip_leg_names,
            train_id_prefix="",
            first_departure_s=dispatch.first_departure_s,
            headway_s=dispatch.headway_s,
            headway_pattern_s=dispatch.headway_pattern_s,
        ),
    )


@dataclass
class _DispatchStreamState:
    origin: DispatchOrigin
    next_departure_time: float
    train_serial: int = 0
    pattern_index: int = 0

    def format_train_id(self) -> str:
        self.train_serial += 1
        prefix = self.origin.train_id_prefix
        if prefix:
            return f"TRAIN_{prefix}{self.train_serial:02d}"
        return f"TRAIN_{self.train_serial:02d}"

    def advance_headway(self) -> None:
        pattern = self.origin.headway_pattern_s
        if pattern:
            step = pattern[self.pattern_index % len(pattern)]
            self.pattern_index += 1
        else:
            step = self.origin.headway_s
        self.next_departure_time += step


class FleetScheduler:
    """多端持续派车；阻塞时不跳班。"""

    def __init__(
        self,
        service: ServiceTimetable,
        station_chainages: dict[str, float] | None = None,
    ):
        self._dispatch = service.dispatch
        self._trip_leg_names = service.trip_leg_names
        chainages = station_chainages or {}
        origins = resolve_dispatch_origins(
            self._dispatch, self._trip_leg_names, chainages
        )
        self._streams = [
            _DispatchStreamState(
                origin=origin,
                next_departure_time=origin.first_departure_s,
            )
            for origin in origins
        ]

    @property
    def next_departure_time(self) -> float:
        if not self._streams:
            return 0.0
        return min(s.next_departure_time for s in self._streams)

    def reset(self) -> None:
        for stream in self._streams:
            stream.next_departure_time = stream.origin.first_departure_s
            stream.train_serial = 0
            stream.pattern_index = 0

    def tick(
        self,
        elapsed: float,
        active_runs: list[_ActiveRun],
        create_run: Callable[..., object],
    ) -> DispatchTickResult:
        """尝试派发所有到点的列车；阻塞时保留班次不推进时钟。"""
        dispatched: list[tuple[str, str, float]] = []
        blocked = False
        max_active = self._dispatch.max_active_trains
        min_clearance = self._dispatch.min_origin_clearance_m

        for stream in self._streams:
            origin = stream.origin
            while (
                elapsed >= stream.next_departure_time
                and len(active_runs) + len(dispatched) < max_active
            ):
                probes: list[object] = list(active_runs) + [
                    _DispatchProbe(direction, position, train_id)
                    for train_id, direction, position in dispatched
                ]
                if not origin_clearance_ok(
                    probes,
                    origin.origin_chainage,
                    origin.initial_direction,
                    min_clearance,
                ):
                    blocked = True
                    break

                train_id = stream.format_train_id()
                create_run(
                    train_id,
                    stream.next_departure_time,
                    origin.initial_direction,
                    origin.trip_leg_names,
                    origin.origin_chainage,
                )
                dispatched.append(
                    (train_id, origin.initial_direction, origin.origin_chainage)
                )
                stream.advance_headway()

        return DispatchTickResult(
            dispatched_ids=[item[0] for item in dispatched],
            blocked=blocked,
            next_departure_time=self.next_departure_time,
        )


@dataclass
class _DispatchProbe:
    """tick 循环内已派未加入 active_runs 的占位，用于 clearance 检测。"""

    direction: str
    position: float
    train_id: str
    active: bool = True

    @property
    def state(self) -> object:
        return _ProbeState(self.position)


@dataclass(frozen=True)
class _ProbeState:
    position: float
