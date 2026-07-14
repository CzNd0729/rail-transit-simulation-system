/**
 * LineProfile — 线路纵断面图
 * 基于《需求文档》UI-VW-01
 */
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { buildProfileSegments } from '../../../data/mvpLineLayout';
import { toStepData } from '../../../utils/profileChart';

export default function LineProfile() {
  const { lineLayout, profileSegments, params } = useSimulationState();
  const segments = profileSegments ?? buildProfileSegments(params.track.gradient);
  const gradientData = toStepData(segments, 'gradient');
  const stations = lineLayout?.stations ?? [];

  const option = useMemo(() => ({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '公里标 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: lineLayout?.total_length ?? 3200,
    },
    yAxis: {
      type: 'value' as const,
      name: '坡度 (‰)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '坡度',
        type: 'line',
        data: gradientData,
        areaStyle: { color: 'rgba(24, 144, 255, 0.15)' },
        lineStyle: { color: '#1890ff' },
        itemStyle: { color: '#1890ff' },
        markPoint: {
          data: stations.map((s) => ({
            name: s.name,
            coord: [s.chainage, segments.find(
              (seg) => s.chainage >= seg.start_chainage && s.chainage <= seg.end_chainage,
            )?.gradient ?? 0],
            symbol: 'pin',
            symbolSize: 30,
          })),
          label: { color: '#fff', fontSize: 10 },
        },
      },
    ],
  }), [gradientData, stations, segments, lineLayout?.total_length]);

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📐 线路纵断面</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
