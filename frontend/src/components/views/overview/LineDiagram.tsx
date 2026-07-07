/**
 * LineDiagram — 交互式线路图主容器
 * 组装 SVG 画布、车站/区间/列车子组件、视口控制栏、信息卡片
 */
import { useRef, useState, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useViewport } from '../../../hooks/useViewport';
import { mockLineData } from '../../../data/mockLineData';
import type { LineLayout } from '../../../types/simulation';
import TrackSegment from './TrackSegment';
import StationNode from './StationNode';
import TrainMarker from './TrainMarker';
import StationInfoCard from './StationInfoCard';
import ViewportControls from './ViewportControls';

export default function LineDiagram() {
  const { trains } = useSimulationState();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 线路数据 (Mock 阶段, 后续从 state.lineLayout 读取)
  const [lineLayout] = useState<LineLayout>(mockLineData);

  // 悬停/选中的车站
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [hoveredStation, setHoveredStation] = useState<string | null>(null);
  const [cardPosition, setCardPosition] = useState({ x: 0, y: 0 });

  // 列车位置 (取第一列列车)
  const trainPosition = trains.length > 0 ? trains[0].position : undefined;

  // 视口管理
  const viewport = useViewport({
    trainPosition,
    totalLength: lineLayout.total_length,
    containerRef: svgRef,
    worldHeight: 80,
  });

  // 判断是否显示站内详情 (缩放 >= 0.8 时显示)
  const showDetail = viewport.zoom >= 0.8;

  // 车站点击
  const handleStationClick = useCallback((stationId: string) => {
    setSelectedStation(prev => prev === stationId ? null : stationId);
    if (svgRef.current && containerRef.current) {
      const svgRect = svgRef.current.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      const station = lineLayout.stations.find(s => s.id === stationId);
      if (station) {
        const viewW = lineLayout.total_length / viewport.zoom;
        const viewX = parseFloat(viewport.viewBox.split(' ')[0]);
        const screenX = ((station.chainage + station.length / 2 - viewX) / viewW) * svgRect.width;
        setCardPosition({
          x: Math.min(Math.max(screenX, 10), containerRect.width - 260),
          y: 10,
        });
      }
    }
  }, [lineLayout, viewport.zoom, viewport.viewBox]);

  const handleStationHover = useCallback((stationId: string) => {
    setHoveredStation(stationId);
  }, []);

  const handleStationLeave = useCallback(() => {
    setHoveredStation(null);
  }, []);

  // 获取显示信息卡片的车站
  const activeStationId = selectedStation || hoveredStation;
  const activeStation = activeStationId
    ? lineLayout.stations.find(s => s.id === activeStationId) || null
    : null;

  // 正线 Y 坐标 (与 StationNode 中 baseY 一致)
  const mainTrackY = 40;

  return (
    <div ref={containerRef} className="panel" style={styles.container}>
      <div className="panel-title">🚇 线路图</div>

      {/* SVG 画布 */}
      <svg
        ref={svgRef}
        style={styles.svg}
        viewBox={viewport.viewBox}
        preserveAspectRatio="none"
        onWheel={viewport.handleWheel}
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
            y={mainTrackY}
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
            onMouseEnter={handleStationHover}
            onMouseLeave={handleStationLeave}
          />
        ))}

        {/* 列车 */}
        {trains.map((train) => (
          <TrainMarker key={train.id} train={train} trackY={mainTrackY} />
        ))}
      </svg>

      {/* 控制栏 */}
      <div style={styles.controlsWrap}>
        <ViewportControls
          zoom={viewport.zoom}
          followMode={viewport.followMode}
          onZoomChange={viewport.setZoom}
          onToggleFollow={viewport.toggleFollow}
          onFitAll={viewport.fitAll}
        />
      </div>

      {/* 车站信息卡片 */}
      {activeStation && (
        <StationInfoCard
          station={activeStation}
          position={cardPosition}
          onClose={() => { setSelectedStation(null); setHoveredStation(null); }}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    height: '100%',
    overflow: 'hidden',
  },
  svg: {
    width: '100%',
    height: 'calc(100% - 30px)',
    cursor: 'grab',
    userSelect: 'none',
  },
  controlsWrap: {
    position: 'absolute',
    bottom: '8px',
    right: '8px',
  },
};
