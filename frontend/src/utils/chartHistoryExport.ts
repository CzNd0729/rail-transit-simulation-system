import type { ChartHistory } from '../types/simulation';

function fmt(n: number | ''): string {
  return n === '' ? '' : n.toFixed(2);
}

export function chartHistoryToCsv(history: ChartHistory): string {
  const header = 'time,position,speed,acceleration,jerk\n';
  const rows = history.speedTime.map(([t, speed], i) => {
    const pos = history.speedPosition[i]?.[0] ?? '';
    const accel = history.accelTime[i]?.[1] ?? '';
    const jerk = history.jerkTime[i]?.[1] ?? '';
    return `${fmt(t)},${fmt(pos)},${fmt(speed)},${fmt(accel)},${fmt(jerk)}`;
  });
  return header + rows.join('\n');
}
