import { describe, it, expect } from 'vitest';
import { buildMvpLineLayout, buildProfileSegments } from '../data/mvpLineLayout';
import { parseApiLineConfig } from './lineLayoutAdapter';

describe('buildMvpLineLayout', () => {
  it('builds 3-station layout matching track.yaml chainages', () => {
    const layout = buildMvpLineLayout();
    expect(layout.total_length).toBe(3200);
    expect(layout.stations.map((s) => s.chainage)).toEqual([0, 1500, 3200]);
    expect(layout.stations[0].name).toBe('A站');
  });

  it('applies gradient override on SEC02 for scenario 2', () => {
    const segs = buildProfileSegments(30);
    const sec02 = segs.find((s) => s.start_chainage === 1500);
    expect(sec02?.gradient).toBe(30);
  });
});

describe('parseApiLineConfig', () => {
  it('converts camelCase backend line to LineLayout', () => {
    const raw = {
      name: '1号线',
      totalLength: 3200,
      stations: [
        { id: 'ST01', name: 'A站', chainage: 0, dwellTime: 30 },
        { id: 'ST02', name: 'B站', chainage: 1500, dwellTime: 30 },
        { id: 'ST03', name: 'C站', chainage: 3200, dwellTime: 30 },
      ],
      segments: [
        { id: 'SEC01', startChainage: 0, endChainage: 1500, gradient: 5, curvature: 800, speedLimit: 80, isTunnel: false },
        { id: 'SEC02', startChainage: 1500, endChainage: 3200, gradient: 0, curvature: 1200, speedLimit: 80, isTunnel: false },
      ],
    };
    const { layout, profileSegments } = parseApiLineConfig(raw);
    expect(layout.total_length).toBe(3200);
    expect(profileSegments[0].gradient).toBe(5);
    expect(layout.stations[1].chainage).toBe(1500);
  });
});
