/**
 * TrackSegment — 区间轨道电路 SVG 渲染
 * 在两站之间绘制轨道电路色块，颜色表示占用/空闲状态
 */
import type { InterStationSegment } from '../../../types/simulation';

interface TrackSegmentProps {
  segment: InterStationSegment;
  /** Y 坐标基准线 (世界坐标) */
  y: number;
  /** 色块高度 (世界坐标) */
  height?: number;
}

const COLOR_OCCUPIED = 'rgba(255, 77, 79, 0.6)';
const COLOR_FREE = 'rgba(82, 196, 26, 0.3)';
const GAP_COLOR = '#2a2a4a';

export default function TrackSegment({ segment, y, height = 6 }: TrackSegmentProps) {
  return (
    <g>
      {segment.circuits.map((circuit) => {
        const x = circuit.start_chainage;
        const w = circuit.end_chainage - circuit.start_chainage;
        return (
          <rect
            key={circuit.id}
            x={x}
            y={y - height / 2}
            width={Math.max(0, w - 1)}
            height={height}
            fill={circuit.occupied ? COLOR_OCCUPIED : COLOR_FREE}
            rx={1}
          />
        );
      })}
      {/* 区间基准线 (轨道中心线) */}
      <line
        x1={segment.start_chainage}
        y1={y}
        x2={segment.end_chainage}
        y2={y}
        stroke={GAP_COLOR}
        strokeWidth={1}
        strokeDasharray="4 2"
      />
    </g>
  );
}
