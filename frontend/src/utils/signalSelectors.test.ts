import { describe, it, expect } from 'vitest';
import {
  resolveMaEnvelope,
  resolveAtpSpeedLimit,
  resolveLatestDeviation,
} from './signalSelectors';
import type { MaProfileEntry, SpeedLimitEntry, TimetableDeviationEntry } from '../types/simulation';

describe('resolveMaEnvelope', () => {
  it('uses backend ma_end_chainage when provided', () => {
    const ma: MaProfileEntry = {
      train_id: 'T1', ma_end_chainage: 1500, safety_distance: 300,
    };
    const result = resolveMaEnvelope(800, 3200, ma, 300);
    expect(result.envelopeEnd).toBe(1500);
    expect(result.safetyDistance).toBe(300);
  });

  it('falls back to position + fixed length', () => {
    const result = resolveMaEnvelope(800, 3200, undefined, 300);
    expect(result.envelopeEnd).toBe(1100);
  });

  it('clamps envelope end to total length', () => {
    const result = resolveMaEnvelope(3000, 3200, undefined, 300);
    expect(result.envelopeEnd).toBe(3200);
  });
});

describe('resolveAtpSpeedLimit', () => {
  it('returns atp_limit for matching train', () => {
    const limits: SpeedLimitEntry[] = [
      { train_id: 'T1', permanent_limit: 80, atp_limit: 76 },
    ];
    expect(resolveAtpSpeedLimit(limits, 'T1', 80)).toBe(76);
  });

  it('returns fallback when no match', () => {
    expect(resolveAtpSpeedLimit([], 'T1', 80)).toBe(80);
  });
});

describe('resolveLatestDeviation', () => {
  it('returns last deviation entry for train', () => {
    const devs: TimetableDeviationEntry[] = [
      { train_id: 'T1', station_id: 'ST_A', delay_arrival: 1, nominal_dwell: 30, adjusted_dwell: 31 },
      { train_id: 'T1', station_id: 'ST_B', delay_arrival: 3, nominal_dwell: 30, adjusted_dwell: 33 },
    ];
    expect(resolveLatestDeviation(devs, 'T1')?.station_id).toBe('ST_B');
  });

  it('returns null when empty', () => {
    expect(resolveLatestDeviation([], 'T1')).toBeNull();
  });
});
