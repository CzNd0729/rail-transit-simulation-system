import type { MockReplayFrame, SimulationSnapshot, SpeedMultiplier } from '../types/simulation';

export function frameToSnapshot(
  frame: MockReplayFrame,
  speedMultiplier: SpeedMultiplier = 1,
): SimulationSnapshot {
  return {
    clock: { elapsed: frame.t, speed_multiplier: speedMultiplier },
    trains: [{
      id: 'TRAIN_01',
      position: frame.position,
      speed: frame.speed,
      acceleration: frame.acceleration,
      mode: frame.mode,
      mass: frame.mass,
      passenger_count: frame.passenger_count,
      door_status: 'closed',
      pantograph_voltage: frame.pantograph_voltage,
      power_demand: frame.power_demand,
      fault_alarm: null,
    }],
    power: {
      substations: [],
      voltage_profile: [{ chainage: frame.position, voltage: frame.pantograph_voltage }],
      total_consumption: 0,
      total_regeneration: 0,
      regeneration_rate: 0,
    },
    signaling: { commands: [], emergency_brake: [], train_intervals: [] },
    track: { occupancy: [], switch_states: [] },
    events: [],
  };
}
