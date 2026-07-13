/**
 * ResistanceChart — 阻力分解图（UI-VHC-04）
 * 堆叠面积图展示 Davis / 坡度 / 弯道 / 隧道四分项；无四分项时降级总阻力折线
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip, stableVehicleTimeMax } from '../../../utils/format';
import { vehicleTimeAxisLabel, vehicleValueAxisLabel, VEHICLE_CHART_DECIMALS } from '../../../utils/vehicleChart';

function hasBreakdownData(history: ReturnType<typeof useActiveChartHistory>): boolean {
  const series = [
    history.davisResistanceTime,
    history.gradientResistanceTime,
    history.curveResistanceTime,
    history.tunnelResistanceTime,
  ];
  return series.some((s) => s.some(([, v]) => v > 0));
}

export default function ResistanceChart() {
  const { clock } = useSimulationState();
  const chartHistory = useActiveChartHistory();
  const stacked = hasBreakdownData(chartHistory);

  const option = useMemo((): EChartsOption => {
    const xMax = chartHistory.resistanceTime.length > 0
      ? stableVehicleTimeMax(clock.elapsed, chartHistory.resistanceTime.at(-1)?.[0])
      : 600;

    const stackedSeries = [
      { name: 'Davis', data: chartHistory.davisResistanceTime, color: '#1890ff' },
      { name: '坡度', data: chartHistory.gradientResistanceTime, color: '#52c41a' },
      { name: '弯道', data: chartHistory.curveResistanceTime, color: '#faad14' },
      { name: '隧道', data: chartHistory.tunnelResistanceTime, color: '#9254de' },
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
        max: xMax,
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: vehicleTimeAxisLabel(),
        axisLine: { lineStyle: { color: '#2a2a4a' } },
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
            data: chartHistory.resistanceTime,
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
  ]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📊 阻力分解</div>
      <div key={stacked ? 'stacked' : 'total'} style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
}
