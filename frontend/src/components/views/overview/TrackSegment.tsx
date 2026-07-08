/**
 * TrackSegment — 区间轨道电路 SVG 渲染
 * 连续正线 + 叠加轨道电路占用色块
 */
import type { InterStationSegment } from '../../../types/simulation';

interface TrackSegmentProps {
  segment: InterStationSegment;
  /** 正线 Y 坐标 (世界坐标) */
  y: number;
  /** 色块高度 (世界坐标) */
  blockHeight?: number;
}

const MAIN_COLOR = '#e0e0e0';
const MAIN_STROKE = 4;
const COLOR_OCCUPIED = 'rgba(255, 77, 79, 0.5)';
const COLOR_FREE = 'rgba(82, 196, 26, 0.2)';

export default function TrackSegment({ segment, y, blockHeight = 8 }: TrackSegmentProps) {
  return (
    <g>
      {/* 正线 — 与车站内正线贯通 */}
      <line
        x1={segment.start_chainage}
        y1={y}
        x2={segment.end_chainage}
        y2={y}
        stroke={MAIN_COLOR}
        strokeWidth={MAIN_STROKE}
        strokeLinecap="round"
      />

      {/* 轨道电路占用色块 — 叠加在正线上方 */}
      {segment.circuits.map((circuit) => {
        const cx = circuit.start_chainage;
        const cw = circuit.end_chainage - circuit.start_chainage;
        return (
          <rect
            key={circuit.id}
            x={cx}
            y={y - blockHeight / 2}
            width={Math.max(0, cw - 1)}
            height={blockHeight}
            fill={circuit.occupied ? COLOR_OCCUPIED : COLOR_FREE}
            rx={1}
            opacity={0.7}
          />
        );
      })}
    </g>
  );
}
