import { describe, it, expect } from 'vitest';
import { EMPTY_CHART_HISTORY, appendChartHistory, clearChartHistory } from './chartHistory';
import type { SimulationSnapshot } from '../types/simulation';

const makeSnapshot = (t: number, speed: number, accel: number, pos: number): SimulationSnapshot => ({
  clock: { elapsed: t, speed_multiplier: 1 },
  trains: [{
    id: 'TRAIN_01', position: pos, speed, acceleration: accel,
    mode: 'traction', mass: 200000, passenger_count: 900,
    door_status: 'closed', pantograph_voltage: 1500, power_demand: 100,
    fault_alarm: null,
  }],
  power: { substations: [], voltage_profile: [], total_consumption: 0, total_regeneration: 0, regeneration_rate: 0 },
  signaling: { commands: [], emergency_brake: [], train_intervals: [] },
  track: { occupancy: [], switch_states: [] },
  events: [],
});

describe('appendChartHistory', () => {
  it('appends one point per snapshot', () => {
    const result = appendChartHistory(EMPTY_CHART_HISTORY, makeSnapshot(1.0, 50, 0.8, 100));
    expect(result.speedTime).toEqual([[1.0, 50]]);
    expect(result.accelTime).toEqual([[1.0, 0.8]]);
    expect(result.speedPosition).toEqual([[100, 50]]);
  });

  it('accumulates multiple snapshots', () => {
    let h = EMPTY_CHART_HISTORY;
    h = appendChartHistory(h, makeSnapshot(1.0, 50, 0.8, 100));
    h = appendChartHistory(h, makeSnapshot(2.0, 60, 0.5, 200));
    expect(h.speedTime).toHaveLength(2);
    expect(h.speedTime[1]).toEqual([2.0, 60]);
  });
});

describe('clearChartHistory', () => {
  it('returns empty arrays', () => {
    expect(clearChartHistory()).toEqual(EMPTY_CHART_HISTORY);
  });
});
