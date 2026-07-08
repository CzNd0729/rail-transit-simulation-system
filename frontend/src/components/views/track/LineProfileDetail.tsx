/**
 * LineProfileDetail — 线路综合剖面图
 * 图表：坡度 + 限速 + 车站标注 + 隧道遮罩（纯静态）
 * 覆盖层：列车红线（图表范围内）
 * 底部：车站条 + 列车图标
 */
import { useMemo, useRef, useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData, mockSegmentParams } from '../../../data/mockLineData';

function toStepData(
  segments: Array<{ start_chainage: number; end_chainage: number; gradient: number; speed_limit: number }>,
  field: 'gradient' | 'speed_limit'
): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    result.push([seg.start_chainage, seg[field]]);
    result.push([seg.end_chainage, seg[field]]);
  }
  return result;
}

export default function LineProfileDetail() {
  const { trains } = useSimulationState();
  const { stations, total_length } = mockLineData;
  const containerRef = useRef<HTMLDivElement>(null);

  const animRef = useRef<number>(0);
  const [displayPos, setDisplayPos] = useState(0);
  const targetPos = trains[0]?.position ?? 0;

  useEffect(() => {
    let running = true;
    const step = () => {
      if (!running) return;
      setDisplayPos(prev => {
        const diff = targetPos - prev;
        if (Math.abs(diff) < 0.5) return targetPos;
        return prev + diff * 0.3;
      });
      animRef.current = requestAnimationFrame(step);
    };
    animRef.current = requestAnimationFrame(step);
    return () => { running = false; cancelAnimationFrame(animRef.current); };
  }, [targetPos]);

  const gradientData = useMemo(() => toStepData(mockSegmentParams, 'gradient'), []);
  const speedLimitData = useMemo(() => toStepData(mockSegmentParams, 'speed_limit'), []);

  const stationMarkLines = useMemo(() =>
    stations.map((s) => ({
      xAxis: s.chainage,
      label: { formatter: s.name, color: '#e0e0e0', fontSize: 10 },
      lineStyle: { color: '#555', type: 'dashed' as const, width: 1 },
    })), [stations]
  );

  const tunnelAreas = useMemo(() =>
    mockSegmentParams
      .filter((s) => s.is_tunnel)
      .map((s) => [
        { xAxis: s.start_chainage, itemStyle: { color: 'rgba(128,128,128,0.15)' } },
        { xAxis: s.end_chainage },
      ]), []
  );

  const option = useMemo(() => ({
    backgroundColor: 'transparent',
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
      min: 0,
      max: total_length,
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
  }), [gradientData, speedLimitData, stationMarkLines, tunnelAreas, total_length]);

  const trainSpeed = trains[0]?.speed ?? 0;

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">🏔️ 线路综合剖面图</div>

      {/* 图表 + 底部条 + 覆盖层 的容器，限定了覆盖层范围 */}
      <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        {/* 图表区 */}
        <div ref={containerRef} style={{ flex: 1, minHeight: 0 }}>
          <ReactECharts option={option} style={{ height: '100%' }} notMerge={false} />
        </div>

        {/* 底部车站条 */}
        <div style={styles.strip}>
          <span style={styles.stripSpeed}>🚇 {trainSpeed.toFixed(0)} km/h</span>
          <svg
            viewBox={`0 0 ${total_length} 28`}
            preserveAspectRatio="none"
            style={{ flex: 1, height: '100%' }}
          >
            {stations.map((s) => (
              <line key={s.id} x1={s.chainage} y1={4} x2={s.chainage} y2={14} stroke="#555" strokeWidth={1} />
            ))}
            {stations.map((s) => (
              <text key={`t-${s.id}`} x={s.chainage} y={27} textAnchor="middle" fontSize={8} fill="#888">
                {s.name}
              </text>
            ))}
          </svg>
          <span style={styles.stripPos}>{displayPos.toFixed(0)} m</span>
        </div>

        {/* 覆盖层容器：left/right 匹配 ECharts grid，使 X=0 对齐横轴刻度 0 */}
        <div style={{
          position: 'absolute',
          top: 0, left: 55, right: 55,
          height: '100%',
          pointerEvents: 'none',
        }}>
          <svg
            style={{ width: '100%', height: '100%' }}
            viewBox={`0 0 ${total_length} 100`}
            preserveAspectRatio="none"
          >
            <line
              x1={displayPos} y1={0}
              x2={displayPos} y2={88}
              stroke="#ff4d4f" strokeWidth={10}
              opacity={0.75}
            />
          </svg>

          {/* 红点：同容器的 left 百分比，与 SVG X 对齐 */}
          <div style={{
            position: 'absolute',
            bottom: '30px',
            left: `${(displayPos / total_length) * 100}%`,
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: '#ff4d4f',
            transform: 'translateX(-50%)',
          }} />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
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
