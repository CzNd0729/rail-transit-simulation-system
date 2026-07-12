"""轨道配置加载。"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import Segment, Station, Switch, Track, TrackCircuit


def load_track(path: str | Path) -> Track:
    path = Path(path)
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    if "line" in data:
        data = data["line"]
    stations = [
        Station(
            id=s["id"],
            name=s["name"],
            chainage=float(s["chainage"]),
            dwell_time=float(s.get("dwell_time", 30.0)),
            platform_half_length=float(s.get("platform_half_length", 15.0)),
        )
        for s in data.get("stations", [])
    ]
    segments = [
        Segment(
            id=s["id"],
            start_chainage=float(s["start_chainage"]),
            end_chainage=float(s["end_chainage"]),
            gradient=float(s.get("gradient", 0.0)),
            curvature=float(s.get("curvature", 0.0)),
            speed_limit=float(s.get("speed_limit", 80.0)),
            is_tunnel=bool(s.get("is_tunnel", False)),
        )
        for s in data.get("segments", [])
    ]
    circuits = [
        TrackCircuit(
            id=c["id"],
            start_chainage=float(c["start_chainage"]),
            end_chainage=float(c["end_chainage"]),
            direction=str(c.get("direction", "down")),
        )
        for c in data.get("track_circuits", [])
    ]
    switches = [
        Switch(
            id=s["id"],
            chainage=float(s["chainage"]),
            switch_type=str(s.get("switch_type", "single")),
            normal_direction=str(s.get("normal_direction", "main")),
            reverse_direction=str(s.get("reverse_direction", "siding")),
            lateral_speed_limit=float(s.get("lateral_speed_limit", 30.0)),
            state=str(s.get("state", "normal")),
        )
        for s in data.get("switches", [])
    ]
    return Track(
        name=data.get("name", "线路"),
        direction=str(data.get("direction", "down")),
        stations=stations,
        segments=segments,
        circuits=circuits,
        switches=switches,
    )
