import { describe, it, expect } from 'vitest';
import { decideMode } from './mockThreeStage';

const base = {
  position: 500,
  nextStationChainage: 1500,
  vTarget: 64,
  mass: 254_000,
  maxBrakeForce: 350_000,
};

describe('decideMode three-stage', () => {
  it('uses traction before reaching target speed', () => {
    expect(decideMode({ ...base, speedKmh: 50 }).mode).toBe('traction');
    expect(decideMode({ ...base, speedKmh: 50 }).cruiseHold).toBe(false);
  });

  it('enters cruise hold at target speed', () => {
    const result = decideMode({ ...base, speedKmh: 64 });
    expect(result.mode).toBe('coasting');
    expect(result.cruiseHold).toBe(true);
  });

  it('stays in cruise hold when already at target', () => {
    const result = decideMode({ ...base, speedKmh: 63.6 });
    expect(result.cruiseHold).toBe(true);
    expect(result.mode).toBe('coasting');
  });

  it('switches to braking near station', () => {
    expect(decideMode({ ...base, speedKmh: 64, position: 1390 }).mode).toBe('braking');
  });
});
