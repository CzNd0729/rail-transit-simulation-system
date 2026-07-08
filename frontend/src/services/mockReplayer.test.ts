import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createMockReplayer } from './mockReplayer';
import type { MockReplayScenario } from '../types/simulation';

const miniScenario: MockReplayScenario = {
  meta: { name: 'test', description: '', timeStep: 1, totalDuration: 2 },
  vehicleParams: {} as MockReplayScenario['vehicleParams'],
  frames: [
    { t: 0, position: 0, speed: 0, acceleration: 0, mode: 'traction', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 0 },
    { t: 1, position: 10, speed: 5, acceleration: 0.5, mode: 'traction', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 100 },
    { t: 2, position: 20, speed: 10, acceleration: 0.5, mode: 'coasting', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 0 },
  ],
};

describe('createMockReplayer', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('step advances one frame', () => {
    const onTick = vi.fn();
    const replayer = createMockReplayer(miniScenario, { onTick, onComplete: vi.fn() });
    replayer.step();
    expect(onTick).toHaveBeenCalledOnce();
    expect(onTick.mock.calls[0][0].clock.elapsed).toBe(0);
    replayer.step();
    expect(onTick).toHaveBeenCalledTimes(2);
  });

  it('calls onComplete when all frames played', () => {
    const onComplete = vi.fn();
    const replayer = createMockReplayer(miniScenario, { onTick: vi.fn(), onComplete });
    replayer.step(); replayer.step(); replayer.step();
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
