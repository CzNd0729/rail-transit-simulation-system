"""时刻表 YAML 加载（v1 单车 + v2 服务运行图）。"""

from __future__ import annotations

from pathlib import Path

import yaml

from sim_engine.signaling.models import (
    DispatchConfig,
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


def _parse_dispatch(raw: dict) -> DispatchConfig:
    pattern = raw.get("headway_pattern_s") or []
    return DispatchConfig(
        mode=str(raw.get("mode", "continuous")),
        origin_station=str(raw.get("origin_station", "ST01")),
        initial_direction=str(raw.get("initial_direction", "down")),
        first_departure_s=float(raw.get("first_departure_s", 0.0)),
        headway_s=float(raw.get("headway_s", 150.0)),
        headway_pattern_s=tuple(float(x) for x in pattern),
        max_active_trains=int(raw.get("max_active_trains", 40)),
        min_origin_clearance_m=float(raw.get("min_origin_clearance_m", 500.0)),
    )


def _parse_service_timetable(root: dict) -> ServiceTimetable:
    meta = root.get("meta", {})
    switches = meta.get("default_turnback_switch", {})
    dispatch = _parse_dispatch(root.get("dispatch", {}))
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


def load_service_timetable(path: str | Path) -> ServiceTimetable:
    """加载 v2 服务运行图（含 dispatch 与 leg 模板）。"""
    with Path(path).open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    root = data.get("timetable", data)
    if "leg_templates" in root or "dispatch" in root:
        return _parse_service_timetable(root)
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


def materialize_trip_timetables(service: ServiceTimetable, train_id: str) -> list[Timetable]:
    """将 leg 模板展开为列车交路时刻表列表（相对时刻，未加仿真绝对偏移）。"""
    legs: list[Timetable] = []
    for leg_name in service.trip_leg_names:
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
