import type { ChartHistory, TrainChartHistory } from '../types/simulation';
import { getTrainChartHistory } from './chartHistory';

function fmt(n: number | ''): string {
  return n === '' ? '' : n.toFixed(2);
}

export function chartHistoryToCsv(
  history: ChartHistory,
  trainId?: string,
): string {
  const header = 'time,position,speed,acceleration,jerk\n';
  const ids = trainId
    ? [trainId]
    : Object.keys(history.byTrain);

  const rows: string[] = [];
  for (const id of ids) {
    const trainHistory = getTrainChartHistory(history, id);
    for (const [i, [t, speed]] of trainHistory.speedTime.entries()) {
      const pos = trainHistory.speedPosition[i]?.[0] ?? '';
      const accel = trainHistory.accelTime[i]?.[1] ?? '';
      const jerk = trainHistory.jerkTime[i]?.[1] ?? '';
      rows.push(`${id},${fmt(t)},${fmt(pos)},${fmt(speed)},${fmt(accel)},${fmt(jerk)}`);
    }
  }

  if (ids.length > 1) {
    return 'train_id,time,position,speed,acceleration,jerk\n' + rows.join('\n');
  }
  return header + rows.map((r) => r.split(',').slice(1).join(',')).join('\n');
}

export function getAllTrainHistories(history: ChartHistory): Array<[string, TrainChartHistory]> {
  return Object.entries(history.byTrain);
}
