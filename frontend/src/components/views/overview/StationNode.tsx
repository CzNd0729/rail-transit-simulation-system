/**
 * StationNode — 站内多股道 SVG 渲染
 * 支持双向正线（上行/下行），侧线通过贝塞尔曲线从正线平滑分岔
 */
import { memo } from 'react';
import type { StationLayout } from '../../../types/simulation';

interface StationNodeProps {
  station: StationLayout;
  /** 是否显示详情 */
  showDetail: boolean;
  /** 点击车站事件 */
  onClick?: (stationId: string) => void;
  /** 是否选中 */
  selected: boolean;
  /** 是否启用双向轨道 */
  dualTrack?: boolean;
  /** 当前缩放倍率（用于固定文字大小） */
  zoom?: number;
  /** 车站索引（用于交替上下布局） */
  index?: number;
}

const MAIN_TRACK_Y = 40;
const DUAL_TRACK_Y = { up: 25, down: 55 };
const MAIN_STROKE = 4;
const SIDING_STROKE = 2.5;
const TRACK_SPACING = 14;
const CURVE_LENGTH = 30;
const MAIN_COLOR = '#e0e0e0';
const SIDING_COLOR = '#a0a0a0';
const PARKING_COLOR = '#808080';
const OCCUPIED_COLOR = '#ff4d4f';

function StationNodeInner({
  station,
  showDetail,
  onClick,
  selected,
  dualTrack = false,
  zoom = 1,
  index = 0,
}: StationNodeProps) {
  const x = station.chainage;
  const w = station.length;
  const sidings = station.tracks.filter(t => t.type !== 'main');

  const totalHeight = showDetail
    ? Math.max((sidings.length + 1) * TRACK_SPACING + 20, 30)
    : dualTrack ? 60 : 20;

  // 固定文字大小：直接计算抵消 viewBox 缩放的字体大小
  const scaleFactor = 10;
  const baseNameFontSize = (dualTrack ? 18 : 13) * scaleFactor;
  const baseChainageFontSize = (dualTrack ? 14 : 9) * scaleFactor;
  const nameFontSize = baseNameFontSize / zoom;
  const chainageFontSize = baseChainageFontSize / zoom;

  // 交替布局：偶数索引在上方，奇数索引在下方
  // 上下间隔固定为最大缩放时的屏幕距离，除以 zoom 保持屏幕空间恒定
  const isAbove = index % 2 === 0;
  const verticalOffset = 400 / zoom; // 屏幕空间 400px 的固定间隔
  const textY = isAbove
    ? (dualTrack ? DUAL_TRACK_Y.up - verticalOffset : MAIN_TRACK_Y - totalHeight / 2 - verticalOffset)
    : (dualTrack ? DUAL_TRACK_Y.down + verticalOffset : MAIN_TRACK_Y + totalHeight / 2 + verticalOffset);

  return (
    <g
      onClick={() => onClick?.(station.id)}
      style={{ cursor: 'pointer' }}
    >
      {/* 透明命中区 */}
      <rect
        x={x}
        y={MAIN_TRACK_Y - totalHeight / 2 - 4}
        width={w}
        height={totalHeight + 8}
        fill="transparent"
        pointerEvents="all"
      />

      {/* 车站选中外框 */}
      {selected && (
        <rect
          x={x - 2}
          y={MAIN_TRACK_Y - totalHeight / 2 - 2}
          width={w + 4}
          height={totalHeight + 4}
          fill="none"
          stroke="#1890ff"
          strokeWidth={1.5}
          strokeDasharray="4 2"
          rx={3}
          opacity={0.6}
        />
      )}

      {/* 正线渲染 */}
      {dualTrack ? (
        <>
          {/* 上行正线 */}
          <line
            x1={x}
            y1={DUAL_TRACK_Y.up}
            x2={x + w}
            y2={DUAL_TRACK_Y.up}
            stroke={MAIN_COLOR}
            strokeWidth={MAIN_STROKE}
            strokeLinecap="round"
          />
          {/* 下行正线 */}
          <line
            x1={x}
            y1={DUAL_TRACK_Y.down}
            x2={x + w}
            y2={DUAL_TRACK_Y.down}
            stroke={MAIN_COLOR}
            strokeWidth={MAIN_STROKE}
            strokeLinecap="round"
          />
        </>
      ) : (
        /* 单正线（向后兼容） */
        <line
          x1={x}
          y1={MAIN_TRACK_Y}
          x2={x + w}
          y2={MAIN_TRACK_Y}
          stroke={MAIN_COLOR}
          strokeWidth={MAIN_STROKE}
          strokeLinecap="round"
        />
      )}

      {/* 车站封端标记 */}
      <line x1={x} y1={MAIN_TRACK_Y - 6} x2={x} y2={MAIN_TRACK_Y + 6}
        stroke="#4a4a6a" strokeWidth={1.5} />
      <line x1={x + w} y1={MAIN_TRACK_Y - 6} x2={x + w} y2={MAIN_TRACK_Y + 6}
        stroke="#4a4a6a" strokeWidth={1.5} />

      {/* 站名 + 公里标（固定大小，交替上下布局） */}
      <text
        x={x + w / 2}
        y={textY}
        textAnchor="middle"
        fill="#e0e0e0"
        fontSize={nameFontSize}
        fontWeight={700}
      >
        {station.name}
      </text>
      <text
        x={x + w / 2}
        y={textY + nameFontSize * 1.2}
        textAnchor="middle"
        fill="#a0a0a0"
        fontSize={chainageFontSize}
      >
        K{(station.chainage / 1000).toFixed(1)}+{station.length}m
      </text>

      {/* 侧线 + 道岔连接 (仅 detail 模式) */}
      {showDetail && sidings.map((track, i) => {
        const sidingY = MAIN_TRACK_Y + (i + 1) * TRACK_SPACING;
        const isOccupied = track.occupied;
        const color = isOccupied ? OCCUPIED_COLOR : (track.type === 'parking' ? PARKING_COLOR : SIDING_COLOR);

        const curveStartX = x + CURVE_LENGTH;
        const curveEndX = x + w - CURVE_LENGTH;
        const sidingW = curveEndX - curveStartX;

        return (
          <g key={track.track_id}>
            {/* 左侧道岔曲线 */}
            <path
              d={`M ${x},${MAIN_TRACK_Y} Q ${x + CURVE_LENGTH * 0.6},${MAIN_TRACK_Y} ${curveStartX},${sidingY}`}
              fill="none"
              stroke={color}
              strokeWidth={SIDING_STROKE}
              strokeLinecap="round"
            />

            {/* 侧线主体 */}
            <line
              x1={curveStartX}
              y1={sidingY}
              x2={curveEndX}
              y2={sidingY}
              stroke={color}
              strokeWidth={SIDING_STROKE}
              strokeDasharray={track.type === 'parking' ? '6 3' : undefined}
              strokeLinecap="round"
            />

            {/* 右侧道岔曲线 */}
            <path
              d={`M ${curveEndX},${sidingY} Q ${x + w - CURVE_LENGTH * 0.6},${MAIN_TRACK_Y} ${x + w},${MAIN_TRACK_Y}`}
              fill="none"
              stroke={color}
              strokeWidth={SIDING_STROKE}
              strokeLinecap="round"
            />

            {/* 占用底色 */}
            {isOccupied && (
              <rect
                x={curveStartX}
                y={sidingY - 3}
                width={sidingW}
                height={6}
                fill="rgba(255, 77, 79, 0.15)"
                rx={2}
              />
            )}

            {/* 股道名称 */}
            <text
              x={curveStartX + 4}
              y={sidingY - 5}
              fill="#808080"
              fontSize={6}
            >
              {track.name}
            </text>
          </g>
        );
      })}

      {/* 简略模式 */}
      {!showDetail && !dualTrack && (
        <rect
          x={x}
          y={MAIN_TRACK_Y - 8}
          width={w}
          height={16}
          fill="rgba(255, 255, 255, 0.03)"
          rx={2}
        />
      )}
    </g>
  );
}

const StationNode = memo(StationNodeInner);
export default StationNode;
