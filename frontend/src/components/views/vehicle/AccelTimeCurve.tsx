/**
 * AccelTimeCurve — 加速度-时间曲线
 * 基于《需求文档》UI-VHC-02
 * 实时绘制加速度曲线
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS } from '../../../utils/vehicleChart';

export default function AccelTimeCurve() {
  const { clock } = useSimulationState();
  const chartHistory = useActiveChartHistory();

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      max: chartHistory.accelTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.accelTime.at(-1)?.[0])
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '加速度 (m/s²)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleValueAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '加速度',
        type: 'line',
        showSymbol: false,
        data: chartHistory.accelTime,
        lineStyle: { color: '#52c41a', width: 2 },
        itemStyle: { color: '#52c41a' },
        areaStyle: { color: 'rgba(82, 196, 26, 0.08)' },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📉 加速度-时间曲线</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
