import type { ChartHistory, SimulationSnapshot, TrainChartHistory } from '../types/simulation';

export const EMPTY_TRAIN_CHART_HISTORY: TrainChartHistory = {
  speedTime: [],
  accelTime: [],
  jerkTime: [],
  speedPosition: [],
  positionTime: [],
  voltagePosition: [],
  resistanceTime: [],
  davisResistanceTime: [],
  gradientResistanceTime: [],
  curveResistanceTime: [],
  tunnelResistanceTime: [],
  tractionEnergyTime: [],
  regenEnergyTime: [],
};

export const EMPTY_CHART_HISTORY: ChartHistory = {
  byTrain: {},
};

/** 每列车每序列最大缓存点数（0.1s 步长约 5000s 全程） */
export const CHART_HISTORY_MAX_POINTS = 50_000;

type Point = [number, number];

function createEmptyTrainHistory(): TrainChartHistory {
  return {
    speedTime: [],
    accelTime: [],
    jerkTime: [],
    speedPosition: [],
    positionTime: [],
    voltagePosition: [],
    resistanceTime: [],
    davisResistanceTime: [],
    gradientResistanceTime: [],
    curveResistanceTime: [],
    tunnelResistanceTime: [],
    tractionEnergyTime: [],
    regenEnergyTime: [],
  };
}

/** 均匀压缩，保留首尾，避免滑动窗口丢弃 t≈0 导致前半段空白 */
export function compressSeriesPoints(points: Point[], maxPoints: number): Point[] {
  const n = points.length;
  if (n <= maxPoints) return points.slice();
  if (maxPoints < 2) return [points[n - 1]];

  const result: Point[] = new Array(maxPoints);
  const last = maxPoints - 1;
  for (let i = 0; i < maxPoints; i += 1) {
    const src = i === last ? n - 1 : Math.round((i * (n - 1)) / last);
    result[i] = points[src];
  }
  return result;
}

/**
 * O(1) 追加；超过高水位后整段压缩到 ~0.8*max（保留起点）。
 * 禁止 shift 丢前缀。
 */
function pushPoint(series: Point[], point: Point, maxPoints: number): void {
  series.push(point);
  const highWater = Math.floor(maxPoints * 1.25);
  if (series.length <= highWater) return;
  const target = Math.max(2, Math.floor(maxPoints * 0.8));
  const compressed = compressSeriesPoints(series, target);
  series.length = 0;
  for (let i = 0; i < compressed.length; i += 1) {
    series.push(compressed[i]);
  }
}

/** 确保某车在 byTrain 中有记录，返回其 TrainChartHistory（原地修改） */
function ensureTrainHistory(
  byTrain: Record<string, TrainChartHistory>,
  trainId: string,
): TrainChartHistory {
  let h = byTrain[trainId];
  if (!h) {
    h = createEmptyTrainHistory();
    byTrain[trainId] = h;
  }
  return h;
}

export function getTrainChartHistory(
  history: ChartHistory,
  trainId: string,
): TrainChartHistory {
  return history.byTrain[trainId] ?? EMPTY_TRAIN_CHART_HISTORY;
}

/**
 * 向 chartHistory 追加一帧仿真快照数据。
 * 直接 push 到现有数组，零数组拷贝。
 * 返回 true 表示有数据写入（调用方应递增 chartVersion）。
 */
export function appendChartHistory(
  history: ChartHistory,
  snapshot: SimulationSnapshot,
): boolean {
  if (snapshot.trains.length === 0) return false;

  const { byTrain } = history;
  const t = snapshot.clock.elapsed;
  const tractionKwh = snapshot.power.total_consumption;
  const regenKwh = snapshot.power.total_regeneration;
  const MAX = CHART_HISTORY_MAX_POINTS;

  for (const train of snapshot.trains) {
    const h = ensureTrainHistory(byTrain, train.id);

    pushPoint(h.speedTime, [t, train.speed], MAX);
    pushPoint(h.accelTime, [t, train.acceleration], MAX);
    pushPoint(h.jerkTime, [t, train.jerk ?? 0], MAX);
    pushPoint(h.speedPosition, [train.position, train.speed], MAX);
    pushPoint(h.positionTime, [t, train.position], MAX);
    pushPoint(h.voltagePosition, [train.position, train.pantograph_voltage], MAX);
    pushPoint(h.resistanceTime, [t, train.total_resistance / 1000], MAX);
    pushPoint(h.davisResistanceTime, [t, (train.davis_resistance ?? 0) / 1000], MAX);
    pushPoint(h.gradientResistanceTime, [t, (train.gradient_resistance ?? 0) / 1000], MAX);
    pushPoint(h.curveResistanceTime, [t, (train.curve_resistance ?? 0) / 1000], MAX);
    pushPoint(h.tunnelResistanceTime, [t, (train.tunnel_resistance ?? 0) / 1000], MAX);
    pushPoint(h.tractionEnergyTime, [t, tractionKwh], MAX);
    pushPoint(h.regenEnergyTime, [t, regenKwh], MAX);
  }

  return true;
}

/** 清空所有曲线历史（零分配：直接清空数组） */
export function clearChartHistory(history: ChartHistory): void {
  for (const h of Object.values(history.byTrain)) {
    h.speedTime.length = 0;
    h.accelTime.length = 0;
    h.jerkTime.length = 0;
    h.speedPosition.length = 0;
    h.positionTime.length = 0;
    h.voltagePosition.length = 0;
    h.resistanceTime.length = 0;
    h.davisResistanceTime.length = 0;
    h.gradientResistanceTime.length = 0;
    h.curveResistanceTime.length = 0;
    h.tunnelResistanceTime.length = 0;
    h.tractionEnergyTime.length = 0;
    h.regenEnergyTime.length = 0;
  }
  history.byTrain = {};
}
