/**
 * LineDiagram — 交互式线路图主容器
 * 支持双向轨道渲染，进出站贝塞尔曲线过渡
 */
import { useRef, useState, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useViewport } from '../../../hooks/useViewport';
import StationNode from './StationNode';
import TrainMarker from './TrainMarker';
import StationInfoCard from './StationInfoCard';
import ViewportControls from './ViewportControls';

// 双向轨道 Y 坐标
const DUAL_TRACK_Y = { up: 35, down: 45 };
const STATION_TRACK_Y = { up: 25, down: 55 };

// 贝塞尔过渡参数
const TRANSITION_LENGTH = 500; // 过渡区长度 (m)

/** 生成贝塞尔过渡路径 */
function generateTransitionPath(
  startX: number,
  startY: number,
  endX: number,
  endY: number
): string {
  const midX = (startX + endX) / 2;
  return `M ${startX},${startY} C ${midX},${startY} ${midX},${endY} ${endX},${endY}`;
}

export default function LineDiagram() {
  const { trains, lineLayout } = useSimulationState();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [cardPosition, setCardPosition] = useState({ x: 0, y: 0 });

  const trainPosition = trains[0]?.position;
  const totalLength = lineLayout?.total_length ?? 3200;

  const viewport = useViewport({
    trainPosition,
    totalLength,
    containerRef: svgRef,
    worldHeight: 80,
  });

  const showDetail = viewport.zoom >= 1.5;

  const handleStationClick = useCallback((stationId: string) => {
    if (!lineLayout) return;
    if (selectedStation === stationId) {
      setSelectedStation(null);
      return;
    }

    setSelectedStation(stationId);
    const station = lineLayout.stations.find(s => s.id === stationId);
    if (station && svgRef.current && containerRef.current) {
      const svgRect = svgRef.current.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      const viewW = lineLayout.total_length / viewport.zoom;
      const viewX = parseFloat(viewport.viewBox.split(' ')[0]);
      const screenX = ((station.chainage + station.length / 2 - viewX) / viewW) * svgRect.width;
      const svgOffsetY = svgRect.top - containerRect.top;
      const screenY = svgOffsetY + svgRect.height / 2;
      setCardPosition({
        x: Math.min(Math.max(screenX + 15, 10), containerRect.width - 310),
        y: Math.max(screenY - 160, 10),
      });
    }
  }, [selectedStation, lineLayout, viewport.zoom, viewport.viewBox]);

  if (!lineLayout) {
    return (
      <div className="panel" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-secondary)' }}>加载线路...</span>
      </div>
    );
  }

  const activeStation = selectedStation
    ? lineLayout.stations.find(s => s.id === selectedStation) || null
    : null;

  return (
    <div ref={containerRef} className="panel" style={styles.container}>
      <div style={styles.titleBar}>
        <span className="panel-title" style={{ margin: 0 }}>🚇 线路图</span>
        <ViewportControls
          zoom={viewport.zoom}
          followMode={viewport.followMode}
          onZoomChange={viewport.setZoom}
          onToggleFollow={viewport.toggleFollow}
          onFitAll={viewport.fitAll}
        />
      </div>

      <svg
        ref={svgRef}
        style={styles.svg}
        viewBox={viewport.viewBox}
        preserveAspectRatio="xMidYMid meet"
        onMouseDown={viewport.handleMouseDown}
        onMouseMove={viewport.handleMouseMove}
        onMouseUp={viewport.handleMouseUp}
        onMouseLeave={viewport.handleMouseUp}
      >
        {/* 区间段（站间独立绘制，与贝塞尔过渡平滑衔接） */}
        {lineLayout.stations.slice(0, -1).map((station, idx) => {
          const nextStation = lineLayout.stations[idx + 1];
          const segStart = station.chainage + station.length + TRANSITION_LENGTH;
          const segEnd = nextStation.chainage - TRANSITION_LENGTH;

          // 如果间距不足，跳过绘制
          if (segEnd <= segStart) return null;

          return (
            <g key={`seg-${station.id}-${nextStation.id}`}>
              {/* 上行轨道 */}
              <line
                x1={segStart}
                y1={DUAL_TRACK_Y.up}
                x2={segEnd}
                y2={DUAL_TRACK_Y.up}
                stroke="#e0e0e0"
                strokeWidth={4}
                strokeLinecap="round"
              />
              {/* 下行轨道 */}
              <line
                x1={segStart}
                y1={DUAL_TRACK_Y.down}
                x2={segEnd}
                y2={DUAL_TRACK_Y.down}
                stroke="#e0e0e0"
                strokeWidth={4}
                strokeLinecap="round"
              />
            </g>
          );
        })}

        {/* 车站（双向轨道 + 站台） */}
        {lineLayout.stations.map((station) => (
          <StationNode
            key={station.id}
            station={station}
            showDetail={showDetail}
            selected={selectedStation === station.id}
            onClick={handleStationClick}
            dualTrack={true}
          />
        ))}

        {/* 进出站贝塞尔过渡 */}
        {lineLayout.stations.map((station) => {
          const stationStart = station.chainage;
          const stationEnd = station.chainage + station.length;

          return (
            <g key={`transition-${station.id}`}>
              {/* 进站过渡（区间 → 车站） */}
              <path
                d={generateTransitionPath(
                  stationStart - TRANSITION_LENGTH, DUAL_TRACK_Y.up,
                  stationStart, STATION_TRACK_Y.up
                )}
                stroke="#e0e0e0"
                strokeWidth={4}
                fill="none"
                strokeLinecap="round"
              />
              <path
                d={generateTransitionPath(
                  stationStart - TRANSITION_LENGTH, DUAL_TRACK_Y.down,
                  stationStart, STATION_TRACK_Y.down
                )}
                stroke="#e0e0e0"
                strokeWidth={4}
                fill="none"
                strokeLinecap="round"
              />

              {/* 出站过渡（车站 → 区间） */}
              <path
                d={generateTransitionPath(
                  stationEnd, STATION_TRACK_Y.up,
                  stationEnd + TRANSITION_LENGTH, DUAL_TRACK_Y.up
                )}
                stroke="#e0e0e0"
                strokeWidth={4}
                fill="none"
                strokeLinecap="round"
              />
              <path
                d={generateTransitionPath(
                  stationEnd, STATION_TRACK_Y.down,
                  stationEnd + TRANSITION_LENGTH, DUAL_TRACK_Y.down
                )}
                stroke="#e0e0e0"
                strokeWidth={4}
                fill="none"
                strokeLinecap="round"
              />
            </g>
          );
        })}

        {/* 列车标记（根据方向选择轨道） */}
        {trains.map((train) => (
          <TrainMarker
            key={train.id}
            train={train}
            direction="up" // TODO: 从 train 对象获取 direction
          />
        ))}
      </svg>

      {activeStation && (
        <StationInfoCard
          station={activeStation}
          position={cardPosition}
          onClose={() => setSelectedStation(null)}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    height: '100%',
    overflow: 'visible',
  },
  titleBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 8px',
    height: '30px',
    flexShrink: 0,
  },
  svg: {
    width: '100%',
    height: 'calc(100% - 30px)',
    cursor: 'grab',
    userSelect: 'none',
  },
};
