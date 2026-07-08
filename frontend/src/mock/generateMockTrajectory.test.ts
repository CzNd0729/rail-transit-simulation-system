import { describe, it, expect } from 'vitest';
import { generateMockTrajectory } from './generateMockTrajectory';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';
import type { MockSimInput } from '../types/simulation';

function makeInput(emptyMass: number, overrides?: Partial<MockSimInput>): MockSimInput {
  return {
    vehicle: { ...DEFAULT_VEHICLE_PARAMS, empty_mass: emptyMass },
    track: { gradient: 30, curvature: 1200, speed_limit: 80 },
    signal: { dwell_time: 30, target_speed_ratio: 0.8 },
    passenger_load_ratio: 0.6,
    ...overrides,
  };
}

function arriveTimeAtB(frames: ReturnType<typeof generateMockTrajectory>): number {
  const hit = frames.find((f) => f.position >= 1490 && f.speed < 1);
  return hit?.t ?? Infinity;
}

describe('generateMockTrajectory', () => {
  it('heavier train takes longer between A and B', () => {
    const light = generateMockTrajectory(makeInput(200_000));
    const heavy = generateMockTrajectory(makeInput(220_000));
    expect(arriveTimeAtB(heavy)).toBeGreaterThan(arriveTimeAtB(light));
  });

  it('lower speed limit caps cruise speed', () => {
    const fast = generateMockTrajectory(makeInput(200_000));
    const slow = generateMockTrajectory(makeInput(200_000, {
      track: { gradient: 30, curvature: 1200, speed_limit: 60 },
    }));
    const maxFast = Math.max(...fast.map((f) => f.speed));
    const maxSlow = Math.max(...slow.map((f) => f.speed));
    expect(maxSlow).toBeLessThan(maxFast);
    expect(maxSlow).toBeLessThanOrEqual(60 * 0.8 + 2);
  });

  it('exports trajectory with expected shape', () => {
    const frames = generateMockTrajectory(makeInput(200_000));
    expect(frames.length).toBeGreaterThan(100);
    expect(frames[0].speed).toBe(0);
    expect(frames.some((f) => f.mode === 'traction')).toBe(true);
    expect(frames.some((f) => f.mode === 'braking')).toBe(true);
  });

  it('300t train completes A to C without stuck braking at platform', () => {
    const frames = generateMockTrajectory(makeInput(300_000));
    expect(frames.length).toBeLessThan(MAX_STEPS_GUARD);
    expect(frames.at(-1)?.position).toBe(3200);
    const stuckBraking = frames.filter((f) => f.speed === 0 && f.acceleration < -0.5);
    expect(stuckBraking).toHaveLength(0);
  });

  it('does not coast to standstill mid-segment on uphill', () => {
    const frames = generateMockTrajectory(makeInput(200_000));
    const stations = [0, 1500, 3200];
    const midSegment = frames.filter(
      (f) =>
        f.t > 35
        && f.mode !== 'braking'
        && f.speed > 1
        && !stations.some((s) => Math.abs(f.position - s) <= 15),
    );
    const minCruise = Math.min(...midSegment.map((f) => f.speed));
    expect(minCruise).toBeGreaterThan(20);
  });

  it('zero-speed dwell frames have zero acceleration', () => {
    const frames = generateMockTrajectory(makeInput(300_000));
    const dwellFrames = frames.filter((f) => f.speed === 0 && f.acceleration === 0);
    expect(dwellFrames.length).toBeGreaterThan(100);
  });

  it('braking phase does not flip back to traction', () => {
    const frames = generateMockTrajectory(makeInput(200_000));
    const approachB = frames.filter((f) => f.position >= 1360 && f.position <= 1495 && f.t > 30);
    const tractionFrames = approachB.filter((f) => f.mode === 'traction');
    expect(tractionFrames).toHaveLength(0);
    const accels = approachB.filter((f) => f.mode === 'braking').map((f) => f.acceleration);
    expect(accels.length).toBeGreaterThan(20);
    expect(Math.max(...accels) - Math.min(...accels)).toBeLessThan(0.15);
  });

  it('near-target cruise holds flat speed with zero acceleration', () => {
    const frames = generateMockTrajectory(makeInput(200_000));
    const cruise = frames.filter((f) => f.speed >= 63 && f.speed <= 65 && f.mode === 'coasting');
    expect(cruise.length).toBeGreaterThan(100);
    const speeds = cruise.map((f) => f.speed);
    expect(Math.max(...speeds) - Math.min(...speeds)).toBeLessThan(0.2);
    const accels = cruise.map((f) => f.acceleration);
    expect(Math.max(...accels)).toBeLessThan(0.05);
    expect(Math.min(...accels)).toBeGreaterThan(-0.05);
  });
});

/** 低于积分上限，防止再次生成 60000 帧死循环 */
const MAX_STEPS_GUARD = 50_000;
