import { describe, it, expect } from 'vitest';
import { parseApiParams, parseServerSnapshot, parseSimulationSummary, toApiParamUpdate } from './apiAdapter';

describe('parseServerSnapshot', () => {
  it('converts camelCase train fields to snake_case', () => {
    const raw = {
      clock: { elapsed: 12.3, speedMultiplier: 5 as const },
      trains: [{
        id: 'TRAIN_01',
        position: 500,
        speed: 64,
        acceleration: 0,
        mode: 'coasting' as const,
        mass: 254000,
        passengerCount: 900,
        pantographVoltage: 1500,
        powerDemand: 0,
        doorStatus: 'closed' as const,
        distanceToStation: 0,
        targetStationId: '',
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: { controlCommands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const snap = parseServerSnapshot(raw);
    expect(snap.clock.speed_multiplier).toBe(5);
    expect(snap.trains[0].passenger_count).toBe(900);
    expect(snap.trains[0].pantograph_voltage).toBe(1500);
    expect(snap.trains[0].jerk).toBe(0);
  });

  it('maps jerk from backend snapshot', () => {
    const raw = {
      clock: { elapsed: 1, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 10, speed: 5, acceleration: 0.5, jerk: 0.12,
        mode: 'traction' as const, mass: 200000, passengerCount: 0,
        pantographVoltage: 1500, powerDemand: 0, doorStatus: 'closed' as const,
        distanceToStation: 0,
        targetStationId: '',
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: { controlCommands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    expect(parseServerSnapshot(raw).trains[0].jerk).toBe(0.12);
  });

  it('preserves stopped mode from backend', () => {
    const raw = {
      clock: { elapsed: 0, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 1500, speed: 0, acceleration: 0,
        mode: 'stopped' as const, mass: 200000, passengerCount: 0,
        pantographVoltage: 1500, powerDemand: 0, doorStatus: 'closed' as const,
        distanceToStation: 0,
        targetStationId: '',
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: { controlCommands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    expect(parseServerSnapshot(raw).trains[0].mode).toBe('stopped');
  });

  it('maps runningPhase from controlCommands', () => {
    const raw = {
      clock: { elapsed: 30, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 1500, speed: 0, acceleration: 0,
        mode: 'stopped' as const, mass: 200000, passengerCount: 900,
        pantographVoltage: 1500, powerDemand: 0, doorStatus: 'closed' as const,
        distanceToStation: 0,
        targetStationId: '',
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: {
        controlCommands: [{
          trainId: 'T1', tractionLevel: 0, brakeLevel: 0, emergencyBrake: false, runningPhase: 'dwell',
        }],
        emergencyBrakes: [],
      },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const snap = parseServerSnapshot(raw);
    expect(snap.signaling.commands[0]?.running_phase).toBe('dwell');
  });

  it('maps maProfile, speedLimits, timetableDeviation from backend', () => {
    const raw = {
      clock: { elapsed: 45, speedMultiplier: 1 as const },
      trains: [{
        id: 'TRAIN_01', position: 800, speed: 60, acceleration: 0,
        mode: 'traction' as const, mass: 254000, passengerCount: 900,
        pantographVoltage: 1480, powerDemand: 1200, doorStatus: 'closed' as const,
        distanceToStation: 700, targetStationId: 'ST_B', faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 1.2, totalRegeneration: 0.3 },
      signaling: {
        controlCommands: [{
          trainId: 'TRAIN_01', tractionLevel: 0.5, brakeLevel: 0,
          emergencyBrake: false, runningPhase: 'traction',
        }],
        emergencyBrakes: [],
        maProfile: [{
          trainId: 'TRAIN_01', maEndChainage: 1500, safetyDistance: 300,
        }],
        speedLimits: [{
          trainId: 'TRAIN_01', permanentLimit: 80, atpLimit: 76,
        }],
        timetableDeviation: [{
          trainId: 'TRAIN_01', stationId: 'ST_A',
          delayArrival: 2.5, nominalDwell: 30, adjustedDwell: 32.5,
        }],
      },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const snap = parseServerSnapshot(raw);
    expect(snap.signaling.ma_profiles[0]).toEqual({
      train_id: 'TRAIN_01',
      ma_end_chainage: 1500,
      safety_distance: 300,
    });
    expect(snap.signaling.speed_limits[0]?.atp_limit).toBe(76);
    expect(snap.signaling.timetable_deviations[0]?.delay_arrival).toBe(2.5);
  });

  it('maps vehicle force fields from backend snapshot', () => {
    const raw = {
      clock: { elapsed: 5, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 800, speed: 40, acceleration: 0.2,
        mode: 'traction' as const, mass: 254000, passengerCount: 900,
        pantographVoltage: 1480, powerDemand: 1200, doorStatus: 'closed' as const,
        distanceToStation: 700, targetStationId: 'ST02', faultAlarm: null,
        tractionForce: 280000, brakeForce: 0, totalResistance: 42000,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 2.5, totalRegeneration: 0.8 },
      signaling: { controlCommands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const train = parseServerSnapshot(raw).trains[0];
    expect(train.traction_force).toBe(280000);
    expect(train.total_resistance).toBe(42000);
  });
});

describe('toApiParamUpdate', () => {
  it('converts vehicle snake_case to camelCase for WS', () => {
    const out = toApiParamUpdate({
      vehicle: { empty_mass: 220000, max_traction_force: 400000 },
      signal: { dwell_time: 35, target_speed_ratio: 0.8 },
    });
    expect(out).toEqual({
      vehicle: { emptyMass: 220000, maxTractionForce: 400000 },
      signal: { dwellTime: 35, targetSpeedRatio: 0.8 },
    });
  });

  it('maps traction_curve to tractionCurve', () => {
    const out = toApiParamUpdate({
      vehicle: {
        traction_curve: [
          { speed: 0, force_percent: 1, sort_order: 0 },
          { speed: 40, force_percent: 0.5, sort_order: 1 },
        ],
      },
    });
    expect(out.vehicle).toEqual({
      tractionCurve: [{ speed: 0, forcePercent: 1 }, { speed: 40, forcePercent: 0.5 }],
    });
  });
});

describe('parseApiParams', () => {
  it('converts REST params camelCase to snake_case', () => {
    const out = parseApiParams({
      vehicle: { emptyMass: 220000, maxTractionForce: 400000 },
      track: { gradient: 30, speedLimit: 80 },
      signal: { targetSpeedRatio: 0.8, dwellTime: 30 },
    });
    expect(out.vehicle?.empty_mass).toBe(220000);
    expect(out.track?.speed_limit).toBe(80);
    expect(out.signal?.target_speed_ratio).toBe(0.8);
  });

  it('parses tractionCurve and segmentId', () => {
    const out = parseApiParams({
      vehicle: {
        tractionCurve: [{ speed: 0, forcePercent: 1 }, { speed: 80, forcePercent: 0.5 }],
      },
      track: { segmentId: 'SEC02', gradient: 30 },
    });
    expect(out.vehicle?.traction_curve).toHaveLength(2);
    expect(out.vehicle?.traction_curve?.[1].force_percent).toBe(0.5);
    expect(out.track?.segment_id).toBe('SEC02');
    expect(out.track?.gradient).toBe(30);
  });
});

describe('parseSimulationSummary', () => {
  it('maps complete summary to SimulationStats fields', () => {
    const stats = parseSimulationSummary({
      steps: 100,
      totalTime: 120.5,
      avgSpeed: 45.2,
      maxSpeed: 64,
    });
    expect(stats.trip_time).toBe(120.5);
    expect(stats.avg_speed).toBe(45.2);
    expect(stats.max_speed).toBe(64);
  });

  it('maps energy fields from simulation summary', () => {
    expect(parseSimulationSummary({
      totalTime: 120,
      avgSpeed: 45,
      maxSpeed: 64,
      totalConsumption: 12.5,
      totalRegeneration: 3.2,
    })).toMatchObject({
      total_energy_consumption: 12.5,
      total_regeneration: 3.2,
    });
  });
});
