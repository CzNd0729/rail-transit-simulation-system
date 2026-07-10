import { describe, it, expect } from 'vitest';
import { getDisplayMode, getSignalPhaseLabel, resolveSignalPhase } from './format';

describe('getDisplayMode', () => {
  it('returns stopped when runningPhase is dwell', () => {
    expect(getDisplayMode('coasting', 0, 'dwell')).toBe('stopped');
  });

  it('returns stopped when mode is stopped', () => {
    expect(getDisplayMode('stopped', 0)).toBe('stopped');
  });

  it('returns stopped when coasting at low speed', () => {
    expect(getDisplayMode('coasting', 0.2)).toBe('stopped');
  });

  it('returns traction when actively accelerating', () => {
    expect(getDisplayMode('traction', 50, 'traction')).toBe('traction');
  });

  it('defaults to coasting when mode is undefined', () => {
    expect(getDisplayMode(undefined, 30)).toBe('coasting');
  });
});

describe('getSignalPhaseLabel', () => {
  it('maps known phases to Chinese', () => {
    expect(getSignalPhaseLabel('traction')).toBe('牵引');
    expect(getSignalPhaseLabel('dwell')).toBe('站停');
  });

  it('returns raw phase for unknown values', () => {
    expect(getSignalPhaseLabel('unknown')).toBe('unknown');
  });
});

describe('resolveSignalPhase', () => {
  it('prefers runningPhase from backend', () => {
    expect(resolveSignalPhase('braking', 'traction', 0.8, 0)).toBe('braking');
  });

  it('derives braking from brake level', () => {
    expect(resolveSignalPhase(undefined, 'braking', 0, 0.6)).toBe('braking');
  });

  it('derives traction from traction level', () => {
    expect(resolveSignalPhase(undefined, 'traction', 0.5, 0)).toBe('traction');
  });

  it('returns dwell for stopped mode', () => {
    expect(resolveSignalPhase(undefined, 'stopped', 0, 0)).toBe('dwell');
  });
});
