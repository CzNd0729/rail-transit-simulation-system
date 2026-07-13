/**
 * CompareChartBar — 方案对比柱状图
 * 使用 ECharts 对比各方案的三个核心指标：净能耗、平均速度、总耗时
 */
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

const BAR_METRICS: BarMetric[] = [
  { key: 'netEnergy', label: '净能耗', unit: 'kWh' },
  { key: 'avgSpeed', label: '平均速度', unit: 'km/h' },
  { key: 'totalTime', label: '总耗时', unit: 's' },
];

export default function CompareChartBar({ scenarios }: CompareChartBarProps) {
  if (scenarios.length < 2) {
    return (
      <div className="panel" style={{ height: '100%' }}>
        <div className="panel-title">📈 能耗/速度/耗时对比</div>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' }}>
          请勾选至少 2 个方案进行对比
        </div>
      </div>
    );
  }

  const names = scenarios.map((s) => s.name);
  const colors = ['#1890ff', '#ff4d4f', '#52c41a', '#fadb14', '#722ed1', '#eb2f96'];

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis' as const,
    },
    legend: {
      data: BAR_METRICS.map((m) => m.label),
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: {
      left: 50,
      right: 20,
      top: 30,
      bottom: 50,
    },
    xAxis: {
      type: 'category' as const,
      data: names,
      axisLabel: {
        color: '#a0a0a0',
        fontSize: 11,
        rotate: names.length > 3 ? 15 : 0,
      },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: (
      BAR_METRICS.map((m, i) => ({
        type: 'value' as const,
        name: `${m.label} (${m.unit})`,
        nameTextStyle: { color: '#a0a0a0', fontSize: 10 },
        axisLabel: { color: '#a0a0a0', fontSize: 10 },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        splitLine: { lineStyle: { color: 'rgba(42, 42, 74, 0.4)' } },
        // 多 Y 轴分左右
        position: i % 2 === 0 ? ('left' as const) : ('right' as const),
        offset: i > 0 ? (Math.floor((i - 1) / 2)) * 55 : 0,
      }))
    ),
    series: BAR_METRICS.map((m, i) => ({
      name: m.label,
      type: 'bar' as const,
      yAxisIndex: i,
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
      <div className="panel-title">📈 能耗/速度/耗时对比</div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
