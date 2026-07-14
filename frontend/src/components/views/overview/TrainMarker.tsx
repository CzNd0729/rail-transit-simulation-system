/**
 * TrainMarker — 列车多车厢 SVG 渲染
 * 120m 总长，6 节车厢，跟随工况着色，沿轨道曲线行驶
 */
import type { TrainState, StationLayout } from '../../../types/simulation';

interface TrainMarkerProps {
  train: TrainState;
  direction?: 'up' | 'down';
  selected?: boolean;
  onSelect?: () => void;
  stations?: StationLayout[];
  transitionLength?: number;
}

const TRAIN_LENGTH = 120; // 列车总长 (m)
const CAR_COUNT = 6;
const CAR_LENGTH = TRAIN_LENGTH / CAR_COUNT; // 20m
const CAR_GAP = 1; // 车厢间距 (m)
const TRAIN_HEIGHT = 12; // 车身高度 (px)

const MODE_COLORS: Record<string, string> = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

// 轨道 Y 坐标
const SEGMENT_Y = { up: 35, down: 45 };
const STATION_Y = { up: 25, down: 55 };

/** 计算三次贝塞尔曲线上的 Y 值 */
function bezierY(t: number, y0: number, y1: number, y2: number, y3: number): number {
  const t2 = t * t;
  const t3 = t2 * t;
  const mt = 1 - t;
  const mt2 = mt * mt;
  const mt3 = mt2 * mt;
  return mt3 * y0 + 3 * mt2 * t * y1 + 3 * mt * t2 * y2 + t3 * y3;
}

/** 根据 X 坐标计算列车所在轨道的 Y 坐标 */
function getTrackY(x: number, direction: 'up' | 'down', stations?: StationLayout[], transitionLength = 500): number {
  if (!stations) return SEGMENT_Y[direction];

  for (const station of stations) {
    const stationStart = station.chainage;
    const stationEnd = station.chainage + station.length;

    // 在车站内
    if (x >= stationStart && x <= stationEnd) {
      return STATION_Y[direction];
    }

    // 进站过渡区
    const entryStart = stationStart - transitionLength;
    if (x >= entryStart && x < stationStart) {
      const t = (x - entryStart) / transitionLength;
      // Bezier: (entryStart, SEGMENT_Y) -> (stationStart, STATION_Y)
      // 控制点: (mid, SEGMENT_Y) 和 (mid, STATION_Y)
      return bezierY(t, SEGMENT_Y[direction], SEGMENT_Y[direction], STATION_Y[direction], STATION_Y[direction]);
    }

    // 出站过渡区
    const exitEnd = stationEnd + transitionLength;
    if (x > stationEnd && x <= exitEnd) {
      const t = (x - stationEnd) / transitionLength;
      // Bezier: (stationEnd, STATION_Y) -> (exitEnd, SEGMENT_Y)
      return bezierY(t, STATION_Y[direction], STATION_Y[direction], SEGMENT_Y[direction], SEGMENT_Y[direction]);
    }
  }

  return SEGMENT_Y[direction];
}

export default function TrainMarker({
  train,
  direction = 'up',
  selected = false,
  onSelect,
  stations,
  transitionLength = 500,
}: TrainMarkerProps) {
  const color = MODE_COLORS[train.mode] || '#999';
  const stroke = selected ? '#ffffff' : 'transparent';
  const strokeWidth = selected ? 1.5 : 0;

  // position 是列车车尾位置，车身向前延伸
  const trainStart = train.position;

  return (
    <g
      style={{ cursor: onSelect ? 'pointer' : undefined }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect?.();
      }}
    >
      {/* 6 节车厢，每节根据位置计算 Y 坐标 */}
      {Array.from({ length: CAR_COUNT }).map((_, i) => {
        const carX = trainStart + i * (CAR_LENGTH + CAR_GAP);
        const carCenterX = carX + (CAR_LENGTH - CAR_GAP) / 2;
        const y = getTrackY(carCenterX, direction, stations, transitionLength);
        return (
          <rect
            key={i}
            x={carX}
            y={y - TRAIN_HEIGHT / 2}
            width={CAR_LENGTH - CAR_GAP}
            height={TRAIN_HEIGHT}
            fill={color}
            stroke={stroke}
            strokeWidth={strokeWidth}
            rx={2}
          />
        );
      })}

      {/* 车头箭头 */}
      {(() => {
        const headX = trainStart + TRAIN_LENGTH;
        const headY = getTrackY(headX, direction, stations, transitionLength);
        return (
          <polygon
            points={`${headX},${headY - 4} ${headX + 4},${headY} ${headX},${headY + 4}`}
            fill={color}
          />
        );
      })()}

      {/* 速度标注 */}
      {(() => {
        const centerX = trainStart + TRAIN_LENGTH / 2;
        const centerY = getTrackY(centerX, direction, stations, transitionLength);
        // 下轨标注放在车身下方，避免与上轨车身重叠
        const labelY = direction === 'down'
          ? centerY + TRAIN_HEIGHT / 2 + 10
          : centerY - TRAIN_HEIGHT / 2 - 2;
        return (
          <text
            x={centerX}
            y={labelY}
            textAnchor="middle"
            fontSize={8}
            fill={color}
            fontWeight={600}
          >
            {train.id} · {train.speed.toFixed(0)}km/h
          </text>
        );
      })()}
    </g>
  );
}
