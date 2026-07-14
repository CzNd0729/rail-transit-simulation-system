import type { ChartHistory, TrainState } from '../types/simulation';

/**
 * 解析车辆/信号曲线应对应的列车 ID。
 *
 * - 显式选中：绑定该车历史（离线后仍可回看）
 * - 全部列车：优先「发车最早」的历史曲线，避免轴从 0 起而线从中途起
 */
export function resolveChartTrainId(
  chartHistory: ChartHistory,
  trains: TrainState[],
  selectedTrainId: string | null,
): string {
  if (selectedTrainId) {
    const selectedHist = chartHistory.byTrain[selectedTrainId];
    if (selectedHist && selectedHist.speedTime.length > 0) {
      return selectedTrainId;
    }
    if (trains.some((t) => t.id === selectedTrainId)) {
      return selectedTrainId;
    }
  }

  let bestAnyId: string | undefined;
  let bestAnyStart = Infinity;

  for (const [id, hist] of Object.entries(chartHistory.byTrain)) {
    const start = hist.speedTime[0]?.[0];
    if (start == null) continue;
    if (start < bestAnyStart) {
      bestAnyStart = start;
      bestAnyId = id;
    }
  }

  if (bestAnyId) {
    return bestAnyId;
  }
  return trains[0]?.id ?? 'TRAIN_01';
}

/** 曲线车是否仍在线：决定时间轴 max 是否跟随全局 clock */
export function isChartTrainLive(
  trains: TrainState[],
  chartTrainId: string,
): boolean {
  return trains.some((t) => t.id === chartTrainId);
}
