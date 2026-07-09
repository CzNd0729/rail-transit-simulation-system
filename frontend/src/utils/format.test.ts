import { describe, it, expect } from 'vitest';
import { getDisplayMode } from './format';

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
