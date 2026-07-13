import { describe, it, expect } from 'vitest';
import { getDisplayMode } from '../../../utils/format';

/** 与 ModeIndicator 组件内 displayMode 推导逻辑一致 */
function resolveIndicatorMode(
  mode: string | undefined,
  speed: number,
  runningPhase?: string,
): string {
  return getDisplayMode(mode, speed, runningPhase);
}

describe('ModeIndicator display mode', () => {
  it('shows stopped when running_phase is dwell', () => {
    expect(resolveIndicatorMode('coasting', 5, 'dwell')).toBe('stopped');
  });

  it('shows traction when running_phase is traction', () => {
    expect(resolveIndicatorMode('traction', 40, 'traction')).toBe('traction');
  });

  it('shows braking when mode is braking', () => {
    expect(resolveIndicatorMode('braking', 30, 'braking')).toBe('braking');
  });

  it('shows stopped at low speed coasting without dwell phase', () => {
    expect(resolveIndicatorMode('coasting', 0.2)).toBe('stopped');
  });
});
