/**
 * LineDiagram — 交互式线路图主容器
 * 组装 SVG 画布、车站/区间/列车子组件、视口控制栏、信息卡片
 *
 * 交互:
 * - 点击车站 → 弹出车站详细轨道构造和信息卡片
 * - 拖拽 → 仅水平方向
 * - 缩放 → 滚轮/滑块控制，zoom >= 1.5 时显示站内股道详情
 */
import { useRef, useState, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useViewport } from '../../../hooks/useViewport';
import { mockLineData } from '../../../data/mockLineData';
import { useMockTrain } from '../../../data/mockTrainData';
import type { LineLayout } from '../../../types/simulation';
import TrackSegment from './TrackSegment';
import StationNode from './StationNode';
import TrainMarker from './TrainMarker';
import StationInfoCard from './StationInfoCard';
import ViewportControls from './ViewportControls';

const MAIN_TRACK_Y = 40;

export default function LineDiagram() {
  const { trains } = useSimulationState();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [lineLayout] = useState<LineLayout>(mockLineData);
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [cardPosition, setCardPosition] = useState({ x: 0, y: 0 });

  // Mock 列车 (后端就绪后替换)
  const mockTrain = useMockTrain();
  const displayTrains = trains.length > 0 ? trains : [mockTrain];
  const trainPosition = displayTrains[0]?.position;

  const viewport = useViewport({
    trainPosition,
    totalLength: lineLayout.total_length,
    containerRef: svgRef,
    worldHeight: 80,
  });

  // 缩放 >= 1.5 时显示所有车站的股道详情
  const showDetail = viewport.zoom >= 1.5;

  // 车站点击: 弹出信息卡片 (不缩放)
  const handleStationClick = useCallback((stationId: string) => {
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
      // 车站中心 X (屏幕坐标，相对于容器)
      const screenX = ((station.chainage + station.length / 2 - viewX) / viewW) * svgRect.width;
      // 车站中心 Y (正线在 SVG 垂直居中处)
      const svgOffsetY = svgRect.top - containerRect.top;
      const screenY = svgOffsetY + svgRect.height / 2;
      // 卡片宽 300, 高约 320; 以点击点为中心，向右偏移避免遮挡
      setCardPosition({
        x: Math.min(Math.max(screenX + 15, 10), containerRect.width - 310),
        y: Math.max(screenY - 160, 10),
      });
    }
  }, [selectedStation, lineLayout, viewport.zoom, viewport.viewBox]);

  const activeStation = selectedStation
    ? lineLayout.stations.find(s => s.id === selectedStation) || null
    : null;

  return (
    <div ref={containerRef} className="panel" style={styles.container}>
      {/* 标题行: 标题 + 控制栏同行 */}
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

      {/* SVG 画布 */}
      <svg
        ref={svgRef}
        style={styles.svg}
        viewBox={viewport.viewBox}
        preserveAspectRatio="none"
        onMouseDown={viewport.handleMouseDown}
        onMouseMove={viewport.handleMouseMove}
        onMouseUp={viewport.handleMouseUp}
        onMouseLeave={viewport.handleMouseUp}
      >
        {/* 区间轨道电路 */}
        {lineLayout.segments.map((seg) => (
          <TrackSegment
            key={`${seg.start_chainage}-${seg.end_chainage}`}
            segment={seg}
            y={MAIN_TRACK_Y}
          />
        ))}

        {/* 车站 */}
        {lineLayout.stations.map((station) => (
          <StationNode
            key={station.id}
            station={station}
            showDetail={showDetail}
            selected={selectedStation === station.id}
            onClick={handleStationClick}
          />
        ))}

        {/* 列车 */}
        {displayTrains.map((train) => (
          <TrainMarker key={train.id} train={train} trackY={MAIN_TRACK_Y} />
        ))}
      </svg>

      {/* 车站信息卡片 (仅点击选中时) */}
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
