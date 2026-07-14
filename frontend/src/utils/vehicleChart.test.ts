import { describe, it, expect } from 'vitest';
import { xAxisSplitLineForRunState } from './vehicleChart';

describe('xAxisSplitLineForRunState', () => {
  it('hides vertical splitLine when simulation is idle', () => {
    expect(xAxisSplitLineForRunState('idle')).toEqual({ show: false });
  });

  it('shows vertical splitLine when running/paused/stopped', () => {
    expect(xAxisSplitLineForRunState('running')).toEqual({ show: true });
    expect(xAxisSplitLineForRunState('paused')).toEqual({ show: true });
    expect(xAxisSplitLineForRunState('stopped')).toEqual({ show: true });
  });
});
