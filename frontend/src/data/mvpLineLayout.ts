import { MOCK_STATIONS, MOCK_SEGMENTS } from '../mock/mockTrackBlueprint';
import type { LineLayout, StationLayout, InterStationSegment } from '../types/simulation';

export interface ProfileSegment {
  start_chainage: number;
  end_chainage: number;
  gradient: number;
  speed_limit: number;
  is_tunnel: boolean;
}

const DEFAULT_STATION_LENGTH = 120;

function toStationLayout(station: (typeof MOCK_STATIONS)[0]): StationLayout {
  return {
    ...station,
    length: DEFAULT_STATION_LENGTH,
    tracks: [{ track_id: 'MAIN', name: '正线', type: 'main', occupied: false }],
    occupancy_rate: 0,
  };
}

function toInterStationSegment(seg: (typeof MOCK_SEGMENTS)[0]): InterStationSegment {
  return {
    start_chainage: seg.start_chainage,
    end_chainage: seg.end_chainage,
    circuits: [{
      id: `${seg.id}_C1`,
      start_chainage: seg.start_chainage,
      end_chainage: seg.end_chainage,
      direction: 'both',
      occupied: false,
    }],
  };
}

export function buildProfileSegments(gradientSec02?: number): ProfileSegment[] {
  return MOCK_SEGMENTS.map((seg) => ({
    start_chainage: seg.start_chainage,
    end_chainage: seg.end_chainage,
    gradient: seg.id === 'SEC02' && gradientSec02 !== undefined ? gradientSec02 : seg.gradient,
    speed_limit: seg.speed_limit,
    is_tunnel: seg.is_tunnel,
  }));
}

export function buildMvpLineLayout(gradientSec02?: number): LineLayout {
  const profile = buildProfileSegments(gradientSec02);
  return {
    name: '1号线',
    stations: MOCK_STATIONS.map(toStationLayout),
    segments: MOCK_SEGMENTS.map(toInterStationSegment),
    total_length: profile[profile.length - 1].end_chainage,
  };
}
