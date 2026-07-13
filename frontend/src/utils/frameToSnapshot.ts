import type { MockReplayFrame, SimulationSnapshot, SpeedMultiplier, TrainMode } from '../types/simulation';
import { MA_ENVELOPE_LENGTH, MOCK_LINE_TOTAL_LENGTH } from './constants';

const DEFAULT_TRAIN_ID = 'TRAIN_01';
const DEFAULT_SPEED_LIMIT = 80;
const ATP_OVERSPEED_MARGIN = 0.05;

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

function resolveMaEndChainage(frame: MockReplayFrame): number {
  if (frame.ma_end_chainage != null) {
    return frame.ma_end_chainage;
  }
  if (frame.distance_to_station != null && frame.distance_to_station > 0) {
    return frame.position + frame.distance_to_station;
  }
  const safety = frame.safety_distance ?? MA_ENVELOPE_LENGTH;
  return Math.min(frame.position + safety, MOCK_LINE_TOTAL_LENGTH);
}

export function frameToSnapshot(
  frame: MockReplayFrame,
  speedMultiplier: SpeedMultiplier = 1,
): SimulationSnapshot {
  const runningPhase = deriveRunningPhase(frame.mode, frame.speed, frame.running_phase);
  const tractionLevel = frame.traction_level ?? (frame.mode === 'traction' ? 0.8 : 0);
  const brakeLevel = frame.brake_level ?? (frame.mode === 'braking' ? 0.5 : 0);
  const safetyDistance = frame.safety_distance ?? MA_ENVELOPE_LENGTH;
  const permanentLimit = frame.permanent_speed_limit ?? DEFAULT_SPEED_LIMIT;
  const atpLimit = frame.atp_speed_limit
    ?? permanentLimit * (1 - ATP_OVERSPEED_MARGIN);

  return {
    clock: { elapsed: frame.t, speed_multiplier: speedMultiplier },
    trains: [{
      id: DEFAULT_TRAIN_ID,
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
      direction: 'up',
      fault_alarm: null,
      traction_force: frame.traction_force ?? 0,
      brake_force: frame.brake_force ?? 0,
      total_resistance: frame.total_resistance ?? 0,
    }],
    power: {
      substations: [],
      voltage_profile: [{ chainage: frame.position, voltage: frame.pantograph_voltage }],
      total_consumption: frame.traction_energy_kwh ?? 0,
      total_regeneration: frame.regen_energy_kwh ?? 0,
      regeneration_rate: 0,
    },
    signaling: {
      commands: [{
        train_id: DEFAULT_TRAIN_ID,
        traction_level: tractionLevel,
        brake_level: brakeLevel,
        emergency_brake: false,
        running_phase: runningPhase,
      }],
      emergency_brake: [],
      train_intervals: [],
      ma_profiles: [{
        train_id: DEFAULT_TRAIN_ID,
        ma_end_chainage: resolveMaEndChainage(frame),
        safety_distance: safetyDistance,
      }],
      speed_limits: [{
        train_id: DEFAULT_TRAIN_ID,
        permanent_limit: permanentLimit,
        atp_limit: atpLimit,
      }],
      timetable_deviations: frame.timetable_deviation
        ? [frame.timetable_deviation]
        : [],
    },
    track: { occupancy: [], switch_states: [] },
    events: [],
  };
}
