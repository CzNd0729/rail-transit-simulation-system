/**
 * SpeedPositionCurve — 速度-位置曲线图（多车叠加）
 */
import ReactECharts from 'echarts-for-react';
import { useMemo } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { getTrainChartHistory } from '../../../utils/chartHistory';
import { trainColorByIndex } from '../../../utils/constants';
import { axisTooltip } from '../../../utils/format';

/** 图例 / 标签用短车号 */
function shortTrainLabel(trainId: string): string {
  const num = trainId.replace(/\D/g, '');
  return num ? `#${num}` : trainId;
}

export default function SpeedPositionCurve() {
  const { chartHistory, lineLayout, profileSegments, trains } = useSimulationState();
  const maxPos = lineLayout?.total_length ?? 3200;
  const speedLimitData = (profileSegments ?? []).flatMap((seg) => [
    [seg.start_chainage, seg.speed_limit],
    [seg.end_chainage, seg.speed_limit],
  ] as [number, number][]);

  const trainSeries = useMemo(
    () =>
      trains.map((train, idx) => {
        const color = trainColorByIndex(idx);
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
    [chartHistory, trains],
  );

  const positionMarkers = useMemo(
    () =>
      trains.map((train, idx) => {
        const color = trainColorByIndex(idx);
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
            position: 'top',
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
    [trains],
  );

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const, formatter: axisTooltip(2) },
    legend: trains.length > 1
      ? {
          data: trains.map((t) => t.id),
          top: 4,
          right: 12,
          orient: 'horizontal' as const,
          itemWidth: 14,
          itemHeight: 8,
          itemGap: 16,
          textStyle: { color: '#a0a0a0', fontSize: 11 },
          icon: 'roundRect',
        }
      : undefined,
    grid: { left: 50, right: 20, top: trains.length > 1 ? 40 : 20, bottom: 40 },
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
      ...trainSeries,
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
