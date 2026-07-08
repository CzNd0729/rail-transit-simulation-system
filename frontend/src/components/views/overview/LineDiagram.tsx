/**
 * LineDiagram — 交互式线路图主容器
 */
import { useRef, useState, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useViewport } from '../../../hooks/useViewport';
import TrackSegment from './TrackSegment';
import StationNode from './StationNode';
import TrainMarker from './TrainMarker';
import StationInfoCard from './StationInfoCard';
import ViewportControls from './ViewportControls';

const MAIN_TRACK_Y = 40;

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
        preserveAspectRatio="none"
        onWheel={viewport.handleWheel}
        onMouseDown={viewport.handleMouseDown}
        onMouseMove={viewport.handleMouseMove}
        onMouseUp={viewport.handleMouseUp}
        onMouseLeave={viewport.handleMouseUp}
      >
        {lineLayout.segments.map((seg) => (
          <TrackSegment
            key={`${seg.start_chainage}-${seg.end_chainage}`}
            segment={seg}
            y={MAIN_TRACK_Y}
          />
        ))}

        {lineLayout.stations.map((station) => (
          <StationNode
            key={station.id}
            station={station}
            showDetail={showDetail}
            selected={selectedStation === station.id}
            onClick={handleStationClick}
          />
        ))}

        {trains.map((train) => (
          <TrainMarker key={train.id} train={train} trackY={MAIN_TRACK_Y} />
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
