"""车辆参数配置加载（NFR-07：参数经配置文件注入，不改代码即可调参）。

对外提供 ``load_vehicle_params``：从 YAML 文件解析出 :class:`VehicleParams`。
编排器可选择传入文件路径由本函数解析，也可直接构造 ``VehicleParams`` 对象
（便于单元测试），两种方式并存。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import TractionCurvePoint, VehicleParams

_REQUIRED_KEYS = (
    "empty_mass",
    "passenger_capacity",
    "max_speed",
    "max_traction_force",
    "max_brake_force",
    "davis_a",
    "davis_b",
    "davis_c_front_area",
    "davis_c_drag_coeff",
)


def params_from_dict(data: dict) -> VehicleParams:
    """从普通字典构造 :class:`VehicleParams`，并做基本校验。"""
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"车辆配置缺少必填字段: {', '.join(missing)}")

    raw_curve = data.get("traction_curve", []) or []
    curve = [
        TractionCurvePoint(speed=float(p["speed"]), force_percent=float(p["force_percent"]))
        for p in raw_curve
    ]

    return VehicleParams(
        empty_mass=float(data["empty_mass"]),
        passenger_capacity=int(data["passenger_capacity"]),
        max_speed=float(data["max_speed"]),
        max_traction_force=float(data["max_traction_force"]),
        max_brake_force=float(data["max_brake_force"]),
        davis_a=float(data["davis_a"]),
        davis_b=float(data["davis_b"]),
        davis_c_front_area=float(data["davis_c_front_area"]),
        davis_c_drag_coeff=float(data["davis_c_drag_coeff"]),
        curve_resist_coeff=float(data.get("curve_resist_coeff", 600.0)),
        tunnel_resist_factor=float(data.get("tunnel_resist_factor", 1.2)),
        traction_curve=curve,
        regeneration_efficiency=float(data.get("regeneration_efficiency", 0.3)),
        length=float(data.get("length", 120.0)),
    )


def load_vehicle_params(path: str | Path) -> VehicleParams:
    """从 YAML 文件加载车辆参数。

    支持顶层直接为车辆字段，或包裹在 ``vehicle:`` 键下两种格式。
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}

    if "vehicle" in data and isinstance(data["vehicle"], dict):
        data = data["vehicle"]

    return params_from_dict(data)
