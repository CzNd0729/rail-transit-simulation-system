/**
 * EnergyChart — 能耗累计图（UI-VHC-05）
 * 牵引能耗 / 再生制动电量累计曲线（kWh）
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory, useChartFollowClock } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS, xAxisSplitLineForRunState } from '../../../utils/vehicleChart';
import { downsample } from '../../../utils/downsample';
import React from 'react';

const EnergyChart = React.memo(function EnergyChart() {
  const { clock, chartVersion, runState } = useSimulationState();
  const chartHistory = useActiveChartHistory();
  const followClock = useChartFollowClock();

  const option = useMemo((): EChartsOption => ({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
    legend: {
      data: ['牵引能耗', '再生电量'],
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 50, right: 20, top: 28, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      min: 0,
      max: chartHistory.tractionEnergyTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.tractionEnergyTime.at(-1)?.[0], 600, followClock)
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      splitLine: xAxisSplitLineForRunState(runState),
    },
    yAxis: {
      type: 'value' as const,
      name: '能量 (kWh)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleValueAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '牵引能耗',
        type: 'line',
        showSymbol: false,
        data: downsample(chartHistory.tractionEnergyTime, 800),
        lineStyle: { color: '#ff4d4f', width: 2 },
        itemStyle: { color: '#ff4d4f' },
      },
      {
        name: '再生电量',
        type: 'line',
        showSymbol: false,
        data: downsample(chartHistory.regenEnergyTime, 800),
        lineStyle: { color: '#52c41a', width: 2 },
        itemStyle: { color: '#52c41a' },
      },
    ],
  }), [chartHistory.tractionEnergyTime, chartHistory.regenEnergyTime, clock.elapsed, chartVersion, followClock, runState]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">🔋 能耗累计</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
});

export default EnergyChart;
