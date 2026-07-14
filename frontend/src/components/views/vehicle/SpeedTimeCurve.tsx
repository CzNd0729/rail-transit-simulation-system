/**
 * SpeedTimeCurve — 速度-时间曲线
 * 基于《需求文档》UI-VHC-01
 * 实时绘制速度随时间变化
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory, useChartFollowClock } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS, xAxisSplitLineForRunState } from '../../../utils/vehicleChart';
import React from 'react';

const SpeedTimeCurve = React.memo(function SpeedTimeCurve() {
  const { clock, chartVersion, runState } = useSimulationState();
  const chartHistory = useActiveChartHistory();
  const followClock = useChartFollowClock();

  const option = useMemo((): EChartsOption => ({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '时间 (s)',
      min: 0,
      max: chartHistory.speedTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.speedTime.at(-1)?.[0], 600, followClock)
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      splitLine: xAxisSplitLineForRunState(runState),
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
        sampling: 'lttb',
        data: chartHistory.speedTime,
        lineStyle: { color: '#1890ff', width: 2 },
        itemStyle: { color: '#1890ff' },
        areaStyle: { color: 'rgba(24, 144, 255, 0.08)' },
      },
    ],
  }), [chartHistory.speedTime, clock.elapsed, chartVersion, followClock, runState]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📈 速度-时间曲线</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
});

export default SpeedTimeCurve;
