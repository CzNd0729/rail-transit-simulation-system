import type { ChartHistory, SimulationSnapshot, TrainChartHistory } from '../types/simulation';

export const EMPTY_TRAIN_CHART_HISTORY: TrainChartHistory = {
  speedTime: [],
  accelTime: [],
  jerkTime: [],
  speedPosition: [],
  positionTime: [],
  voltagePosition: [],
  resistanceTime: [],
  tractionEnergyTime: [],
  regenEnergyTime: [],
};

export const EMPTY_CHART_HISTORY: ChartHistory = {
  byTrain: {},
};

/** 每列车每序列最大缓存点数（0.1s 步长约 5000s 全程） */
export const CHART_HISTORY_MAX_POINTS = 50_000;

function trimHistory(history: TrainChartHistory): TrainChartHistory {
  const MAX_POINTS = CHART_HISTORY_MAX_POINTS;
  if (history.speedTime.length <= MAX_POINTS) {
    return history;
  }
  // 仅裁剪时间维度的数组；位置维度（speedPosition/voltagePosition）受线路长度自然约束
  return {
    speedTime: history.speedTime.slice(-MAX_POINTS),
    accelTime: history.accelTime.slice(-MAX_POINTS),
    jerkTime: history.jerkTime.slice(-MAX_POINTS),
    speedPosition: history.speedPosition,
    positionTime: history.positionTime.slice(-MAX_POINTS),
    voltagePosition: history.voltagePosition,
    resistanceTime: history.resistanceTime.slice(-MAX_POINTS),
    tractionEnergyTime: history.tractionEnergyTime.slice(-MAX_POINTS),
    regenEnergyTime: history.regenEnergyTime.slice(-MAX_POINTS),
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
  const tractionKwh = snapshot.power.total_consumption;
  const regenKwh = snapshot.power.total_regeneration;

  for (const train of snapshot.trains) {
    const prev = byTrain[train.id] ?? EMPTY_TRAIN_CHART_HISTORY;
    byTrain[train.id] = trimHistory({
      speedTime: [...prev.speedTime, [t, train.speed]],
      accelTime: [...prev.accelTime, [t, train.acceleration]],
      jerkTime: [...prev.jerkTime, [t, train.jerk]],
      speedPosition: [...prev.speedPosition, [train.position, train.speed]],
      positionTime: [...prev.positionTime, [t, train.position]],
      voltagePosition: [...prev.voltagePosition, [train.position, train.pantograph_voltage]],
      resistanceTime: [...prev.resistanceTime, [t, train.total_resistance / 1000]],
      tractionEnergyTime: [...prev.tractionEnergyTime, [t, tractionKwh]],
      regenEnergyTime: [...prev.regenEnergyTime, [t, regenKwh]],
    });
  }

  return { byTrain };
}

export function clearChartHistory(): ChartHistory {
  return { ...EMPTY_CHART_HISTORY };
}

/** @internal 供单元测试验证截断逻辑 */
export function trimChartHistoryForTest(history: TrainChartHistory): TrainChartHistory {
  return trimHistory(history);
}
