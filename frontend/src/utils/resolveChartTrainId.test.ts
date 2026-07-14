import { describe, it, expect } from 'vitest';
import type { TrainChartHistory, TrainState } from '../types/simulation';
import { isChartTrainLive, resolveChartTrainId } from './resolveChartTrainId';

function emptyHist(speedTime: [number, number][]): TrainChartHistory {
  return {
    speedTime,
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

const train = (id: string): TrainState =>
  ({
    id,
    position: 0,
    speed: 0,
    acceleration: 0,
    jerk: 0,
    mode: 'traction',
    mass: 1,
    passenger_count: 0,
    door_status: 'closed',
    pantograph_voltage: 1500,
    power_demand: 0,
    distance_to_station: 0,
    target_station_id: '',
    direction: 'up',
    fault_alarm: null,
    traction_force: 0,
    brake_force: 0,
    total_resistance: 0,
  }) as TrainState;

describe('resolveChartTrainId', () => {
  it('prefers earliest-start history when no selection', () => {
    const full = {
      byTrain: {
        LATE: emptyHist([[150, 0]]),
        EARLY: emptyHist([[10, 0]]),
      },
    };
    expect(resolveChartTrainId(full, [train('LATE'), train('EARLY')], null)).toBe('EARLY');
  });

  it('keeps explicit selection', () => {
    const full = {
      byTrain: {
        LATE: emptyHist([[150, 0]]),
      },
    };
    expect(resolveChartTrainId(full, [train('LATE')], 'LATE')).toBe('LATE');
  });
});

describe('isChartTrainLive', () => {
  it('returns false when train left the snapshot', () => {
    expect(isChartTrainLive([train('A')], 'B')).toBe(false);
    expect(isChartTrainLive([train('A')], 'A')).toBe(true);
  });
});
