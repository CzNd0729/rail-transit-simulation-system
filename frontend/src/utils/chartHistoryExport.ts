import type { ChartHistory, TrainChartHistory } from '../types/simulation';
import { getTrainChartHistory } from './chartHistory';

function fmt(n: number | ''): string {
  return n === '' ? '' : n.toFixed(2);
}

const BASE_HEADER = [
  'time',
  'position',
  'speed',
  'acceleration',
  'jerk',
  'total_resistance_kn',
  'davis_kn',
  'gradient_kn',
  'curve_kn',
  'tunnel_kn',
  'traction_energy_kwh',
  'regen_energy_kwh',
].join(',');

export function chartHistoryToCsv(
  history: ChartHistory,
  trainId?: string,
): string {
  const ids = trainId
    ? [trainId]
    : Object.keys(history.byTrain);

  const rows: string[] = [];
  for (const id of ids) {
    const h = getTrainChartHistory(history, id);
    rows.push(...rowsForTrain(id, h));
  }

  if (ids.length > 1) {
    return `train_id,${BASE_HEADER}\n` + rows.join('\n');
  }
  return `${BASE_HEADER}\n` + rows.map((r) => r.split(',').slice(1).join(',')).join('\n');
}

function rowsForTrain(trainId: string, h: TrainChartHistory): string[] {
  const out: string[] = [];
  for (const [i, [t, speed]] of h.speedTime.entries()) {
    const pos = h.speedPosition[i]?.[0] ?? '';
    const accel = h.accelTime[i]?.[1] ?? '';
    const jerk = h.jerkTime[i]?.[1] ?? '';
    const totalKn = h.resistanceTime[i]?.[1] ?? '';
    const davis = h.davisResistanceTime[i]?.[1] ?? '';
    const gradient = h.gradientResistanceTime[i]?.[1] ?? '';
    const curve = h.curveResistanceTime[i]?.[1] ?? '';
    const tunnel = h.tunnelResistanceTime[i]?.[1] ?? '';
    const traction = h.tractionEnergyTime[i]?.[1] ?? '';
    const regen = h.regenEnergyTime[i]?.[1] ?? '';
    out.push([
      trainId,
      fmt(t),
      fmt(pos),
      fmt(speed),
      fmt(accel),
      fmt(jerk),
      fmt(totalKn),
      fmt(davis),
      fmt(gradient),
      fmt(curve),
      fmt(tunnel),
      fmt(traction),
      fmt(regen),
    ].join(','));
  }
  return out;
}

export function getAllTrainHistories(history: ChartHistory): Array<[string, TrainChartHistory]> {
  return Object.entries(history.byTrain);
}
