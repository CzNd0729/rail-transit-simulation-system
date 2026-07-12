import { describe, it, expect } from 'vitest';
import {
  applyParamStep,
  computeFixedParamStep,
  extractVehicleParamBaselines,
  extractTrackParamBaselines,
  extractSignalParamBaselines,
  extractPowerParamBaselines,
  extractTractionCurveBaselines,
  DEFAULT_TRACK_PARAMS,
  DEFAULT_SIGNAL_PARAMS,
  DEFAULT_POWER_PARAMS,
} from './paramStep';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';

describe('computeFixedParamStep', () => {
  it('returns 10% of baseline for large values', () => {
    expect(computeFixedParamStep(200_000)).toBe(20_000);
    expect(computeFixedParamStep(400_000)).toBe(40_000);
  });

  it('returns 10% for medium values', () => {
    expect(computeFixedParamStep(1500)).toBe(150);
    expect(computeFixedParamStep(80)).toBe(8);
    expect(computeFixedParamStep(30)).toBe(3);
  });

  it('handles small coefficients', () => {
    expect(computeFixedParamStep(0.01)).toBe(0.001);
    expect(computeFixedParamStep(0.8)).toBe(0.08);
  });

  it('falls back when baseline is zero', () => {
    expect(computeFixedParamStep(0)).toBe(1);
  });
});

describe('applyParamStep', () => {
  it('avoids float noise for Davis A step', () => {
    const step = computeFixedParamStep(0.01);
    expect(step).toBe(0.001);
    expect(applyParamStep(0.01, step, 1)).toBe(0.011);
    expect(applyParamStep(0.011, step, -1)).toBe(0.01);
    expect(applyParamStep(0.01, step, -1)).toBe(0.009);
  });

  it('increments and decrements large integers cleanly', () => {
    const step = 20_000;
    expect(applyParamStep(200_000, step, 1)).toBe(220_000);
    expect(applyParamStep(220_000, step, -1)).toBe(200_000);
  });

  it('respects minimum bound', () => {
    expect(applyParamStep(0.001, 0.001, -1, 0)).toBe(0);
  });
});

describe('extractParamBaselines', () => {
  it('extracts vehicle numeric fields', () => {
    const baselines = extractVehicleParamBaselines(DEFAULT_VEHICLE_PARAMS);
    expect(baselines.empty_mass).toBe(200_000);
  });

  it('extracts track numeric fields', () => {
    const baselines = extractTrackParamBaselines(DEFAULT_TRACK_PARAMS);
    expect(baselines.gradient).toBe(30);
    expect(baselines.speed_limit).toBe(80);
  });

  it('extracts signal numeric fields', () => {
    const baselines = extractSignalParamBaselines(DEFAULT_SIGNAL_PARAMS);
    expect(baselines.dwell_time).toBe(30);
    expect(baselines.target_speed_ratio).toBe(0.8);
  });

  it('extracts power numeric fields', () => {
    const baselines = extractPowerParamBaselines(DEFAULT_POWER_PARAMS);
    expect(baselines.pantograph_voltage).toBe(1500);
    expect(baselines.substation_capacity).toBe(5000);
  });

  it('computes 10% fixed steps for power params', () => {
    const baselines = extractPowerParamBaselines(DEFAULT_POWER_PARAMS);
    expect(computeFixedParamStep(baselines.pantograph_voltage!)).toBe(150);
    expect(computeFixedParamStep(baselines.substation_capacity!)).toBe(500);
  });
});

describe('extractTractionCurveBaselines', () => {
  it('locks per-point speed and force_percent baselines', () => {
    const baselines = extractTractionCurveBaselines(DEFAULT_VEHICLE_PARAMS.traction_curve);
    expect(baselines).toHaveLength(3);
    expect(baselines[0]).toEqual({ speed: 0, force_percent: 1 });
    expect(baselines[1]).toEqual({ speed: 40, force_percent: 1 });
    expect(baselines[2]).toEqual({ speed: 80, force_percent: 0.5 });
  });

  it('computes fixed steps for curve points on percent scale', () => {
    const baselines = extractTractionCurveBaselines(DEFAULT_VEHICLE_PARAMS.traction_curve);
    expect(computeFixedParamStep(baselines[1]!.speed)).toBe(4);
    expect(computeFixedParamStep(baselines[1]!.force_percent * 100)).toBe(10);
    expect(computeFixedParamStep(baselines[2]!.force_percent * 100)).toBe(5);
  });
});
