import { describe, it, expect } from 'vitest';
import { chartHistoryToCsv } from './chartHistoryExport';

describe('chartHistoryToCsv', () => {
  it('exports time, position, speed, acceleration columns', () => {
    const csv = chartHistoryToCsv({
      speedTime: [[1, 10], [2, 20]],
      speedPosition: [[100, 10], [200, 20]],
      accelTime: [[1, 0.5], [2, 0.3]],
    });
    expect(csv).toContain('time,position,speed,acceleration');
    expect(csv).toContain('1,100,10,0.5');
    expect(csv).toContain('2,200,20,0.3');
  });
});
