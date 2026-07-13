import { describe, it, expect } from 'vitest';
import { frameToSnapshot } from './frameToSnapshot';

describe('frameToSnapshot', () => {
  it('maps mock signaling fields when present on frame', () => {
    const snap = frameToSnapshot({
      t: 10,
      position: 500,
      speed: 60,
      acceleration: 0.5,
      mode: 'traction',
      mass: 254000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: 800,
      running_phase: 'traction',
      distance_to_station: 700,
      target_station_id: 'ST_B',
      traction_level: 0.6,
      brake_level: 0,
    });
    expect(snap.trains[0].distance_to_station).toBe(700);
    expect(snap.trains[0].target_station_id).toBe('ST_B');
    expect(snap.signaling.commands[0]?.running_phase).toBe('traction');
    expect(snap.signaling.commands[0]?.traction_level).toBe(0.6);
    expect(snap.signaling.ma_profiles[0]).toEqual({
      train_id: 'TRAIN_01',
      ma_end_chainage: 1200,
      safety_distance: 300,
    });
    expect(snap.signaling.speed_limits[0]?.permanent_limit).toBe(80);
    expect(snap.signaling.speed_limits[0]?.atp_limit).toBe(76);
  });

  it('maps explicit mock ATP/ATS fields from frame', () => {
    const snap = frameToSnapshot({
      t: 120,
      position: 1500,
      speed: 0,
      acceleration: 0,
      mode: 'coasting',
      mass: 254000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: 0,
      ma_end_chainage: 3200,
      safety_distance: 300,
      permanent_speed_limit: 80,
      atp_speed_limit: 76,
      timetable_deviation: {
        train_id: 'TRAIN_01',
        station_id: 'ST02',
        delay_arrival: 2.5,
        nominal_dwell: 30,
        adjusted_dwell: 32.5,
      },
    });
    expect(snap.signaling.ma_profiles[0]?.ma_end_chainage).toBe(3200);
    expect(snap.signaling.timetable_deviations[0]?.station_id).toBe('ST02');
  });

  it('derives running_phase from mode when frame field missing', () => {
    const snap = frameToSnapshot({
      t: 5,
      position: 1500,
      speed: 0,
      acceleration: 0,
      mode: 'coasting',
      mass: 254000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: 0,
    });
    expect(snap.signaling.commands[0]?.running_phase).toBe('dwell');
  });
});
