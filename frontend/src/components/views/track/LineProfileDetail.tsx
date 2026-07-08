/**
 * LineProfileDetail — 线路综合剖面图（ECharts 双 Y 轴）
 * 显示全线坡度填充图 + 限速虚线 + 车站标注 + 隧道遮罩 + 列车位置
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData, mockSegmentParams } from '../../../data/mockLineData';

/** 将分段参数展开为 ECharts 阶梯图坐标对 */
function toStepData(
  segments: Array<{ start_chainage: number; end_chainage: number; gradient: number; speed_limit: number }>,
  field: 'gradient' | 'speed_limit'
): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    result.push([seg.start_chainage, seg[field]]);
    result.push([seg.end_chainage, seg[field]]);
  }
  return result;
}

export default function LineProfileDetail() {
  const { trains } = useSimulationState();
  const { stations, total_length } = mockLineData;

  const gradientData = toStepData(mockSegmentParams, 'gradient');
  const speedLimitData = toStepData(mockSegmentParams, 'speed_limit');

  // 车站竖虚线标注
  const stationMarkLines = stations.map((s) => ({
    xAxis: s.chainage,
    label: { formatter: s.name, color: '#e0e0e0', fontSize: 10 },
    lineStyle: { color: '#555', type: 'dashed' as const, width: 1 },
  }));

  // 隧道段半透明遮罩
  const tunnelAreas = mockSegmentParams
    .filter((s) => s.is_tunnel)
    .map((s) => [
      { xAxis: s.start_chainage, itemStyle: { color: 'rgba(128,128,128,0.15)' } },
      { xAxis: s.end_chainage },
    ]);

  // 列车当前位置竖线
  const trainPos = trains[0]?.position;
  const trainMarkLine = trainPos != null ? [{
    xAxis: trainPos,
    label: { formatter: '🚇', color: '#ff4d4f', fontSize: 14 },
    lineStyle: { color: '#ff4d4f', type: 'solid' as const, width: 2 },
  }] : [];

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    legend: {
      data: ['坡度 (‰)', '限速 (km/h)'],
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 55, right: 55, top: 36, bottom: 32 },
    xAxis: {
      type: 'value' as const,
      name: '公里标 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      min: 0,
      max: total_length,
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '坡度 (‰)',
        nameTextStyle: { color: '#1890ff' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#1890ff' } },
        splitLine: { lineStyle: { color: '#1a1a2e' } },
      },
      {
        type: 'value' as const,
        name: '限速 (km/h)',
        nameTextStyle: { color: '#ff4d4f' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#ff4d4f' } },
        splitLine: { show: false },
        min: 0,
        max: 100,
      },
    ],
    series: [
      {
        name: '坡度 (‰)',
        type: 'line',
        yAxisIndex: 0,
        data: gradientData,
        areaStyle: { color: 'rgba(24, 144, 255, 0.12)' },
        lineStyle: { color: '#1890ff', width: 1.5 },
        itemStyle: { color: '#1890ff' },
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: stationMarkLines,
        },
        markArea: {
          silent: true,
          data: tunnelAreas,
        },
      },
      {
        name: '限速 (km/h)',
        type: 'line',
        yAxisIndex: 1,
        data: speedLimitData,
        lineStyle: { color: '#ff4d4f', type: 'dashed' as const, width: 1.5 },
        itemStyle: { color: '#ff4d4f' },
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: trainMarkLine,
        },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🏔️ 线路综合剖面图</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
