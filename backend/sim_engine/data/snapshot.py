"""组装 API 文档 8.4.2 格式的 simulation_snapshot（供 WebSocket 层直接序列化）。"""

from __future__ import annotations

from dataclasses import dataclass

from sim_engine.core.clock import SimulationClock
from sim_engine.core.config import SimulationParams
from sim_engine.vehicle.models import ForceBreakdown, TrainState


@dataclass
class TrainSnapshotEntry:
    """单列车快照条目（多车 snapshot 的基本单元）。"""

    train_id: str
    state: TrainState
    forces: ForceBreakdown
    pantograph_voltage: float = 1500.0
    power_demand: float = 0.0
    direction: str = "up"


def _serialize_train(entry: TrainSnapshotEntry) -> dict:
    display_mode = entry.state.mode
    if entry.state.speed < 0.01:
        display_mode = "stopped"
    return {
        "id": entry.train_id,
        "position": entry.state.position,
        "speed": entry.state.speed,
        "acceleration": entry.state.acceleration,
        "jerk": entry.state.jerk,
        "mode": display_mode,
        "direction": entry.state.direction,
        "mass": entry.state.mass,
        "passengerCount": int(entry.state.passenger_load * 1500),
        "pantographVoltage": entry.pantograph_voltage,
        "powerDemand": entry.power_demand,
        "tractionForce": entry.forces.traction,
        "totalResistance": entry.forces.resistance_total,
        "brakeForce": entry.forces.brake,
        "doorStatus": "closed",
        "runningBrakeForce": entry.forces.brake,
        "faultAlarm": None,
        "distanceToStation": entry.state.distance_to_station,
        "targetStationId": entry.state.target_station_id,
        "direction": entry.direction,
    }


def build_simulation_snapshot(
    clock: SimulationClock,
    sim_params: SimulationParams,
    train_entries: list[TrainSnapshotEntry],
    voltage_profile: list[dict] | None = None,
    substation_states: list | None = None,
    signaling_extra: dict | None = None,
    occupancy: list[dict] | None = None,
    switch_states: list[dict] | None = None,
) -> dict:
    """构建 simulation_snapshot（camelCase，与 API 文档对齐）。"""
    if not train_entries:
        raise ValueError("train_entries must not be empty")

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

    vp = voltage_profile or []

    total_consumption_kwh = sum(
        e.state.traction_energy / 3_600_000.0 for e in train_entries
    )
    total_regeneration_kwh = sum(
        e.state.regen_energy / 3_600_000.0 for e in train_entries
    )

    extra = dict(signaling_extra or {})
    control_commands = extra.pop(
        "controlCommands",
        [
            {
                "trainId": e.train_id,
                "tractionLevel": 0.0,
                "brakeLevel": 0.0,
                "emergencyBrake": False,
            }
            for e in train_entries
        ],
    )

    signaling: dict = {
        "controlCommands": control_commands,
        "emergencyBrakes": [],
        "speedLimits": extra.pop("speedLimits", []),
        "maProfile": extra.pop("maProfile", []),
        "timetableDeviation": extra.pop("timetableDeviation", []),
        "trainIntervals": extra.pop("trainIntervals", []),
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
            "trains": [_serialize_train(e) for e in train_entries],
            "power": {
                "substations": subs,
                "voltageProfile": vp,
                "totalConsumption": total_consumption_kwh,
                "totalRegeneration": total_regeneration_kwh,
            },
            "signaling": signaling,
            "track": {"occupancy": occupancy or [], "switchStates": switch_states or []},
            "events": [],
        },
    }
