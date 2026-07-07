"""车辆系统子模块。

对外暴露 I/O 数据类型、动力学解算引擎与配置加载函数，供仿真编排器集成。
"""

from .models import (
    ControlCommands,
    ForceBreakdown,
    StepResult,
    TractionCurvePoint,
    TrackPointParams,
    TrainState,
    VehicleParams,
)
from .config import load_vehicle_params
from .dynamics import VehicleSystem

__all__ = [
    "ControlCommands",
    "ForceBreakdown",
    "StepResult",
    "TractionCurvePoint",
    "TrackPointParams",
    "TrainState",
    "VehicleParams",
    "VehicleSystem",
    "load_vehicle_params",
]
