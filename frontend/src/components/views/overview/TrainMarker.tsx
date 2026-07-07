/**
 * TrainMarker — 列车图标 SVG 渲染
 * 在正线上显示列车位置，底色跟随工况
 */
import type { TrainState } from '../../../types/simulation';

interface TrainMarkerProps {
  train: TrainState;
  /** 正线 Y 坐标 (世界坐标) */
  trackY: number;
}

const MODE_COLORS: Record<string, string> = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

export default function TrainMarker({ train, trackY }: TrainMarkerProps) {
  const color = MODE_COLORS[train.mode] || '#999';
  const x = train.position;

  return (
    <g style={{ transition: 'transform 100ms linear' }}>
      {/* 列车背景色块 */}
      <rect
        x={x - 10}
        y={trackY - 8}
        width={20}
        height={16}
        rx={4}
        fill={color}
        opacity={0.9}
      />
      {/* 列车图标 */}
      <text
        x={x}
        y={trackY + 4}
        textAnchor="middle"
        fontSize={10}
        fill="#fff"
      >
        🚇
      </text>
      {/* 速度标注 */}
      <text
        x={x}
        y={trackY - 12}
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
