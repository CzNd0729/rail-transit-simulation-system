/**
 * TrackSegment — 区间轨道电路 SVG 渲染
 * 支持双向轨道（上行/下行），叠加轨道电路占用色块
 */
import type { InterStationSegment } from '../../../types/simulation';

interface TrackSegmentProps {
  segment: InterStationSegment;
  /** 正线 Y 坐标 (世界坐标) */
  y?: number;
  /** 色块高度 (世界坐标) */
  blockHeight?: number;
  /** 是否启用双向轨道 */
  dualTrack?: boolean;
}

const MAIN_COLOR = '#e0e0e0';
const MAIN_STROKE = 4;
const COLOR_OCCUPIED = 'rgba(255, 77, 79, 0.5)';
const COLOR_FREE = 'rgba(82, 196, 26, 0.2)';

// 双向轨道 Y 坐标
const DUAL_TRACK_Y = {
  up: 35,
  down: 45,
};

export default function TrackSegment({
  segment,
  y = 40,
  blockHeight = 8,
  dualTrack = false,
}: TrackSegmentProps) {
  if (!dualTrack) {
    // 单轨道模式（向后兼容）
    return (
      <g>
        <line
          x1={segment.start_chainage}
          y1={y}
          x2={segment.end_chainage}
          y2={y}
          stroke={MAIN_COLOR}
          strokeWidth={MAIN_STROKE}
          strokeLinecap="round"
        />
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

  // 双向轨道模式
  return (
    <g>
      {/* 上行轨道 */}
      <line
        x1={segment.start_chainage}
        y1={DUAL_TRACK_Y.up}
        x2={segment.end_chainage}
        y2={DUAL_TRACK_Y.up}
        stroke={MAIN_COLOR}
        strokeWidth={MAIN_STROKE}
        strokeLinecap="round"
      />

      {/* 下行轨道 */}
      <line
        x1={segment.start_chainage}
        y1={DUAL_TRACK_Y.down}
        x2={segment.end_chainage}
        y2={DUAL_TRACK_Y.down}
        stroke={MAIN_COLOR}
        strokeWidth={MAIN_STROKE}
        strokeLinecap="round"
      />

      {/* 轨道电路色块（上行） */}
      {segment.circuits.map((circuit) => {
        const cx = circuit.start_chainage;
        const cw = circuit.end_chainage - circuit.start_chainage;
        return (
          <rect
            key={`up-${circuit.id}`}
            x={cx}
            y={DUAL_TRACK_Y.up - blockHeight / 2}
            width={Math.max(0, cw - 1)}
            height={blockHeight}
            fill={circuit.occupied ? COLOR_OCCUPIED : COLOR_FREE}
            rx={1}
            opacity={0.7}
          />
        );
      })}

      {/* 轨道电路色块（下行） */}
      {segment.circuits.map((circuit) => {
        const cx = circuit.start_chainage;
        const cw = circuit.end_chainage - circuit.start_chainage;
        return (
          <rect
            key={`down-${circuit.id}`}
            x={cx}
            y={DUAL_TRACK_Y.down - blockHeight / 2}
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
