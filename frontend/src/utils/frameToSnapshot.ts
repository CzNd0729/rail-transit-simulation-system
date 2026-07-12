import type { MockReplayFrame, SimulationSnapshot, SpeedMultiplier, TrainMode } from '../types/simulation';
import { EMPTY_SIGNAL_STATE } from '../types/simulation';

function deriveRunningPhase(
  mode: TrainMode,
  speed: number,
  framePhase?: string,
): string {
  if (framePhase) return framePhase;
  if (mode === 'stopped' || (mode === 'coasting' && speed < 0.5)) return 'dwell';
  if (mode === 'braking') return 'braking';
  if (mode === 'traction') return 'traction';
  return 'coasting';
}

export function frameToSnapshot(
  frame: MockReplayFrame,
  speedMultiplier: SpeedMultiplier = 1,
): SimulationSnapshot {
  const runningPhase = deriveRunningPhase(frame.mode, frame.speed, frame.running_phase);
  const tractionLevel = frame.traction_level ?? (frame.mode === 'traction' ? 0.8 : 0);
  const brakeLevel = frame.brake_level ?? (frame.mode === 'braking' ? 0.5 : 0);

  return {
    clock: { elapsed: frame.t, speed_multiplier: speedMultiplier },
    trains: [{
      id: 'TRAIN_01',
      position: frame.position,
      speed: frame.speed,
      acceleration: frame.acceleration,
      jerk: frame.jerk ?? 0,
      mode: frame.mode,
      mass: frame.mass,
      passenger_count: frame.passenger_count,
      door_status: 'closed',
      pantograph_voltage: frame.pantograph_voltage,
      power_demand: frame.power_demand,
      distance_to_station: frame.distance_to_station ?? 0,
      target_station_id: frame.target_station_id ?? '',
      fault_alarm: null,
    }],
    power: {
      substations: [],
      voltage_profile: [{ chainage: frame.position, voltage: frame.pantograph_voltage }],
      total_consumption: 0,
      total_regeneration: 0,
      regeneration_rate: 0,
    },
    signaling: {
      ...EMPTY_SIGNAL_STATE,
      commands: [{
        train_id: 'TRAIN_01',
        traction_level: tractionLevel,
        brake_level: brakeLevel,
        emergency_brake: false,
        running_phase: runningPhase,
      }],
    },
    track: { occupancy: [], switch_states: [] },
    events: [],
  };
}
