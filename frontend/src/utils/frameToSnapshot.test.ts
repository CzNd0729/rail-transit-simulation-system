import { describe, it, expect } from 'vitest';
import { frameToSnapshot } from './frameToSnapshot';
import type { MockReplayFrame } from '../types/simulation';

const frame: MockReplayFrame = {
  t: 10.0, position: 500, speed: 64, acceleration: 0.3,
  mode: 'coasting', mass: 215000, passenger_count: 900,
  pantograph_voltage: 1500, power_demand: 0,
};

describe('frameToSnapshot', () => {
  it('maps frame fields to SimulationSnapshot', () => {
    const snap = frameToSnapshot(frame, 5);
    expect(snap.clock.elapsed).toBe(10.0);
    expect(snap.clock.speed_multiplier).toBe(5);
    expect(snap.trains[0].speed).toBe(64);
    expect(snap.trains[0].mode).toBe('coasting');
    expect(snap.trains[0].position).toBe(500);
  });
});
