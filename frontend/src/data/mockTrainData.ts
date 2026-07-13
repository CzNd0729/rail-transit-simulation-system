/**
 * Mock 列车运行数据 — 后端就绪后移除
 */
import { useState, useEffect } from 'react';
import type { TrainState } from '../types/simulation';

const endC = 12100;
const centers: Array<{ c: number; id: string }> = [
  { c: 1875, id: 'ST02' },
  { c: 3560, id: 'ST03' },
  { c: 5325, id: 'ST04' },
  { c: 6865, id: 'ST05' },
  { c: 8590, id: 'ST06' },
  { c: 10260, id: 'ST07' },
];

export function useMockTrain(): TrainState {
  const [s, setS] = useState({ pos: 100, dir: 1, stop: 0, last: '' as string });

  useEffect(() => {
    const id = setInterval(() => {
      setS(prev => {
        if (prev.stop > 0) return { ...prev, stop: prev.stop - 1 };

        let p = prev.pos + 50 * prev.dir;
        let d = prev.dir;
        let stop = 0;
        let last = prev.last;

        if (p >= endC) { p = endC; d = -1; stop = 30; last = ''; }
        else if (p <= 100) { p = 100; d = 1; stop = 30; last = ''; }

        if (stop === 0) {
          for (const { c, id } of centers) {
            if (id !== prev.last && Math.abs(p - c) < 60) { p = c; stop = 30; last = id; break; }
          }
        }

        return { pos: p, dir: d, stop, last };
      });
    }, 100);
    return () => clearInterval(id);
  }, []);

  return {
    id: 'T001',
    position: s.pos,
    speed: s.stop ? 0 : 60,
    acceleration: 0,
    jerk: 0,
    mode: s.stop ? 'braking' : 'traction',
    mass: 30000,
    passenger_count: 200,
    door_status: s.stop ? 'open' : 'closed',
    pantograph_voltage: 1500,
    power_demand: 0,
    distance_to_station: 0,
    target_station_id: '',
    direction: 'up',
    fault_alarm: null,
    traction_force: 0,
    brake_force: 0,
    total_resistance: 0,
    davis_resistance: 0,
    gradient_resistance: 0,
    curve_resistance: 0,
    tunnel_resistance: 0,
  };
}
