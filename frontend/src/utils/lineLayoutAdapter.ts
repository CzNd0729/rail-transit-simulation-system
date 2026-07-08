import { buildMvpLineLayout, type ProfileSegment } from '../data/mvpLineLayout';
import type { LineLayout, StationLayout } from '../types/simulation';

function toStationLayout(raw: Record<string, unknown>): StationLayout {
  const chainage = Number(raw.chainage ?? 0);
  return {
    id: String(raw.id),
    name: String(raw.name),
    chainage,
    dwell_time: Number(raw.dwellTime ?? raw.dwell_time ?? 30),
    platform_half_length: 15,
    is_terminus: chainage === 0,
    sort_order: 0,
    length: 120,
    tracks: [{ track_id: 'MAIN', name: '正线', type: 'main', occupied: false }],
    occupancy_rate: 0,
  };
}

export function parseApiLineConfig(raw: Record<string, unknown>): {
  layout: LineLayout;
  profileSegments: ProfileSegment[];
} {
  const stations = (raw.stations as Record<string, unknown>[] | undefined) ?? [];
  const segments = (raw.segments as Record<string, unknown>[] | undefined) ?? [];

  const profileSegments: ProfileSegment[] = segments.map((s) => ({
    start_chainage: Number(s.startChainage ?? s.start_chainage),
    end_chainage: Number(s.endChainage ?? s.end_chainage),
    gradient: Number(s.gradient),
    speed_limit: Number(s.speedLimit ?? s.speed_limit),
    is_tunnel: Boolean(s.isTunnel ?? s.is_tunnel),
  }));

  const layout: LineLayout = {
    name: String(raw.name ?? '1号线'),
    stations: stations.map(toStationLayout),
    segments: segments.map((s) => ({
      start_chainage: Number(s.startChainage ?? s.start_chainage),
      end_chainage: Number(s.endChainage ?? s.end_chainage),
      circuits: [{
        id: `${s.id}_C1`,
        start_chainage: Number(s.startChainage ?? s.start_chainage),
        end_chainage: Number(s.endChainage ?? s.end_chainage),
        direction: 'both',
        occupied: false,
      }],
    })),
    total_length: Number(raw.totalLength ?? raw.total_length ?? profileSegments.at(-1)?.end_chainage ?? 3200),
  };

  return { layout, profileSegments };
}

export function getDefaultLineLayout(): LineLayout {
  return buildMvpLineLayout();
}
