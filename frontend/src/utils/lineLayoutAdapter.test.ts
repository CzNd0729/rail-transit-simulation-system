import { describe, it, expect } from 'vitest';
import { buildMvpLineLayout, buildProfileSegments } from '../data/mvpLineLayout';

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
