/**
 * SpeedPositionCurve — 速度-位置曲线图
 * 基于《需求文档》UI-VW-03
 * 实时绘制速度随位置变化曲线
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';

export default function SpeedPositionCurve() {
  const { trains } = useSimulationState();
  const train = trains[0]; // 默认显示第一列车

  // TODO: 从数据记录器获取历史轨迹数据
  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '位置 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: 3200,
    },
    yAxis: {
      type: 'value' as const,
      name: '速度 (km/h)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: 100,
    },
    series: [
      {
        name: '实际速度',
        type: 'line',
        smooth: true,
        data: train
          ? [[train.position, train.speed]]
          : [],
        lineStyle: { color: '#1890ff', width: 2 },
        itemStyle: { color: '#1890ff' },
        showSymbol: false,
      },
      {
        name: '限速',
        type: 'line',
        data: [[0, 80], [1500, 80], [3200, 80]],
        lineStyle: { color: '#ff4d4f', type: 'dashed' as const, width: 1 },
        itemStyle: { color: '#ff4d4f' },
        showSymbol: false,
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📈 速度-位置曲线</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
