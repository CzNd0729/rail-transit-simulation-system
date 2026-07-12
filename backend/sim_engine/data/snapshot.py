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
    power_demand: float = 0.0,
    voltage_profile: list[dict] | None = None,
    substation_states: list | None = None,
    signaling_extra: dict | None = None,
    occupancy: list[dict] | None = None,
) -> dict:
    """构建单列车 MVP 快照（camelCase，与 API 文档对齐）。"""
    display_mode = state.mode
    if state.speed < 0.01:
        display_mode = "stopped"

    # 变电所状态序列化
    if substation_states:
        subs = [
            {
                "id": s.id,
                "name": s.name,
                "chainage": s.chainage,
                "ratedVoltage": s.rated_voltage,
                "ratedPower": s.rated_power,
                "outputCurrent": s.output_current,
                "outputPower": s.output_power,
            }
            for s in substation_states
        ]
    else:
        subs = []

    # 电压曲线（当前步采样点）
    vp = voltage_profile or []

    # 能耗数据（J → kWh，供前端展示）
    total_consumption_kwh = state.traction_energy / 3_600_000.0  # J → kWh
    total_regeneration_kwh = state.regen_energy / 3_600_000.0

    extra = dict(signaling_extra or {})
    running_phase = extra.pop("runningPhase", None)
    control_cmd: dict = {
        "trainId": train_id,
        "tractionLevel": 0.0,
        "brakeLevel": 0.0,
        "emergencyBrake": False,
    }
    if running_phase is not None:
        control_cmd["runningPhase"] = running_phase

    signaling: dict = {
        "controlCommands": [control_cmd],
        "emergencyBrakes": [],
        "speedLimits": extra.pop("speedLimits", []),
        "maProfile": extra.pop("maProfile", []),
        "timetableDeviation": extra.pop("timetableDeviation", []),
    }
    signaling.update(extra)

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
                    "jerk": state.jerk,
                    "mode": display_mode,
                    "mass": state.mass,
                    "passengerCount": int(state.passenger_load * 1500),
                    "pantographVoltage": pantograph_voltage,
                    "powerDemand": power_demand,
                    "tractionForce": forces.traction,
                    "totalResistance": forces.resistance_total,
                    "brakeForce": forces.brake,
                    "doorStatus": "closed",
                    "runningBrakeForce": forces.brake,
                    "faultAlarm": None,
                    "distanceToStation": state.distance_to_station,
                    "targetStationId": state.target_station_id,
                }
            ],
            "power": {
                "substations": subs,
                "voltageProfile": vp,
                "totalConsumption": total_consumption_kwh,
                "totalRegeneration": total_regeneration_kwh,
            },
            "signaling": signaling,
            "track": {"occupancy": occupancy or [], "switchStates": []},
            "events": [],
        },
    }
