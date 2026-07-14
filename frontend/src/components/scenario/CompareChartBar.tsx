/**
 * CompareChartBar — 方案对比柱状图
 * 支持按维度切换（效率/能耗/舒适/安全/准点），使用 ECharts 对比各方案指标
 */
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareChartBarProps {
  scenarios: ScenarioDetailResponse[];
}

/** 对比指标定义 */
interface BarMetric {
  key: string;
  label: string;
  unit: string;
}

const DIMENSION_METRICS: Record<string, BarMetric[]> = {
  '效率': [
    { key: 'totalTime', label: '总耗时', unit: 's' },
    { key: 'totalDistance', label: '总里程', unit: 'm' },
    { key: 'avgSpeed', label: '平均速度', unit: 'km/h' },
    { key: 'maxSpeed', label: '最高速度', unit: 'km/h' },
  ],
  '能耗': [
    { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh' },
    { key: 'regenEnergy', label: '再生电量', unit: 'kWh' },
    { key: 'netEnergy', label: '净能耗', unit: 'kWh' },
    { key: 'regenRate', label: '再生利用率', unit: '%' },
  ],
  '舒适度': [
    { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³' },
    { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³' },
    { key: 'maxAccel', label: '最大加速度', unit: 'm/s²' },
  ],
  '安全': [
    { key: 'minVoltage', label: '最低网压', unit: 'V' },
    { key: 'peakPower', label: '峰值功率', unit: 'kW' },
    { key: 'ebCount', label: '紧急制动', unit: '次' },
  ],
  '准点': [
    { key: 'totalDelay', label: '总晚点', unit: 's' },
  ],
};

const DIMENSION_NAMES = Object.keys(DIMENSION_METRICS);

export default function CompareChartBar({ scenarios }: CompareChartBarProps) {
  const [selectedDim, setSelectedDim] = useState('效率');

  if (scenarios.length < 2) {
    return (
      <div className="panel" style={{ height: '100%' }}>
        <div className="panel-title">📈 指标对比柱状图</div>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' }}>
          请勾选至少 2 个方案进行对比
        </div>
      </div>
    );
  }

  const metrics = DIMENSION_METRICS[selectedDim];
  const names = scenarios.map((s) => s.name);
  const colors = ['#1890ff', '#ff4d4f', '#52c41a', '#fadb14', '#722ed1', '#eb2f96'];

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    legend: {
      data: metrics.map((m) => m.label),
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 60, right: 60, top: 30, bottom: 50 },
    xAxis: {
      type: 'category' as const,
      data: names,
      axisLabel: {
        color: '#a0a0a0', fontSize: 11,
        rotate: names.length > 3 ? 15 : 0,
      },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: metrics.map((m) => `${m.label}(${m.unit})`).join(' / '),
        nameTextStyle: { color: '#a0a0a0', fontSize: 10 },
        axisLabel: { color: '#a0a0a0', fontSize: 10 },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        splitLine: { lineStyle: { color: 'rgba(42, 42, 74, 0.4)' } },
      },
    ],
    series: metrics.map((m, i) => ({
      name: m.label,
      type: 'bar' as const,
      data: scenarios.map((s) => {
        const v = (s.result as unknown as Record<string, number>)[m.key];
        return typeof v === 'number' ? Number(v.toFixed(1)) : 0;
      }),
      itemStyle: { color: colors[i % colors.length] },
      barMaxWidth: 40,
    })),
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <div className="panel-title" style={{ margin: 0 }}>📈 指标对比柱状图</div>
        <select
          value={selectedDim}
          onChange={(e) => setSelectedDim(e.target.value)}
          style={{
            fontSize: '12px',
            padding: '2px 8px',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
          }}
        >
          {DIMENSION_NAMES.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
