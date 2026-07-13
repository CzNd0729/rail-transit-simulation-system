"""时刻表 YAML 加载（v1 单车 + v2 服务运行图）。"""

from __future__ import annotations

from pathlib import Path

import yaml

from sim_engine.signaling.models import (
    DispatchConfig,
    DispatchOrigin,
    ServiceTimetable,
    Timetable,
    TimetableEntry,
    TimetableLegTemplate,
)


def _parse_entries(raw_entries: list[dict]) -> list[TimetableEntry]:
    return [
        TimetableEntry(
            station_id=str(e["station_id"]),
            planned_arrival=float(e["planned_arrival"]),
            planned_departure=float(e["planned_departure"]),
        )
        for e in raw_entries
    ]


def load_timetable(path: str | Path) -> Timetable:
    """加载 v1 单车时刻表（向后兼容）。"""
    with Path(path).open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    root = data.get("timetable", data)
    if "leg_templates" in root or "dispatch" in root:
        svc = _parse_service_timetable(root)
        legs = materialize_trip_timetables(svc, "TRAIN_01")
        return legs[0] if legs else Timetable(train_id="TRAIN_01", entries=[])
    entries = _parse_entries(root.get("entries", []))
    return Timetable(train_id=str(root.get("train_id", "TRAIN_01")), entries=entries)


def _parse_dispatch_origin(raw: dict, station_chainages: dict[str, float]) -> DispatchOrigin:
    station_id = str(raw["origin_station"])
    trip_legs = tuple(raw.get("trip_legs", ("down", "up")))
    pattern = raw.get("headway_pattern_s") or []
    return DispatchOrigin(
        origin_station=station_id,
        origin_chainage=float(
            raw.get("origin_chainage", station_chainages.get(station_id, 0.0))
        ),
        initial_direction=str(raw.get("initial_direction", "down")),
        trip_leg_names=trip_legs,
        train_id_prefix=str(raw.get("train_id_prefix", "")),
        first_departure_s=float(raw.get("first_departure_s", 0.0)),
        headway_s=float(raw.get("headway_s", 150.0)),
        headway_pattern_s=tuple(float(x) for x in pattern),
    )


def _parse_dispatch(raw: dict, station_chainages: dict[str, float] | None = None) -> DispatchConfig:
    chainages = station_chainages or {}
    pattern = raw.get("headway_pattern_s") or []
    origins_raw = raw.get("origins")
    origins: tuple[DispatchOrigin, ...] = ()
    if origins_raw:
        origins = tuple(
            _parse_dispatch_origin(item, chainages) for item in origins_raw
        )
    return DispatchConfig(
        mode=str(raw.get("mode", "continuous")),
        origin_station=str(raw.get("origin_station", "ST01")),
        initial_direction=str(raw.get("initial_direction", "down")),
        first_departure_s=float(raw.get("first_departure_s", 0.0)),
        headway_s=float(raw.get("headway_s", 150.0)),
        headway_pattern_s=tuple(float(x) for x in pattern),
        max_active_trains=int(raw.get("max_active_trains", 40)),
        min_origin_clearance_m=float(raw.get("min_origin_clearance_m", 500.0)),
        origins=origins,
    )


def _parse_service_timetable(
    root: dict,
    station_chainages: dict[str, float] | None = None,
) -> ServiceTimetable:
    meta = root.get("meta", {})
    switches = meta.get("default_turnback_switch", {})
    dispatch = _parse_dispatch(root.get("dispatch", {}), station_chainages)
    leg_root = root.get("leg_templates", {})
    leg_templates: dict[str, TimetableLegTemplate] = {}
    for name, leg in leg_root.items():
        if name == "trip_legs":
            continue
        if not isinstance(leg, dict):
            continue
        leg_templates[name] = TimetableLegTemplate(
            name=name,
            direction=str(leg.get("direction", name)),
            terminal_station=str(leg["terminal_station"]),
            entries=_parse_entries(leg.get("entries", [])),
        )
    trip_legs = tuple(leg_root.get("trip_legs", ("down", "up")))
    return ServiceTimetable(
        line_name=str(meta.get("line_name", "")),
        turnback_time_s=float(meta.get("turnback_time_s", 150.0)),
        turnback_switch_down=str(switches.get("down", "SW04")),
        turnback_switch_up=str(switches.get("up", "SW01")),
        dispatch=dispatch,
        leg_templates=leg_templates,
        trip_leg_names=trip_legs,
    )


def load_service_timetable(
    path: str | Path,
    station_chainages: dict[str, float] | None = None,
) -> ServiceTimetable:
    """加载 v2 服务运行图（含 dispatch 与 leg 模板）。"""
    with Path(path).open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    root = data.get("timetable", data)
    if "leg_templates" in root or "dispatch" in root:
        return _parse_service_timetable(root, station_chainages)
    entries = _parse_entries(root.get("entries", []))
    fixed_dispatch = DispatchConfig(mode="fixed")
    down_leg = TimetableLegTemplate(
        name="down",
        direction="down",
        terminal_station=entries[-1].station_id if entries else "ST01",
        entries=entries,
    )
    return ServiceTimetable(
        line_name="legacy",
        turnback_time_s=150.0,
        turnback_switch_down="SW04",
        turnback_switch_up="SW01",
        dispatch=fixed_dispatch,
        leg_templates={"down": down_leg},
        trip_leg_names=("down",),
    )


def materialize_trip_timetables(
    service: ServiceTimetable,
    train_id: str,
    trip_leg_names: tuple[str, ...] | None = None,
) -> list[Timetable]:
    """将 leg 模板展开为列车交路时刻表列表（相对时刻，未加仿真绝对偏移）。"""
    leg_names = trip_leg_names or service.trip_leg_names
    legs: list[Timetable] = []
    for leg_name in leg_names:
        template = service.leg_templates.get(leg_name)
        if template is None:
            continue
        legs.append(
            Timetable(
                train_id=train_id,
                entries=list(template.entries),
            )
        )
    return legs
