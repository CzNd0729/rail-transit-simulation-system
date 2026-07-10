import type { ChartHistory, SimulationSnapshot } from '../types/simulation';

export const EMPTY_CHART_HISTORY: ChartHistory = {
  speedTime: [],
  accelTime: [],
  jerkTime: [],
  speedPosition: [],
  positionTime: [],
};

const MAX_POINTS = 10_000;

export function appendChartHistory(
  history: ChartHistory,
  snapshot: SimulationSnapshot,
): ChartHistory {
  const train = snapshot.trains[0];
  if (!train) return history;

  const t = snapshot.clock.elapsed;
  const next: ChartHistory = {
    speedTime: [...history.speedTime, [t, train.speed]],
    accelTime: [...history.accelTime, [t, train.acceleration]],
    jerkTime: [...history.jerkTime, [t, train.jerk]],
    speedPosition: [...history.speedPosition, [train.position, train.speed]],
    positionTime: [...history.positionTime, [t, train.position]],
  };

  if (next.speedTime.length > MAX_POINTS) {
    return {
      speedTime: next.speedTime.slice(-MAX_POINTS),
      accelTime: next.accelTime.slice(-MAX_POINTS),
      jerkTime: next.jerkTime.slice(-MAX_POINTS),
      speedPosition: next.speedPosition.slice(-MAX_POINTS),
      positionTime: next.positionTime.slice(-MAX_POINTS),
    };
  }
  return next;
}

export function clearChartHistory(): ChartHistory {
  return { ...EMPTY_CHART_HISTORY };
}
