import { describe, it, expect } from 'vitest';
import {
  CHART_HISTORY_MAX_POINTS,
  appendChartHistory,
  clearChartHistory,
  getTrainChartHistory,
} from './chartHistory';
import type { SimulationSnapshot } from '../types/simulation';
import { EMPTY_SIGNAL_STATE } from '../types/simulation';

const makeTrain = (
  id: string,
  _elapsed: number,
  speed: number,
  accel: number,
  pos: number,
  jerk = 0,
) => ({
  id,
  position: pos,
  speed,
  acceleration: accel,
  jerk,
  mode: 'traction' as const,
  mass: 200000,
  passenger_count: 900,
  door_status: 'closed' as const,
  pantograph_voltage: 1500,
  power_demand: 100,
  distance_to_station: 0,
  target_station_id: '',
  direction: 'up' as const,
  fault_alarm: null,
  traction_force: 0,
  brake_force: 0,
  total_resistance: 0,
  davis_resistance: 0,
  gradient_resistance: 0,
  curve_resistance: 0,
  tunnel_resistance: 0,
});

const makeSnapshot = (
  t: number,
  speed: number,
  accel: number,
  pos: number,
  jerk = 0,
  trainId = 'TRAIN_01',
): SimulationSnapshot => ({
  clock: { elapsed: t, speed_multiplier: 1 },
  trains: [makeTrain(trainId, t, speed, accel, pos, jerk)],
  power: {
    substations: [],
    voltage_profile: [],
    total_consumption: 1.2,
    total_regeneration: 0.3,
    regeneration_rate: 0,
  },
  signaling: { ...EMPTY_SIGNAL_STATE },
  track: { occupancy: [], switch_states: [] },
  events: [],
});

describe('appendChartHistory', () => {
  it('appends one point per snapshot (mutable push)', () => {
    const history = { byTrain: {} };
    const wrote = appendChartHistory(history, makeSnapshot(1.0, 50, 0.8, 100));
    expect(wrote).toBe(true);
    const h = getTrainChartHistory(history, 'TRAIN_01');
    expect(h.speedTime).toEqual([[1.0, 50]]);
    expect(h.accelTime).toEqual([[1.0, 0.8]]);
    expect(h.jerkTime).toEqual([[1.0, 0]]);
    expect(h.speedPosition).toEqual([[100, 50]]);
    expect(h.positionTime).toEqual([[1.0, 100]]);
    expect(h.resistanceTime).toEqual([[1.0, 0]]);
    expect(h.tractionEnergyTime).toEqual([[1.0, 1.2]]);
    expect(h.regenEnergyTime).toEqual([[1.0, 0.3]]);
  });

  it('returns false when snapshot has no trains', () => {
    const history = { byTrain: {} };
    const snap: SimulationSnapshot = {
      ...makeSnapshot(1.0, 50, 0.8, 100),
      trains: [],
    };
    const wrote = appendChartHistory(history, snap);
    expect(wrote).toBe(false);
  });

  it('records jerk from train state', () => {
    const history = { byTrain: {} };
    appendChartHistory(history, makeSnapshot(2.0, 60, 0.5, 200, 0.12));
    expect(getTrainChartHistory(history, 'TRAIN_01').jerkTime).toEqual([[2.0, 0.12]]);
  });

  it('accumulates multiple snapshots (mutable append)', () => {
    const history = { byTrain: {} };
    appendChartHistory(history, makeSnapshot(1.0, 50, 0.8, 100));
    appendChartHistory(history, makeSnapshot(2.0, 60, 0.5, 200));
    const trainHistory = getTrainChartHistory(history, 'TRAIN_01');
    expect(trainHistory.speedTime).toHaveLength(2);
    expect(trainHistory.speedTime[1]).toEqual([2.0, 60]);
  });

  it('stores history per train id', () => {
    const history = { byTrain: {} };
    const snap: SimulationSnapshot = {
      ...makeSnapshot(1.0, 50, 0.8, 100),
      trains: [
        makeTrain('TRAIN_01', 1.0, 50, 0.8, 100),
        makeTrain('TRAIN_02', 1.0, 40, 0.5, 80),
      ],
    };
    appendChartHistory(history, snap);
    expect(getTrainChartHistory(history, 'TRAIN_01').speedTime).toEqual([[1.0, 50]]);
    expect(getTrainChartHistory(history, 'TRAIN_02').speedTime).toEqual([[1.0, 40]]);
  });

  it('truncates when exceeding CHART_HISTORY_MAX_POINTS', () => {
    const history = { byTrain: {} };
    // Push more than the cap
    for (let i = 0; i < CHART_HISTORY_MAX_POINTS + 5; i++) {
      appendChartHistory(history, makeSnapshot(i * 0.1, 50, 0, i));
    }
    const h = getTrainChartHistory(history, 'TRAIN_01');
    expect(h.speedTime.length).toBeLessThanOrEqual(CHART_HISTORY_MAX_POINTS);
  });
});

describe('clearChartHistory', () => {
  it('clears all arrays in place', () => {
    const history = { byTrain: {} };
    appendChartHistory(history, makeSnapshot(1.0, 50, 0.8, 100));
    expect(getTrainChartHistory(history, 'TRAIN_01').speedTime).toHaveLength(1);
    clearChartHistory(history);
    expect(getTrainChartHistory(history, 'TRAIN_01').speedTime).toEqual([]);
  });
});
