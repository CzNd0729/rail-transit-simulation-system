import { describe, it, expect } from 'vitest';
import { chartHistoryToCsv } from './chartHistoryExport';

describe('chartHistoryToCsv', () => {
  it('exports time, position, speed, acceleration columns', () => {
    const csv = chartHistoryToCsv({
      byTrain: {
        TRAIN_01: {
          speedTime: [[1, 10], [2, 20]],
          speedPosition: [[100, 10], [200, 20]],
          accelTime: [[1, 0.5], [2, 0.3]],
          jerkTime: [[1, 0.8], [2, -0.2]],
          positionTime: [[1, 100], [2, 200]],
          voltagePosition: [],
          resistanceTime: [],
          tractionEnergyTime: [],
          regenEnergyTime: [],
        },
      },
    });
    expect(csv).toContain('time,position,speed,acceleration,jerk');
    expect(csv).toContain('1.00,100.00,10.00,0.50,0.80');
    expect(csv).toContain('2.00,200.00,20.00,0.30,-0.20');
  });
});
