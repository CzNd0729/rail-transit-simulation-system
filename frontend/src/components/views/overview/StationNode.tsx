/**
 * StationNode — 站内多股道 SVG 渲染
 * 绘制车站范围内的所有股道，正线粗实线、侧线细实线、存车线虚线
 */
import { memo } from 'react';
import type { StationLayout } from '../../../types/simulation';

interface StationNodeProps {
  station: StationLayout;
  /** 是否显示详情 (缩放级别控制) */
  showDetail: boolean;
  /** 点击车站事件 */
  onClick?: (stationId: string) => void;
  /** 鼠标进入事件 */
  onMouseEnter?: (stationId: string) => void;
  /** 鼠标离开事件 */
  onMouseLeave?: () => void;
  /** 是否选中 */
  selected: boolean;
}

const TRACK_STYLES = {
  main: { strokeWidth: 3, stroke: '#e0e0e0', strokeDasharray: '' },
  siding: { strokeWidth: 2, stroke: '#a0a0a0', strokeDasharray: '' },
  parking: { strokeWidth: 2, stroke: '#808080', strokeDasharray: '6 3' },
} as const;

const TRACK_SPACING = 12;
const BORDER_COLOR = '#4a4a6a';

function StationNodeInner({
  station,
  showDetail,
  onClick,
  onMouseEnter,
  onMouseLeave,
  selected,
}: StationNodeProps) {
  const x = station.chainage;
  const w = station.length;
  const trackCount = station.tracks.length;

  const totalHeight = showDetail
    ? Math.max(trackCount * TRACK_SPACING + 8, 20)
    : 16;

  const baseY = 40;
  const startY = baseY - ((trackCount - 1) * TRACK_SPACING) / 2;

  return (
    <g
      onClick={() => onClick?.(station.id)}
      onMouseEnter={() => onMouseEnter?.(station.id)}
      onMouseLeave={onMouseLeave}
      style={{ cursor: 'pointer' }}
    >
      {/* 车站背景 */}
      <rect
        x={x}
        y={baseY - totalHeight / 2}
        width={w}
        height={totalHeight}
        fill={selected ? 'rgba(24, 144, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)'}
        stroke={selected ? '#1890ff' : BORDER_COLOR}
        strokeWidth={selected ? 2 : 1}
        rx={2}
      />

      {/* 车站封边竖线 */}
      <line x1={x} y1={baseY - totalHeight / 2 - 4} x2={x} y2={baseY + totalHeight / 2 + 4}
        stroke={BORDER_COLOR} strokeWidth={1} />
      <line x1={x + w} y1={baseY - totalHeight / 2 - 4} x2={x + w} y2={baseY + totalHeight / 2 + 4}
        stroke={BORDER_COLOR} strokeWidth={1} />

      {/* 站名 */}
      <text
        x={x + w / 2}
        y={baseY - totalHeight / 2 - 6}
        textAnchor="middle"
        fill="#e0e0e0"
        fontSize={10}
        fontWeight={600}
      >
        {station.name}
      </text>

      {/* 公里标 */}
      <text
        x={x + w / 2}
        y={baseY + totalHeight / 2 + 12}
        textAnchor="middle"
        fill="#808080"
        fontSize={8}
      >
        K{(station.chainage / 1000).toFixed(1)}
      </text>

      {/* 股道渲染 (仅 detail 模式) */}
      {showDetail && station.tracks.map((track, i) => {
        const ty = startY + i * TRACK_SPACING;
        const style = TRACK_STYLES[track.type];
        return (
          <g key={track.track_id}>
            {track.occupied && (
              <rect
                x={x + 2}
                y={ty - 3}
                width={w - 4}
                height={6}
                fill="rgba(255, 77, 79, 0.2)"
                rx={1}
              />
            )}
            <line
              x1={x + 4}
              y1={ty}
              x2={x + w - 4}
              y2={ty}
              stroke={track.occupied ? '#ff4d4f' : style.stroke}
              strokeWidth={style.strokeWidth}
              strokeDasharray={style.strokeDasharray || undefined}
            />
            <text
              x={x + 6}
              y={ty - 4}
              fill="#808080"
              fontSize={6}
            >
              {track.name}
            </text>
          </g>
        );
      })}

      {/* 简略模式: 只显示车站方块 + 正线 */}
      {!showDetail && (
        <line
          x1={x + 4}
          y1={baseY}
          x2={x + w - 4}
          y2={baseY}
          stroke="#e0e0e0"
          strokeWidth={3}
        />
      )}
    </g>
  );
}

const StationNode = memo(StationNodeInner);
export default StationNode;
