import { describe, it, expect } from 'vitest';
import { chartHistoryToCsv } from './chartHistoryExport';
import type { ChartHistory } from '../types/simulation';

const sampleHistory: ChartHistory = {
  byTrain: {
    TRAIN_01: {
      speedTime: [[1, 10], [2, 20]],
      speedPosition: [[100, 10], [200, 20]],
      accelTime: [[1, 0.5], [2, 0.3]],
      jerkTime: [[1, 0.8], [2, -0.2]],
      positionTime: [[1, 100], [2, 200]],
      voltagePosition: [],
      resistanceTime: [[1, 12.5], [2, 13.1]],
      davisResistanceTime: [[1, 7.5], [2, 7.8]],
      gradientResistanceTime: [[1, 3], [2, 3.2]],
      curveResistanceTime: [[1, 1.2], [2, 1.3]],
      tunnelResistanceTime: [[1, 0.8], [2, 0.8]],
      tractionEnergyTime: [[1, 0.5], [2, 1.2]],
      regenEnergyTime: [[1, 0.1], [2, 0.2]],
    },
  },
};

describe('chartHistoryToCsv', () => {
  it('exports extended resistance and energy columns', () => {
    const csv = chartHistoryToCsv(sampleHistory, 'TRAIN_01');
    expect(csv).toContain('total_resistance_kn');
    expect(csv).toContain('davis_kn');
    expect(csv).toContain('traction_energy_kwh');
    expect(csv).toContain('1.00,100.00,10.00,0.50,0.80,12.50,7.50,3.00,1.20,0.80,0.50,0.10');
  });
});
