/**
 * EnergyChart — 能耗累计图（UI-VHC-05）
 * 牵引能耗 / 再生制动电量累计曲线（kWh）
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip } from '../../../utils/format';

export default function EnergyChart() {
  const { clock } = useSimulationState();
  const chartHistory = useActiveChartHistory();

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(2) },
    legend: {
      data: ['牵引能耗', '再生电量'],
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 50, right: 20, top: 28, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      max: chartHistory.tractionEnergyTime.length > 0
        ? Math.max(clock.elapsed + 10, chartHistory.tractionEnergyTime.at(-1)?.[0] ?? 0 + 10)
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '能量 (kWh)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '牵引能耗',
        type: 'line',
        showSymbol: false,
        data: chartHistory.tractionEnergyTime,
        lineStyle: { color: '#ff4d4f', width: 2 },
        itemStyle: { color: '#ff4d4f' },
      },
      {
        name: '再生电量',
        type: 'line',
        showSymbol: false,
        data: chartHistory.regenEnergyTime,
        lineStyle: { color: '#52c41a', width: 2 },
        itemStyle: { color: '#52c41a' },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🔋 能耗累计</div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
