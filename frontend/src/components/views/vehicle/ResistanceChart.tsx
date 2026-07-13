/**
 * ResistanceChart — 总阻力-时间曲线（UI-VHC-04 降级版）
 * 后端未推送四分项时展示 totalResistance 时序；完整分解留迭代三
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS } from '../../../utils/vehicleChart';

export default function ResistanceChart() {
  const { clock } = useSimulationState();
  const chartHistory = useActiveChartHistory();

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      max: chartHistory.resistanceTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.resistanceTime.at(-1)?.[0])
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '总阻力 (kN)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleValueAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '总阻力',
        type: 'line',
        showSymbol: false,
        data: chartHistory.resistanceTime,
        lineStyle: { color: '#fa8c16', width: 2 },
        itemStyle: { color: '#fa8c16' },
        areaStyle: { color: 'rgba(250, 140, 22, 0.08)' },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📊 总阻力-时间</div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
