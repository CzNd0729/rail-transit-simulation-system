"""组装 API 文档 8.4.2 格式的 simulation_snapshot（供 WebSocket 层直接序列化）。"""

from __future__ import annotations

from sim_engine.core.clock import SimulationClock
from sim_engine.core.config import SimulationParams
from sim_engine.vehicle.models import ForceBreakdown, TrainState


def build_simulation_snapshot(
    clock: SimulationClock,
    sim_params: SimulationParams,
    train_id: str,
    state: TrainState,
    forces: ForceBreakdown,
    pantograph_voltage: float = 1500.0,
) -> dict:
    """构建单列车 MVP 快照（camelCase，与 API 文档对齐）。"""
    display_mode = state.mode
    if state.speed < 0.01:
        display_mode = "stopped"

    return {
        "type": "simulation_snapshot",
        "timestamp": clock.elapsed,
        "data": {
            "clock": {
                "elapsed": clock.elapsed,
                "speedMultiplier": clock.speed_multiplier,
            },
            "trains": [
                {
                    "id": train_id,
                    "position": state.position,
                    "speed": state.speed,
                    "acceleration": state.acceleration,
                    "mode": display_mode,
                    "mass": state.mass,
                    "passengerCount": int(state.passenger_load * 1500),
                    "pantographVoltage": pantograph_voltage,
                    "powerDemand": 0.0,
                    "tractionForce": forces.traction,
                    "totalResistance": forces.resistance_total,
                    "brakeForce": forces.brake,
                    "doorStatus": "closed",
                    "runningBrakeForce": forces.brake,
                    "faultAlarm": None,
                }
            ],
            "power": {
                "substations": [],
                "voltageProfile": [],
                "totalConsumption": 0.0,
                "totalRegeneration": 0.0,
            },
            "signaling": {
                "controlCommands": [
                    {
                        "trainId": train_id,
                        "tractionLevel": 0.0,
                        "brakeLevel": 0.0,
                        "emergencyBrake": False,
                    }
                ],
                "emergencyBrakes": [],
            },
            "track": {"occupancy": [], "switchStates": []},
            "events": [],
        },
    }
