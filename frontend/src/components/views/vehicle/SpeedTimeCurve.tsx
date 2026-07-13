/**
 * SpeedTimeCurve — 速度-时间曲线
 * 基于《需求文档》UI-VHC-01
 * 实时绘制速度随时间变化
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS } from '../../../utils/vehicleChart';

export default function SpeedTimeCurve() {
  const { clock } = useSimulationState();
  const chartHistory = useActiveChartHistory();

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      max: chartHistory.speedTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.speedTime.at(-1)?.[0])
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '速度 (km/h)',
      max: 100,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleValueAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '速度',
        type: 'line',
        showSymbol: false,
        data: chartHistory.speedTime,
        lineStyle: { color: '#1890ff', width: 2 },
        itemStyle: { color: '#1890ff' },
        areaStyle: { color: 'rgba(24, 144, 255, 0.08)' },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📈 速度-时间曲线</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
