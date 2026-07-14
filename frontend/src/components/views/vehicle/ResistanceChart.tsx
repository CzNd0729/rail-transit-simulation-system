/**
 * ResistanceChart — 阻力图（UI-VHC-04）
 * 默认总阻力折线；可切换四分项堆叠（Davis / 坡度 / 弯道 / 隧道）
 */
import { useMemo, useState, type CSSProperties } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory, useChartFollowClock } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS, xAxisSplitLineForRunState } from '../../../utils/vehicleChart';
import { downsample } from '../../../utils/downsample';
import React from 'react';

function hasBreakdownData(history: ReturnType<typeof useActiveChartHistory>): boolean {
  const series = [
    history.davisResistanceTime,
    history.gradientResistanceTime,
    history.curveResistanceTime,
    history.tunnelResistanceTime,
  ];
  return series.some((s) => s.some(([, v]) => Math.abs(v) > 0));
}

const ResistanceChart = React.memo(function ResistanceChart() {
  const { clock, chartVersion, runState } = useSimulationState();
  const chartHistory = useActiveChartHistory();
  const followClock = useChartFollowClock();
  const breakdownAvailable = hasBreakdownData(chartHistory);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const stacked = showBreakdown && breakdownAvailable;

  const option = useMemo((): EChartsOption => {
    const xMax = chartHistory.resistanceTime.length > 0
      ? stableVehicleTimeMax(clock.elapsed, chartHistory.resistanceTime.at(-1)?.[0], 600, followClock)
      : 600;

    const stackedSeries = [
      { name: 'Davis', data: downsample(chartHistory.davisResistanceTime, 800), color: '#1890ff' },
      { name: '坡度', data: downsample(chartHistory.gradientResistanceTime, 800), color: '#52c41a' },
      { name: '弯道', data: downsample(chartHistory.curveResistanceTime, 800), color: '#faad14' },
      { name: '隧道', data: downsample(chartHistory.tunnelResistanceTime, 800), color: '#9254de' },
    ];

    return {
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' as const, formatter: axisTooltip(VEHICLE_CHART_DECIMALS) },
      legend: stacked
        ? {
            data: stackedSeries.map((s) => s.name),
            textStyle: { color: '#a0a0a0', fontSize: 11 },
            top: 0,
          }
        : undefined,
      grid: { left: 50, right: 20, top: stacked ? 28 : 20, bottom: 40 },
      xAxis: {
        type: 'value' as const,
        name: '时间 (s)',
        min: 0,
        max: xMax,
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: vehicleTimeAxisLabel(),
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        splitLine: xAxisSplitLineForRunState(runState),
      },
      yAxis: {
        type: 'value' as const,
        name: '阻力 (kN)',
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: vehicleValueAxisLabel(),
        axisLine: { lineStyle: { color: '#2a2a4a' } },
      },
      series: stacked
        ? stackedSeries.map((s) => ({
            name: s.name,
            type: 'line' as const,
            stack: 'resistance',
            showSymbol: false,
            data: s.data,
            lineStyle: { color: s.color, width: 1 },
            itemStyle: { color: s.color },
            areaStyle: { color: s.color, opacity: 0.35 },
          }))
        : [{
            name: '总阻力',
            type: 'line' as const,
            showSymbol: false,
            data: downsample(chartHistory.resistanceTime, 800),
            lineStyle: { color: '#fa8c16', width: 2 },
            itemStyle: { color: '#fa8c16' },
            areaStyle: { color: 'rgba(250, 140, 22, 0.08)' },
          }],
    };
  }, [
    chartHistory.resistanceTime,
    chartHistory.davisResistanceTime,
    chartHistory.gradientResistanceTime,
    chartHistory.curveResistanceTime,
    chartHistory.tunnelResistanceTime,
    clock.elapsed,
    stacked,
    chartVersion,
    followClock,
    runState,
  ]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={styles.titleBar}>
        <div className="panel-title" style={styles.title}>
          {stacked ? '📊 阻力分解' : '📊 总阻力'}
        </div>
        <button
          type="button"
          className="btn"
          style={styles.toggleBtn}
          disabled={!breakdownAvailable}
          title={breakdownAvailable ? undefined : '暂无四分项数据'}
          onClick={() => setShowBreakdown((v) => !v)}
        >
          {stacked ? '总阻力' : '四分项'}
        </button>
      </div>
      <div key={stacked ? 'stacked' : 'total'} style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
});

export default ResistanceChart;

const styles: Record<string, CSSProperties> = {
  titleBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
    paddingBottom: 6,
    borderBottom: '1px solid var(--border-color)',
  },
  title: {
    margin: 0,
    padding: 0,
    borderBottom: 'none',
  },
  toggleBtn: {
    padding: '2px 8px',
    fontSize: 11,
    minWidth: 52,
  },
};
