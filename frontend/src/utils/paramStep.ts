import type { TractionCurvePoint, VehicleParams } from '../types/simulation';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';

/** 支持步进调节的车辆数值参数字段 */
export const VEHICLE_PARAM_STEP_KEYS = [
  'empty_mass',
  'passenger_capacity',
  'max_speed',
  'max_traction_force',
  'max_brake_force',
  'davis_A',
  'davis_B',
  'davis_C_front_area',
  'davis_C_drag_coeff',
  'curve_resist_coeff',
  'tunnel_resist_factor',
] as const;

export type VehicleParamStepKey = (typeof VEHICLE_PARAM_STEP_KEYS)[number];
export type VehicleParamBaselines = Partial<Record<VehicleParamStepKey, number>>;

/** 线路参数步进字段 */
export const TRACK_PARAM_STEP_KEYS = [
  'gradient',
  'curvature',
  'speed_limit',
] as const;

export type TrackParamStepKey = (typeof TRACK_PARAM_STEP_KEYS)[number];
export type TrackParamBaselines = Partial<Record<TrackParamStepKey, number>>;

/** 信号参数步进字段 */
export const SIGNAL_PARAM_STEP_KEYS = [
  'dwell_time',
  'departure_interval',
  'target_speed_ratio',
  'safety_distance',
  'comfort_decel',
  'max_jerk',
] as const;

export type SignalParamStepKey = (typeof SIGNAL_PARAM_STEP_KEYS)[number];
export type SignalParamBaselines = Partial<Record<SignalParamStepKey, number>>;

export const DEFAULT_TRACK_PARAMS = {
  gradient: 30,
  curvature: 1200,
  speed_limit: 80,
} as const;

export const DEFAULT_SIGNAL_PARAMS = {
  dwell_time: 30,
  departure_interval: 120,
  target_speed_ratio: 0.8,
  safety_distance: 300,
  comfort_decel: 0.8,
  max_jerk: 0.75,
} as const;

/** 供电参数步进字段 */
export const POWER_PARAM_STEP_KEYS = [
  'pantograph_voltage',
  'substation_capacity',
] as const;

export type PowerParamStepKey = (typeof POWER_PARAM_STEP_KEYS)[number];
export type PowerParamBaselines = Partial<Record<PowerParamStepKey, number>>;

export const DEFAULT_POWER_PARAMS = {
  pantograph_voltage: 1500,
  substation_capacity: 5000,
} as const;

/** 从对象提取指定数值字段作为步进基准 */
export function extractParamBaselines<K extends string>(
  keys: readonly K[],
  source: Partial<Record<K, number>>,
): Partial<Record<K, number>> {
  const result: Partial<Record<K, number>> = {};
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'number' && !Number.isNaN(value)) {
      result[key] = value;
    }
  }
  return result;
}

export function extractVehicleParamBaselines(
  vehicle: Partial<VehicleParams>,
): VehicleParamBaselines {
  return extractParamBaselines(VEHICLE_PARAM_STEP_KEYS, vehicle as Partial<Record<VehicleParamStepKey, number>>);
}

export function extractTrackParamBaselines(
  track: Partial<Record<TrackParamStepKey, number>>,
): TrackParamBaselines {
  return extractParamBaselines(TRACK_PARAM_STEP_KEYS, track);
}

export function extractSignalParamBaselines(
  signal: Partial<Record<SignalParamStepKey, number>>,
): SignalParamBaselines {
  return extractParamBaselines(SIGNAL_PARAM_STEP_KEYS, signal);
}

export function extractPowerParamBaselines(
  power: Partial<Record<PowerParamStepKey, number>>,
): PowerParamBaselines {
  return extractParamBaselines(POWER_PARAM_STEP_KEYS, power);
}

/** 牵引特性曲线各折点的步进基准（按索引锁定） */
export interface TractionCurvePointBaseline {
  speed: number;
  force_percent: number;
}

export function extractTractionCurveBaselines(
  curve: TractionCurvePoint[] | undefined,
  fallback: TractionCurvePoint[] = DEFAULT_VEHICLE_PARAMS.traction_curve,
): TractionCurvePointBaseline[] {
  const points = curve?.length ? curve : fallback;
  return points.map((pt) => ({
    speed: pt.speed,
    force_percent: pt.force_percent,
  }));
}

/**
 * 根据基准值计算固定步进量：基准值的 10%，此后不再变化。
 */
export function computeFixedParamStep(baseline: number): number {
  if (baseline === 0) return 1;
  const step = Math.abs(baseline) * 0.1;
  if (step >= 1) return Math.round(step);
  if (step >= 0.0001) return Number(step.toPrecision(3));
  return step;
}

/** 统计小数位数（用于消除浮点误差） */
function decimalPlaces(n: number): number {
  if (!Number.isFinite(n)) return 0;
  const str = n.toString();
  if (str.includes('e-')) {
    const match = /e-(\d+)/.exec(str);
    return match ? Number(match[1]) : 0;
  }
  const dot = str.indexOf('.');
  return dot === -1 ? 0 : str.length - dot - 1;
}

/**
 * 按固定步进量增减，并按步进精度四舍五入，避免 0.01-0.001=0.009999... 问题。
 */
export function applyParamStep(
  current: number,
  step: number,
  direction: 1 | -1,
  min = 0,
): number {
  const next = current + direction * step;
  const precision = Math.max(decimalPlaces(step), decimalPlaces(current));
  const rounded = precision > 0
    ? Number(next.toFixed(precision))
    : Math.round(next);
  return Math.max(min, rounded);
}
