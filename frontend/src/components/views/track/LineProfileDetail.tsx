/**
 * LineProfileDetail — 线路综合剖面图
 * 图表：坡度 + 限速 + 车站标注 + 隧道遮罩
 * 交互：复用 useViewport，支持拖拽平移 / 滚轮缩放 / 跟随列车（同综合视图线路图）
 */
import { useMemo, useRef, useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData, mockSegmentParams } from '../../../data/mockLineData';
import { useViewport, parseViewBox } from '../../../hooks/useViewport';
import ViewportControls from '../overview/ViewportControls';
import { toStepData } from '../../../utils/profileChart';

const PROFILE_WINDOW_METERS = 4500;

function computeInitialZoom(totalLength: number): number {
  if (totalLength <= 0) return 1;
  return Math.min(5, Math.max(2, totalLength / PROFILE_WINDOW_METERS));
}

export default function LineProfileDetail() {
  const { trains, lineLayout, profileSegments } = useSimulationState();

  const stations = lineLayout?.stations ?? mockLineData.stations;
  const total_length = lineLayout?.total_length ?? mockLineData.total_length;
  const segments = profileSegments ?? mockSegmentParams;
  const chartContainerRef = useRef<HTMLDivElement>(null);

  const animRef = useRef<number>(0);
  const [displayPos, setDisplayPos] = useState(0);
  const targetPos = trains[0]?.position ?? 0;

  useEffect(() => {
    let running = true;
    const step = () => {
      if (!running) return;
      setDisplayPos((prev) => {
        const diff = targetPos - prev;
        if (Math.abs(diff) < 0.5) return targetPos;
        return prev + diff * 0.3;
      });
      animRef.current = requestAnimationFrame(step);
    };
    animRef.current = requestAnimationFrame(step);
    return () => {
      running = false;
      cancelAnimationFrame(animRef.current);
    };
  }, [targetPos]);

  const initialZoom = useMemo(() => computeInitialZoom(total_length), [total_length]);

  const viewport = useViewport({
    trainPosition: displayPos,
    totalLength: total_length,
    containerRef: chartContainerRef,
    initialZoom,
    initialFollowMode: false,
    clampPan: true,
  });

  const lastLengthRef = useRef(0);
  useEffect(() => {
    if (total_length <= 0 || lastLengthRef.current === total_length) return;
    lastLengthRef.current = total_length;
    viewport.focusPosition(displayPos, computeInitialZoom(total_length), 0);
  }, [total_length, displayPos, viewport.focusPosition]);

  const { panX, viewW } = parseViewBox(viewport.viewBox);
  const xMax = panX + viewW;
  const trainInView = displayPos >= panX && displayPos <= xMax;
  const trainScreenRatio = viewW > 0 ? (displayPos - panX) / viewW : 0;

  const gradientData = useMemo(() => toStepData(segments, 'gradient'), [segments]);
  const speedLimitData = useMemo(() => toStepData(segments, 'speed_limit'), [segments]);

  const stationMarkLines = useMemo(
    () =>
      stations.map((s) => ({
        xAxis: s.chainage,
        label: { formatter: s.name, color: '#e0e0e0', fontSize: 10 },
        lineStyle: { color: '#555', type: 'dashed' as const, width: 1 },
      })),
    [stations],
  );

  const tunnelAreas = useMemo(
    () =>
      segments
        .filter((s) => s.is_tunnel)
        .map((s) => [
          { xAxis: s.start_chainage, itemStyle: { color: 'rgba(128,128,128,0.15)' } },
          { xAxis: s.end_chainage },
        ]),
    [segments],
  );

  const option = useMemo(
    () => ({
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' as const },
      legend: {
        data: ['坡度 (‰)', '限速 (km/h)'],
        textStyle: { color: '#a0a0a0', fontSize: 11 },
        top: 0,
      },
      grid: { left: 55, right: 55, top: 36, bottom: 32 },
      xAxis: {
        type: 'value' as const,
        name: '公里标 (m)',
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        min: panX,
        max: xMax,
      },
      yAxis: [
        {
          type: 'value' as const,
          name: '坡度 (‰)',
          nameTextStyle: { color: '#1890ff' },
          axisLabel: { color: '#a0a0a0' },
          axisLine: { lineStyle: { color: '#1890ff' } },
          splitLine: { lineStyle: { color: '#1a1a2e' } },
        },
        {
          type: 'value' as const,
          name: '限速 (km/h)',
          nameTextStyle: { color: '#ff4d4f' },
          axisLabel: { color: '#a0a0a0' },
          axisLine: { lineStyle: { color: '#ff4d4f' } },
          splitLine: { show: false },
          min: 0,
          max: 100,
        },
      ],
      series: [
        {
          name: '坡度 (‰)',
          type: 'line',
          yAxisIndex: 0,
          data: gradientData,
          areaStyle: { color: 'rgba(24, 144, 255, 0.12)' },
          lineStyle: { color: '#1890ff', width: 1.5 },
          itemStyle: { color: '#1890ff' },
          showSymbol: false,
          markLine: {
            silent: true,
            symbol: 'none',
            data: stationMarkLines,
          },
          markArea: {
            silent: true,
            data: tunnelAreas,
          },
        },
        {
          name: '限速 (km/h)',
          type: 'line',
          yAxisIndex: 1,
          data: speedLimitData,
          lineStyle: { color: '#ff4d4f', type: 'dashed' as const, width: 1.5 },
          itemStyle: { color: '#ff4d4f' },
          showSymbol: false,
        },
      ],
    }),
    [gradientData, speedLimitData, stationMarkLines, tunnelAreas, panX, xMax],
  );

  const trainSpeed = trains[0]?.speed ?? 0;

  const visibleStations = useMemo(
    () => stations.filter((s) => s.chainage >= panX - 200 && s.chainage <= xMax + 200),
    [stations, panX, xMax],
  );

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={styles.titleBar}>
        <span className="panel-title" style={{ margin: 0 }}>🏔️ 线路综合剖面图</span>
        <ViewportControls
          zoom={viewport.zoom}
          followMode={viewport.followMode}
          onZoomChange={viewport.setZoom}
          onToggleFollow={viewport.toggleFollow}
          onFitAll={viewport.fitAll}
        />
      </div>

      <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div
          ref={chartContainerRef}
          style={styles.chartArea}
          onMouseDown={viewport.handleMouseDown}
          onMouseMove={viewport.handleMouseMove}
          onMouseUp={viewport.handleMouseUp}
          onMouseLeave={viewport.handleMouseUp}
        >
          <ReactECharts option={option} style={{ height: '100%', pointerEvents: 'none' }} notMerge />
        </div>

        <div style={styles.strip}>
          <span style={styles.stripSpeed}>🚇 {trainSpeed.toFixed(0)} km/h</span>
          <svg
            viewBox={`${panX} 0 ${viewW} 28`}
            preserveAspectRatio="none"
            style={{ flex: 1, height: '100%' }}
          >
            {visibleStations.map((s) => (
              <line key={s.id} x1={s.chainage} y1={4} x2={s.chainage} y2={14} stroke="#555" strokeWidth={1} />
            ))}
            {visibleStations.map((s) => (
              <text key={`t-${s.id}`} x={s.chainage} y={27} textAnchor="middle" fontSize={8} fill="#888">
                {s.name}
              </text>
            ))}
          </svg>
          <span style={styles.stripPos}>{displayPos.toFixed(0)} m</span>
        </div>

        {trainInView && (
          <div
            style={{
              position: 'absolute',
              top: 30,
              left: 55,
              right: 55,
              bottom: 32,
              pointerEvents: 'none',
            }}
          >
            <svg
              style={{ width: '100%', height: '100%' }}
              viewBox={`${panX} 0 ${viewW} 100`}
              preserveAspectRatio="none"
            >
              <line
                x1={displayPos}
                y1={0}
                x2={displayPos}
                y2={88}
                stroke="#ff4d4f"
                strokeWidth={10}
                opacity={0.75}
              />
            </svg>
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: `${trainScreenRatio * 100}%`,
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: '#ff4d4f',
                transform: 'translateX(-50%)',
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  titleBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 8px',
    height: '30px',
    flexShrink: 0,
  },
  chartArea: {
    flex: 1,
    minHeight: 0,
    cursor: 'grab',
    userSelect: 'none',
  },
  strip: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '0 4px',
    borderTop: '1px solid var(--border-color)',
    flexShrink: 0,
    height: '32px',
  },
  stripSpeed: {
    fontSize: '10px',
    color: '#ff4d4f',
    fontWeight: 600,
    minWidth: '60px',
    flexShrink: 0,
    marginTop: '8px',
  },
  stripPos: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
    minWidth: '55px',
    textAlign: 'right',
    flexShrink: 0,
  },
};
