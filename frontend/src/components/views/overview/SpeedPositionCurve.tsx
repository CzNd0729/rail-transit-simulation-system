/**
 * SpeedPositionCurve — 速度-位置曲线图（单列车，选中即切换）
 * 使用 SimEChart 避免 notMerge 全量 DOM 重建，动画关闭实现即时切换
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { getTrainChartHistory } from '../../../utils/chartHistory';
import { trainColorByIndex } from '../../../utils/constants';
import { axisTooltip } from '../../../utils/format';
import { downsample } from '../../../utils/downsample';

/** 图例 / 标签用短车号 */
function shortTrainLabel(trainId: string): string {
  const num = trainId.replace(/\D/g, '');
  return num ? `#${num}` : trainId;
}

export default function SpeedPositionCurve() {
  const { chartHistory, lineLayout, profileSegments, trains, selectedTrainId, chartVersion } = useSimulationState();
  const maxPos = lineLayout?.total_length ?? 3200;
  const speedLimitData = (profileSegments ?? []).flatMap((seg) => [
    [seg.start_chainage, seg.speed_limit],
    [seg.end_chainage, seg.speed_limit],
  ] as [number, number][]);

  // 仅绘制选中列车
  const selectedTrains = trains.filter((t) => t.id === selectedTrainId);

  const trainSeries = useMemo(
    () =>
      selectedTrains.map((train) => {
        // 用列车在全部 trains 中的实际索引确保颜色一致
        const realIdx = trains.findIndex((t) => t.id === train.id);
        const color = trainColorByIndex(realIdx >= 0 ? realIdx : 0);
        return {
          name: train.id,
          type: 'line' as const,
          smooth: true,
          data: getTrainChartHistory(chartHistory, train.id).speedPosition,
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          showSymbol: false,
          emphasis: { focus: 'series' as const },
        };
      }),
    [chartHistory, selectedTrains, chartVersion],
  );

  const positionMarkers = useMemo(
    () =>
      selectedTrains.map((train) => {
        const realIdx = trains.findIndex((t) => t.id === train.id);
        const color = trainColorByIndex(realIdx >= 0 ? realIdx : 0);
        return {
          name: `${train.id}·当前`,
          type: 'scatter' as const,
          data: [[train.position, train.speed]],
          symbol: 'circle',
          symbolSize: 9,
          itemStyle: {
            color,
            borderColor: '#fff',
            borderWidth: 1.5,
            shadowBlur: 6,
            shadowColor: color,
          },
          label: {
            show: true,
            formatter: shortTrainLabel(train.id),
            position: 'top' as const,
            distance: 8,
            color,
            fontSize: 11,
            fontWeight: 600,
            backgroundColor: 'rgba(0,0,0,0.55)',
            padding: [2, 5],
            borderRadius: 3,
          },
          tooltip: {
            formatter: () =>
              `${train.id}<br/>位置 ${train.position.toFixed(0)} m<br/>速度 ${train.speed.toFixed(1)} km/h`,
          },
          z: 10,
        };
      }),
    [selectedTrains],
  );

  const option = useMemo(() => ({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(2) },
    legend: undefined,
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
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
      ...trainSeries.map((s) => ({
        ...s,
        data: downsample(s.data as [number, number][], 500),
      })),
      ...positionMarkers,
      {
        name: '限速',
        type: 'line',
        data: speedLimitData.length > 0 ? speedLimitData : [[0, 80], [1500, 80], [3200, 80]],
        lineStyle: { color: '#666', type: 'dashed' as const, width: 1 },
        itemStyle: { color: '#666' },
        showSymbol: false,
      },
    ],
  } as EChartsOption), [trainSeries, positionMarkers, speedLimitData, maxPos, chartVersion]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">
        📈 速度-位置曲线
        {selectedTrains[0] && (
          <span style={{ color: trainColorByIndex(trains.findIndex((t) => t.id === selectedTrains[0].id)), marginLeft: 8, fontSize: 12 }}>
            {selectedTrains[0].id}
          </span>
        )}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
}
