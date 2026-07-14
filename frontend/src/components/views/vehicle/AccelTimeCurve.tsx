/**
 * AccelTimeCurve — 加速度-时间曲线
 * 基于《需求文档》UI-VHC-02
 * 实时绘制加速度曲线
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory, useChartFollowClock } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS, xAxisSplitLineForRunState } from '../../../utils/vehicleChart';
import React from 'react';

const AccelTimeCurve = React.memo(function AccelTimeCurve() {
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
      max: chartHistory.accelTime.length > 0
        ? stableVehicleTimeMax(clock.elapsed, chartHistory.accelTime.at(-1)?.[0], 600, followClock)
        : 600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: vehicleTimeAxisLabel(),
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      splitLine: xAxisSplitLineForRunState(runState),
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
        sampling: 'lttb',
        data: chartHistory.accelTime,
        lineStyle: { color: '#52c41a', width: 2 },
        itemStyle: { color: '#52c41a' },
        areaStyle: { color: 'rgba(82, 196, 26, 0.08)' },
      },
    ],
  }), [chartHistory.accelTime, clock.elapsed, chartVersion, followClock, runState]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📉 加速度-时间曲线</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
});

export default AccelTimeCurve;
