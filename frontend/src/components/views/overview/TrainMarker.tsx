/**
 * TrainMarker — 列车图标 SVG 渲染
 * 支持双向轨道，根据 direction 选择上行/下行轨道 Y 坐标
 */
import type { TrainState } from '../../../types/simulation';

interface TrainMarkerProps {
  train: TrainState;
  /** 正线 Y 坐标 (世界坐标，单轨模式) */
  trackY?: number;
  /** 列车方向（双向轨道模式） */
  direction?: 'up' | 'down';
}

const MODE_COLORS: Record<string, string> = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

// 双向轨道 Y 坐标
const DUAL_TRACK_Y = {
  up: 35,
  down: 45,
  default: 35,
};

export default function TrainMarker({ train, trackY, direction }: TrainMarkerProps) {
  const color = MODE_COLORS[train.mode] || '#999';
  const x = train.position;

  // 确定 Y 坐标：优先 direction，其次 trackY，最后默认值
  const y = direction
    ? DUAL_TRACK_Y[direction]
    : trackY ?? DUAL_TRACK_Y.default;

  return (
    <g style={{ transition: 'transform 100ms linear' }}>
      {/* 列车背景色块 */}
      <rect
        x={x - 10}
        y={y - 8}
        width={20}
        height={16}
        rx={4}
        fill={color}
        opacity={0.9}
      />
      {/* 列车图标 */}
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fontSize={10}
        fill="#fff"
      >
        🚇
      </text>
      {/* 速度标注 */}
      <text
        x={x}
        y={y - 12}
        textAnchor="middle"
        fontSize={7}
        fill={color}
        fontWeight={600}
      >
        {train.speed.toFixed(0)}km/h
      </text>
    </g>
  );
}
