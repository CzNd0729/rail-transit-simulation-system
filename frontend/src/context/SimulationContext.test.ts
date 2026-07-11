import { describe, it, expect } from 'vitest';
import { simulationReducer, initialState } from './SimulationContext';

describe('simulationReducer lifecycle', () => {
  it('CLEAR_CHART_HISTORY does not reset stats', () => {
    const withStats = {
      ...initialState,
      stats: {
        ...initialState.stats,
        trip_time: 120,
        avg_speed: 45,
        max_speed: 64,
        stop_count: 2,
      },
      chartHistory: {
        speedTime: [[1, 50], [2, 60]] as [number, number][],
        accelTime: [[1, 0.5]] as [number, number][],
        jerkTime: [] as [number, number][],
        speedPosition: [[100, 50]] as [number, number][],
        positionTime: [] as [number, number][],
      },
    };
    const next = simulationReducer(withStats, { type: 'CLEAR_CHART_HISTORY' });
    expect(next.stats.trip_time).toBe(120);
    expect(next.chartHistory.speedTime).toEqual([]);
  });

  it('RESET_RUN_DATA clears both chart and stats', () => {
    const withData = {
      ...initialState,
      stats: {
        ...initialState.stats,
        trip_time: 120,
        avg_speed: 45,
        max_speed: 64,
        stop_count: 2,
      },
      chartHistory: {
        speedTime: [[1, 50]] as [number, number][],
        accelTime: [[1, 0.5]] as [number, number][],
        jerkTime: [] as [number, number][],
        speedPosition: [[100, 50]] as [number, number][],
        positionTime: [] as [number, number][],
      },
    };
    const next = simulationReducer(withData, { type: 'RESET_RUN_DATA' });
    expect(next.stats.trip_time).toBe(0);
    expect(next.chartHistory.speedTime).toEqual([]);
  });
});
