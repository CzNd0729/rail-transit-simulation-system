/**
 * SpeedEnvelope — 速度包络线图
 * 基于《迭代二需求文档》UI-SIG-02（单列车简化版）
 * ATP 紧急制动曲线留待迭代三
 */
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { axisTooltip } from '../../../utils/format';
import type { ProfileSegment } from '../../../data/mvpLineLayout';

function toStepData(
  segments: ProfileSegment[],
  field: 'speed_limit',
): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    result.push([seg.start_chainage, seg[field]]);
    result.push([seg.end_chainage, seg[field]]);
  }
  return result;
}

export default function SpeedEnvelope() {
  const { chartHistory, lineLayout, profileSegments, params } = useSimulationState();
  const maxPos = lineLayout?.total_length ?? 3200;
  const segments = profileSegments ?? [];
  const ratio = params.signal.target_speed_ratio ?? 0.85;

  const speedLimitData = segments.length > 0
    ? toStepData(segments, 'speed_limit')
    : ([[0, 80], [maxPos, 80]] as [number, number][]);

  const targetSpeedData = segments.length > 0
    ? segments.flatMap((seg) => [
        [seg.start_chainage, seg.speed_limit * ratio],
        [seg.end_chainage, seg.speed_limit * ratio],
      ] as [number, number][])
    : ([[0, 80 * ratio], [maxPos, 80 * ratio]] as [number, number][]);

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(1) },
    legend: {
      data: ['区段限速', '目标速度', '实际速度'],
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 50, right: 20, top: 28, bottom: 40 },
    xAxis: {
      type: 'value' as const,
      name: '位置 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      max: maxPos,
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
        name: '区段限速',
        type: 'line',
        data: speedLimitData,
        lineStyle: { color: '#ff4d4f', type: 'dashed' as const, width: 1 },
        itemStyle: { color: '#ff4d4f' },
        showSymbol: false,
      },
      {
        name: '目标速度',
        type: 'line',
        data: targetSpeedData,
        lineStyle: { color: '#fa8c16', type: 'dashed' as const, width: 1 },
        itemStyle: { color: '#fa8c16' },
        showSymbol: false,
      },
      {
        name: '实际速度',
        type: 'line',
        smooth: true,
        data: chartHistory.speedPosition,
        lineStyle: { color: '#1890ff', width: 2 },
        itemStyle: { color: '#1890ff' },
        showSymbol: false,
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">📉 速度包络线</div>
      <ReactECharts
        option={option}
        style={{ height: 'calc(100% - 30px)' }}
        notMerge
      />
    </div>
  );
}
