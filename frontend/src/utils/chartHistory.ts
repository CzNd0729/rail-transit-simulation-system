import type { ChartHistory, SimulationSnapshot, TrainChartHistory } from '../types/simulation';

export const EMPTY_TRAIN_CHART_HISTORY: TrainChartHistory = {
  speedTime: [],
  accelTime: [],
  jerkTime: [],
  speedPosition: [],
  positionTime: [],
};

export const EMPTY_CHART_HISTORY: ChartHistory = {
  byTrain: {},
};

const MAX_POINTS = 10_000;

function trimHistory(history: TrainChartHistory): TrainChartHistory {
  if (history.speedTime.length <= MAX_POINTS) {
    return history;
  }
  return {
    speedTime: history.speedTime.slice(-MAX_POINTS),
    accelTime: history.accelTime.slice(-MAX_POINTS),
    jerkTime: history.jerkTime.slice(-MAX_POINTS),
    speedPosition: history.speedPosition.slice(-MAX_POINTS),
    positionTime: history.positionTime.slice(-MAX_POINTS),
  };
}

export function getTrainChartHistory(
  history: ChartHistory,
  trainId: string,
): TrainChartHistory {
  return history.byTrain[trainId] ?? EMPTY_TRAIN_CHART_HISTORY;
}

export function appendChartHistory(
  history: ChartHistory,
  snapshot: SimulationSnapshot,
): ChartHistory {
  if (snapshot.trains.length === 0) {
    return history;
  }

  const byTrain = { ...history.byTrain };
  const t = snapshot.clock.elapsed;

  for (const train of snapshot.trains) {
    const prev = byTrain[train.id] ?? EMPTY_TRAIN_CHART_HISTORY;
    byTrain[train.id] = trimHistory({
      speedTime: [...prev.speedTime, [t, train.speed]],
      accelTime: [...prev.accelTime, [t, train.acceleration]],
      jerkTime: [...prev.jerkTime, [t, train.jerk]],
      speedPosition: [...prev.speedPosition, [train.position, train.speed]],
      positionTime: [...prev.positionTime, [t, train.position]],
    });
  }

  return { byTrain };
}

export function clearChartHistory(): ChartHistory {
  return { ...EMPTY_CHART_HISTORY };
}
