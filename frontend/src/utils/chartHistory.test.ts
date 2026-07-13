import { describe, it, expect } from 'vitest';
import {
  EMPTY_CHART_HISTORY,
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
  it('appends one point per snapshot', () => {
    const result = appendChartHistory(EMPTY_CHART_HISTORY, makeSnapshot(1.0, 50, 0.8, 100));
    const h = getTrainChartHistory(result, 'TRAIN_01');
    expect(h.speedTime).toEqual([[1.0, 50]]);
    expect(h.accelTime).toEqual([[1.0, 0.8]]);
    expect(h.jerkTime).toEqual([[1.0, 0]]);
    expect(h.speedPosition).toEqual([[100, 50]]);
    expect(h.positionTime).toEqual([[1.0, 100]]);
    expect(h.resistanceTime).toEqual([[1.0, 0]]);
    expect(h.tractionEnergyTime).toEqual([[1.0, 1.2]]);
    expect(h.regenEnergyTime).toEqual([[1.0, 0.3]]);
  });

  it('truncates positionTime when exceeding MAX_POINTS', () => {
    let h = EMPTY_CHART_HISTORY;
    for (let i = 0; i < 10_001; i++) {
      h = appendChartHistory(h, makeSnapshot(i * 0.1, 50, 0, i));
    }
    expect(getTrainChartHistory(h, 'TRAIN_01').positionTime).toHaveLength(10_000);
    expect(getTrainChartHistory(h, 'TRAIN_01').positionTime[0]).toEqual([0.1, 1]);
  });

  it('records jerk from train state', () => {
    const result = appendChartHistory(EMPTY_CHART_HISTORY, makeSnapshot(2.0, 60, 0.5, 200, 0.12));
    expect(getTrainChartHistory(result, 'TRAIN_01').jerkTime).toEqual([[2.0, 0.12]]);
  });

  it('accumulates multiple snapshots', () => {
    let h = EMPTY_CHART_HISTORY;
    h = appendChartHistory(h, makeSnapshot(1.0, 50, 0.8, 100));
    h = appendChartHistory(h, makeSnapshot(2.0, 60, 0.5, 200));
    const trainHistory = getTrainChartHistory(h, 'TRAIN_01');
    expect(trainHistory.speedTime).toHaveLength(2);
    expect(trainHistory.speedTime[1]).toEqual([2.0, 60]);
  });

  it('stores history per train id', () => {
    const snap: SimulationSnapshot = {
      ...makeSnapshot(1.0, 50, 0.8, 100),
      trains: [
        makeTrain('TRAIN_01', 1.0, 50, 0.8, 100),
        makeTrain('TRAIN_02', 1.0, 40, 0.5, 80),
      ],
    };
    const result = appendChartHistory(EMPTY_CHART_HISTORY, snap);
    expect(getTrainChartHistory(result, 'TRAIN_01').speedTime).toEqual([[1.0, 50]]);
    expect(getTrainChartHistory(result, 'TRAIN_02').speedTime).toEqual([[1.0, 40]]);
  });
});

describe('clearChartHistory', () => {
  it('returns empty arrays', () => {
    expect(clearChartHistory()).toEqual(EMPTY_CHART_HISTORY);
  });
});
