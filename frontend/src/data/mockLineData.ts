/**
 * Mock 线路数据 — 8 站线路
 * 用于前端开发阶段，后端就绪后替换为 API 数据
 */
import type { LineLayout, StationLayout, InterStationSegment, TrackCircuit, Switch, Segment } from '../types/simulation';

// ==================== 车站定义 ====================

const stations: StationLayout[] = [
  {
    id: 'ST01', name: '始发站', chainage: 0, dwell_time: 30,
    platform_half_length: 100, is_terminus: true, sort_order: 1,
    length: 200,
    tracks: [
      { track_id: 'ST01-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST01-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST01-s2', name: '侧线2', type: 'siding', occupied: true },
      { track_id: 'ST01-p1', name: '存车线', type: 'parking', occupied: false },
    ],
    occupancy_rate: 0.25,
  },
  {
    id: 'ST02', name: '科技园', chainage: 1800, dwell_time: 25,
    platform_half_length: 75, is_terminus: false, sort_order: 2,
    length: 150,
    tracks: [
      { track_id: 'ST02-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST02-s1', name: '侧线1', type: 'siding', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST03', name: '大学城', chainage: 3500, dwell_time: 20,
    platform_half_length: 60, is_terminus: false, sort_order: 3,
    length: 120,
    tracks: [
      { track_id: 'ST03-main', name: '正线', type: 'main', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST04', name: '市中心', chainage: 5200, dwell_time: 35,
    platform_half_length: 125, is_terminus: false, sort_order: 4,
    length: 250,
    tracks: [
      { track_id: 'ST04-main', name: '正线', type: 'main', occupied: true },
      { track_id: 'ST04-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST04-s2', name: '侧线2', type: 'siding', occupied: true },
    ],
    occupancy_rate: 0.67,
  },
  {
    id: 'ST05', name: '商业街', chainage: 6800, dwell_time: 25,
    platform_half_length: 65, is_terminus: false, sort_order: 5,
    length: 130,
    tracks: [
      { track_id: 'ST05-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST05-s1', name: '侧线1', type: 'siding', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST06', name: '工业区', chainage: 8500, dwell_time: 30,
    platform_half_length: 90, is_terminus: false, sort_order: 6,
    length: 180,
    tracks: [
      { track_id: 'ST06-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST06-s1', name: '侧线1', type: 'siding', occupied: true },
      { track_id: 'ST06-p1', name: '存车线', type: 'parking', occupied: false },
    ],
    occupancy_rate: 0.33,
  },
  {
    id: 'ST07', name: '新城', chainage: 10200, dwell_time: 20,
    platform_half_length: 60, is_terminus: false, sort_order: 7,
    length: 120,
    tracks: [
      { track_id: 'ST07-main', name: '正线', type: 'main', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST08', name: '终点站', chainage: 12000, dwell_time: 30,
    platform_half_length: 100, is_terminus: true, sort_order: 8,
    length: 200,
    tracks: [
      { track_id: 'ST08-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST08-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST08-s2', name: '侧线2', type: 'siding', occupied: false },
      { track_id: 'ST08-p1', name: '存车线', type: 'parking', occupied: true },
    ],
    occupancy_rate: 0.25,
  },
];

// ==================== 区间轨道电路 ====================

function generateCircuits(start: number, end: number, prefix: string): TrackCircuit[] {
  const circuits: TrackCircuit[] = [];
  const segmentLen = 300;
  let pos = start;
  let idx = 0;
  while (pos < end) {
    const next = Math.min(pos + segmentLen + Math.floor(Math.sin(idx * 1.7) * 80), end);
    circuits.push({
      id: `${prefix}-TC${idx + 1}`,
      start_chainage: pos,
      end_chainage: next,
      direction: 'both',
      occupied: idx % 5 === 2,
    });
    pos = next;
    idx++;
  }
  return circuits;
}

const segments: InterStationSegment[] = [];
for (let i = 0; i < stations.length - 1; i++) {
  const startStation = stations[i];
  const endStation = stations[i + 1];
  const segStart = startStation.chainage + startStation.length;
  const segEnd = endStation.chainage;
  segments.push({
    start_chainage: segStart,
    end_chainage: segEnd,
    circuits: generateCircuits(segStart, segEnd, `SEG${i + 1}`),
  });
}

// ==================== 导出 ====================

export const mockLineData: LineLayout = {
  name: 'NULL示范线',
  stations,
  segments,
  total_length: 12200,
};

// ==================== Mock 道岔数据 ====================

export const mockSwitches: Switch[] = [
  {
    id: 'SW01', chainage: 100, type: 'single',
    normal_direction: 'ST01→ST02', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW02', chainage: 1900, type: 'single',
    normal_direction: 'ST02→ST03', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW03', chainage: 3600, type: 'crossover',
    normal_direction: '上行→下行', reverse_direction: '上行→上行',
    lateral_speed_limit: 30, state: 'reverse',
  },
  {
    id: 'SW04', chainage: 5300, type: 'single',
    normal_direction: 'ST04→ST05', reverse_direction: '侧线2',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW05', chainage: 6900, type: 'single',
    normal_direction: 'ST05→ST06', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'transitioning',
  },
  {
    id: 'SW06', chainage: 8600, type: 'single',
    normal_direction: 'ST06→ST07', reverse_direction: '存车线',
    lateral_speed_limit: 20, state: 'reverse',
  },
  {
    id: 'SW07', chainage: 10300, type: 'crossover',
    normal_direction: '上行→下行', reverse_direction: '上行→上行',
    lateral_speed_limit: 30, state: 'normal',
  },
  {
    id: 'SW08', chainage: 12100, type: 'single',
    normal_direction: 'ST08→折返', reverse_direction: '存车线',
    lateral_speed_limit: 20, state: 'normal',
  },
];

// ==================== Mock 区段参数 ====================

export const mockSegmentParams: Segment[] = [
  { id: 'SEG1', start_chainage: 200,  end_chainage: 1650, gradient: 5,   curvature: 2000, speed_limit: 80, is_tunnel: false, sort_order: 1 },
  { id: 'SEG2', start_chainage: 1950, end_chainage: 3440, gradient: 10,  curvature: 1500, speed_limit: 80, is_tunnel: true,  sort_order: 2 },
  { id: 'SEG3', start_chainage: 3560, end_chainage: 5075, gradient: -5,  curvature: 3000, speed_limit: 80, is_tunnel: false, sort_order: 3 },
  { id: 'SEG4', start_chainage: 5325, end_chainage: 6735, gradient: 0,   curvature: 0,    speed_limit: 60, is_tunnel: false, sort_order: 4 },
  { id: 'SEG5', start_chainage: 6865, end_chainage: 8410, gradient: 30,  curvature: 800,  speed_limit: 80, is_tunnel: true,  sort_order: 5 },
  { id: 'SEG6', start_chainage: 8590, end_chainage: 10140, gradient: -15, curvature: 1200, speed_limit: 80, is_tunnel: false, sort_order: 6 },
  { id: 'SEG7', start_chainage: 10260, end_chainage: 11900, gradient: 5,  curvature: 2500, speed_limit: 80, is_tunnel: false, sort_order: 7 },
];
