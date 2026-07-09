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
  });

  it('preserves stopped mode from backend', () => {
    const raw = {
      clock: { elapsed: 0, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 1500, speed: 0, acceleration: 0,
        mode: 'stopped' as const, mass: 200000, passengerCount: 0,
        pantographVoltage: 1500, powerDemand: 0, doorStatus: 'closed' as const,
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
});
