import { describe, it, expect } from 'vitest';
import {
  canPaintCharts,
  nextPhaseAfterBegin,
  nextPhaseAfterEnd,
  nextPhaseAfterSettle,
} from './chartSwitchPhase';

describe('chartSwitchPhase', () => {
  it('blocks paint only while switching', () => {
    expect(canPaintCharts('idle')).toBe(true);
    expect(canPaintCharts('switching')).toBe(false);
    expect(canPaintCharts('settling')).toBe(true);
  });

  it('transitions begin → settle → end', () => {
    expect(nextPhaseAfterBegin('idle')).toBe('switching');
    expect(nextPhaseAfterSettle('switching')).toBe('settling');
    expect(nextPhaseAfterEnd('settling')).toBe('idle');
  });
});
