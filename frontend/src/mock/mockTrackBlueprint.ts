import type { Station, Segment } from '../types/simulation';

/** MVP 验收线路：A(0) → B(1500) → C(3200)，2 区间 */
export const MOCK_STATIONS: Station[] = [
  { id: 'ST01', name: 'A站', chainage: 0, dwell_time: 30, platform_half_length: 15, is_terminus: true, sort_order: 1 },
  { id: 'ST02', name: 'B站', chainage: 1500, dwell_time: 30, platform_half_length: 15, is_terminus: false, sort_order: 2 },
  { id: 'ST03', name: 'C站', chainage: 3200, dwell_time: 30, platform_half_length: 15, is_terminus: true, sort_order: 3 },
];

export const MOCK_SEGMENTS: Segment[] = [
  { id: 'SEC01', start_chainage: 0, end_chainage: 1500, gradient: 5, curvature: 800, speed_limit: 80, is_tunnel: false, sort_order: 1 },
  { id: 'SEC02', start_chainage: 1500, end_chainage: 3200, gradient: 30, curvature: 1200, speed_limit: 80, is_tunnel: false, sort_order: 2 },
];

export function getSegmentAt(position: number, gradientOverride?: number): Segment {
  const seg = MOCK_SEGMENTS.find(
    (s) => position >= s.start_chainage && position < s.end_chainage,
  ) ?? MOCK_SEGMENTS[MOCK_SEGMENTS.length - 1];
  if (gradientOverride !== undefined && seg.id === 'SEC02') {
    return { ...seg, gradient: gradientOverride };
  }
  return seg;
}
