import type { ChartHistory } from '../types/simulation';

export function chartHistoryToCsv(history: ChartHistory): string {
  const header = 'time,position,speed,acceleration,jerk\n';
  const rows = history.speedTime.map(([t, speed], i) => {
    const pos = history.speedPosition[i]?.[0] ?? '';
    const accel = history.accelTime[i]?.[1] ?? '';
    const jerk = history.jerkTime[i]?.[1] ?? '';
    return `${t},${pos},${speed},${accel},${jerk}`;
  });
  return header + rows.join('\n');
}
