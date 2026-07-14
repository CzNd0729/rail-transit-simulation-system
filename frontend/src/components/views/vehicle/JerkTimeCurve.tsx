/**
 * JerkTimeCurve — 冲击率-时间曲线
 * 实时绘制 jerk = Δa/Δt；参考线 ±0.75 m/s³（乘客舒适度建议上限）
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS } from '../../../utils/vehicleChart';
import { downsample } from '../../../utils/downsample';
import React from 'react';

const COMFORT_JERK_LIMIT = 0.75;

const JerkTimeCurve = React.memo(function JerkTimeCurve() {
  const { clock, chartVersion } = useSimulationState();
  const chartHistory = useActiveChartHistory();

  const option = useMemo((): EChartsOption => {
    const xMax = chartHistory.jerkTime.length > 0
      ? stableVehicleTimeMax(clock.elapsed, chartHistory.jerkTime.at(-1)?.[0])
      : 600;

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
      grid: { left: 50, right: 60, top: 20, bottom: 40 },
      xAxis: {
        type: 'value' as const,
        name: '时间 (s)',
        max: xMax,
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: vehicleTimeAxisLabel(),
        axisLine: { lineStyle: { color: '#2a2a4a' } },
      },
      yAxis: {
        type: 'value' as const,
        name: '冲击率 (m/s³)',
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: vehicleValueAxisLabel(),
        axisLine: { lineStyle: { color: '#2a2a4a' } },
      },
      series: [
        {
          name: '冲击率',
          type: 'line',
          showSymbol: false,
          data: downsample(chartHistory.jerkTime, 800),
          lineStyle: { color: '#9254de', width: 2 },
          itemStyle: { color: '#9254de' },
          areaStyle: { color: 'rgba(146, 84, 222, 0.08)' },
        },
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
              { name: 'upper', xAxis: xMax, yAxis: COMFORT_JERK_LIMIT, value: COMFORT_JERK_LIMIT },
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
              { name: 'lower', xAxis: xMax, yAxis: -COMFORT_JERK_LIMIT, value: -COMFORT_JERK_LIMIT },
            ],
          },
          silent: true,
        },
      ],
    };
  }, [chartHistory.jerkTime, clock.elapsed, chartVersion]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📊 冲击率-时间曲线</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
});

export default JerkTimeCurve;
