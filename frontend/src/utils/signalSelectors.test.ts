import { describe, it, expect } from 'vitest';
import {
  resolveMaEnvelope,
  resolveAtpSpeedLimit,
  resolvePermanentSpeedLimit,
  resolveLatestDeviation,
  resolveTrainInterval,
} from './signalSelectors';
import type { MaProfileEntry, SpeedLimitEntry, TimetableDeviationEntry, TrainTrackingInterval } from '../types/simulation';

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

describe('resolvePermanentSpeedLimit', () => {
  it('returns backend permanent_limit when present', () => {
    const limits: SpeedLimitEntry[] = [
      { train_id: 'TRAIN_01', permanent_limit: 72, atp_limit: 68 },
    ];
    expect(resolvePermanentSpeedLimit(limits, 'TRAIN_01', 80)).toBe(72);
  });

  it('falls back when train not found', () => {
    expect(resolvePermanentSpeedLimit([], 'TRAIN_01', 80)).toBe(80);
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

describe('resolveTrainInterval', () => {
  it('returns interval for matching train', () => {
    const intervals: TrainTrackingInterval[] = [
      {
        train_id: 'TRAIN_02',
        leading_train_id: 'TRAIN_01',
        interval_m: 480,
        min_interval_m: 500,
        safe: false,
      },
    ];
    expect(resolveTrainInterval(intervals, 'TRAIN_02')?.safe).toBe(false);
  });

  it('returns null when no match', () => {
    expect(resolveTrainInterval([], 'TRAIN_01')).toBeNull();
  });
});
