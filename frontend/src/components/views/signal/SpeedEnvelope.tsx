/**
 * SpeedEnvelope — 速度包络线图
 * 基于《迭代二需求文档》UI-SIG-02（单列车简化版）
 * ATP 紧急制动曲线留待迭代三
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory } from '../../../hooks/useSelectedTrain';
import { axisTooltip } from '../../../utils/format';
import { resolveAtpSpeedLimit, resolvePermanentSpeedLimit } from '../../../utils/signalSelectors';
import { useSelectedTrain } from '../../../hooks/useSelectedTrain';
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
  const { lineLayout, profileSegments, params, signaling } = useSimulationState();
  const chartHistory = useActiveChartHistory();
  const train = useSelectedTrain();
  const maxPos = lineLayout?.total_length ?? 3200;
  const segments = profileSegments ?? [];
  const ratio = params.signal.target_speed_ratio ?? 0.85;
  const defaultLimit = segments.length > 0 ? segments[0].speed_limit : 80;
  const trainId = train?.id ?? 'TRAIN_01';
  const hasBackendLimits = signaling.speed_limits.length > 0;
  const permanentLimitKmh = resolvePermanentSpeedLimit(
    signaling.speed_limits,
    trainId,
    defaultLimit,
  );
  const atpLimitKmh = resolveAtpSpeedLimit(
    signaling.speed_limits,
    trainId,
    defaultLimit,
  );

  const speedLimitData = hasBackendLimits
    ? ([[0, permanentLimitKmh], [maxPos, permanentLimitKmh]] as [number, number][])
    : segments.length > 0
      ? toStepData(segments, 'speed_limit')
      : ([[0, 80], [maxPos, 80]] as [number, number][]);

  const targetSpeedData = hasBackendLimits
    ? ([[0, permanentLimitKmh * ratio], [maxPos, permanentLimitKmh * ratio]] as [number, number][])
    : segments.length > 0
      ? segments.flatMap((seg) => [
          [seg.start_chainage, seg.speed_limit * ratio],
          [seg.end_chainage, seg.speed_limit * ratio],
        ] as [number, number][])
      : ([[0, 80 * ratio], [maxPos, 80 * ratio]] as [number, number][]);

  const atpLimitData = segments.length > 0
    ? segments.flatMap((seg) => [
        [seg.start_chainage, Math.min(seg.speed_limit, atpLimitKmh)],
        [seg.end_chainage, Math.min(seg.speed_limit, atpLimitKmh)],
      ] as [number, number][])
    : ([[0, atpLimitKmh], [maxPos, atpLimitKmh]] as [number, number][]);

  const option = useMemo((): EChartsOption => ({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(1) },
    legend: {
      data: ['区段限速', 'ATP 限速', '目标速度', '实际速度'],
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
        name: 'ATP 限速',
        type: 'line',
        data: atpLimitData,
        lineStyle: { color: '#eb2f96', type: 'dotted' as const, width: 1 },
        itemStyle: { color: '#eb2f96' },
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
  }), [
    speedLimitData,
    atpLimitData,
    targetSpeedData,
    chartHistory.speedPosition,
    maxPos,
  ]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📉 速度包络线</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
}
