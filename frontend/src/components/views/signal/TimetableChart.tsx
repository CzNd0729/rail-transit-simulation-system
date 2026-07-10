/**
 * TimetableChart — 运行图（时间-距离图）
 * 基于《迭代二需求文档》UI-SIG-03（单列车简化版）
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import { axisTooltip } from '../../../utils/format';

export default function TimetableChart() {
  const { chartHistory, clock, lineLayout } = useSimulationState();
  const stations = lineLayout?.stations ?? mockLineData.stations;
  const maxPos = lineLayout?.total_length ?? mockLineData.total_length;

  const xMax = chartHistory.positionTime.length > 0
    ? Math.max(clock.elapsed + 10, chartHistory.positionTime[chartHistory.positionTime.length - 1][0] + 10)
    : Math.max(clock.elapsed + 10, 60);

  const stationMarkLines = stations.map((st) => ({
    yAxis: st.chainage,
    label: {
      formatter: st.name,
      color: '#a0a0a0',
      fontSize: 10,
    },
    lineStyle: { color: '#3a3a5a', type: 'dashed' as const },
  }));

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(1) },
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: xMax,
    },
    yAxis: {
      type: 'value' as const,
      name: '位置 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: maxPos,
    },
    series: [
      {
        name: '运行轨迹',
        type: 'line',
        smooth: true,
        data: chartHistory.positionTime,
        lineStyle: { color: '#1890ff', width: 2 },
        itemStyle: { color: '#1890ff' },
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: stationMarkLines,
        },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📅 运行图</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
