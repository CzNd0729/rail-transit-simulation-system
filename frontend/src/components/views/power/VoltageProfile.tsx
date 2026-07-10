/**
 * VoltageProfile — 接触网电压分布图
 * 基于《需求文档》UI-PWR-01
 * 全线电压曲线，标示变电所位置
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { axisTooltip } from '../../../utils/format';

export default function VoltageProfile() {
  const { power } = useSimulationState();

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: (params: any) => {
      const formatted = axisTooltip(2)(params);
      return formatted.replace(/:\s*([\d.]+)$/, ': $1 V');
    } },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '公里标 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '电压 (V)',
      min: 1400,
      max: 1600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '接触网电压',
        type: 'line',
        smooth: true,
        data: power.voltage_profile.length > 0
          ? power.voltage_profile.map((p) => [p.chainage, p.voltage])
          : [[0, 1500], [3200, 1500]],
        lineStyle: { color: '#faad14', width: 2 },
        itemStyle: { color: '#faad14' },
        areaStyle: { color: 'rgba(250, 173, 20, 0.1)' },
        showSymbol: false,
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📊 接触网电压分布</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
