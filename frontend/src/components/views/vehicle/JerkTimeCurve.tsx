/**
 * JerkTimeCurve — 冲击率-时间曲线
 * 实时绘制 jerk = Δa/Δt；参考线 ±0.75 m/s³（乘客舒适度建议上限）
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { axisTooltip } from '../../../utils/format';

const COMFORT_JERK_LIMIT = 0.75;

export default function JerkTimeCurve() {
  const { chartHistory, clock } = useSimulationState();

  const xMax = chartHistory.jerkTime.length > 0
    ? Math.max(clock.elapsed + 10, chartHistory.jerkTime[chartHistory.jerkTime.length - 1][0] + 10)
    : 600;

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(2) },
    grid: { left: 50, right: 60, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      max: xMax,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: {
        color: '#a0a0a0',
        formatter: (value: number) => value.toFixed(2),
      },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '冲击率 (m/s³)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '冲击率',
        type: 'line',
        showSymbol: false,
        data: chartHistory.jerkTime,
        lineStyle: { color: '#9254de', width: 2 },
        itemStyle: { color: '#9254de' },
        areaStyle: { color: 'rgba(146, 84, 222, 0.08)' },
      },
      // 静态参考线：使用独立 series，避免随主数据重绘闪烁
      {
        name: `+${COMFORT_JERK_LIMIT}`,
        type: 'line',
        showSymbol: false,
        lineStyle: { type: 'dashed', color: '#faad14', width: 1 },
        itemStyle: { color: '#faad14' },
        data: [[0, COMFORT_JERK_LIMIT], [xMax, COMFORT_JERK_LIMIT]],
        markPoint: {
          symbol: 'rect',
          symbolSize: [0, 0],
          label: {
            show: true,
            position: 'right',
            formatter: `+${COMFORT_JERK_LIMIT}`,
            color: '#faad14',
            fontSize: 10,
            offset: [0, 0],
          },
          data: [
            { xAxis: xMax, yAxis: COMFORT_JERK_LIMIT, value: COMFORT_JERK_LIMIT },
          ],
        },
        silent: true,
      },
      {
        name: `-${COMFORT_JERK_LIMIT}`,
        type: 'line',
        showSymbol: false,
        lineStyle: { type: 'dashed', color: '#faad14', width: 1 },
        itemStyle: { color: '#faad14' },
        data: [[0, -COMFORT_JERK_LIMIT], [xMax, -COMFORT_JERK_LIMIT]],
        markPoint: {
          symbol: 'rect',
          symbolSize: [0, 0],
          label: {
            show: true,
            position: 'right',
            formatter: `-${COMFORT_JERK_LIMIT}`,
            color: '#faad14',
            fontSize: 10,
            offset: [0, 0],
          },
          data: [
            { xAxis: xMax, yAxis: -COMFORT_JERK_LIMIT, value: -COMFORT_JERK_LIMIT },
          ],
        },
        silent: true,
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📊 冲击率-时间曲线</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge={true}
      />
    </div>
  );
}
