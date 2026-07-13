/**
 * TimetableChart — 运行图（时间-距离图）
 * 基于《迭代二需求文档》UI-SIG-03（单列车简化版）
 */
import { useMemo } from 'react';
import type { EChartsOption } from 'echarts';
import SimEChart from '../../common/SimEChart';
import { useSimulationState } from '../../../context/SimulationContext';
import { useActiveChartHistory, useSelectedTrain } from '../../../hooks/useSelectedTrain';
import { mockLineData } from '../../../data/mockLineData';
import { axisTooltip } from '../../../utils/format';
import { resolveLatestDeviation } from '../../../utils/signalSelectors';

/** X 轴上限按 50s 阶梯取整，避免每帧 float 抖动 */
function stableTimeMax(points: [number, number][]): number {
  if (points.length === 0) return 60;
  const lastT = points[points.length - 1][0];
  return Math.ceil(Math.max(lastT + 20, 60) / 50) * 50;
}

const STATION_LABEL_MAX_CHARS = 4;
const STATION_LABEL_WIDTH = 76;
const STATION_LABEL_LINE_HEIGHT = 12;
const BOTTOM_ZONE_RATIO = 0.04;
const MIN_FONT_SIZE = 7;
/** 用于估算相邻站名垂直间距（像素） */
const CHART_HEIGHT_ESTIMATE = 400;

interface StationLabelStyle {
  formatter: string;
  fontSize: number;
  offset?: [number, number];
}

function wrapStationName(name: string, maxCharsPerLine: number): string {
  if (name.length <= maxCharsPerLine) return name;
  const lines: string[] = [];
  for (let i = 0; i < name.length; i += maxCharsPerLine) {
    lines.push(name.slice(i, i + maxCharsPerLine));
  }
  return lines.join('\n');
}

function baseFontSize(name: string): number {
  if (name.length <= 4) return 10;
  if (name.length <= 6) return 9;
  return 8;
}

function buildStationLabel(
  name: string,
  chainage: number,
  maxPos: number,
  prevChainage: number | null,
): StationLabelStyle {
  const wrapped = wrapStationName(name, STATION_LABEL_MAX_CHARS);
  const lineCount = wrapped.split('\n').length;
  let fontSize =
    lineCount > 1 ? Math.min(baseFontSize(name), 9) : baseFontSize(name);

  const isBottom = chainage <= maxPos * BOTTOM_ZONE_RATIO;
  if (isBottom) {
    fontSize = Math.min(fontSize, 8);
  }

  if (prevChainage !== null && maxPos > 0) {
    const minGapM =
      ((lineCount * STATION_LABEL_LINE_HEIGHT) / CHART_HEIGHT_ESTIMATE) * maxPos;
    if (chainage - prevChainage < minGapM) {
      fontSize = Math.max(MIN_FONT_SIZE, fontSize - 1);
    }
  }

  return {
    formatter: wrapped,
    fontSize,
    offset: isBottom ? [0, -14] : undefined,
  };
}

export default function TimetableChart() {
  const chartHistory = useActiveChartHistory();
  const { lineLayout, signaling } = useSimulationState();
  const train = useSelectedTrain();
  const stations = lineLayout?.stations ?? mockLineData.stations;
  const maxPos = lineLayout?.total_length ?? mockLineData.total_length;
  const deviation = resolveLatestDeviation(
    signaling.timetable_deviations,
    train?.id ?? 'TRAIN_01',
  );

  const xMax = useMemo(
    () => stableTimeMax(chartHistory.positionTime),
    [chartHistory.positionTime],
  );

  const stationMarkLines = useMemo(() => {
    const sorted = [...stations].sort((a, b) => a.chainage - b.chainage);
    const labelById = new Map<string, StationLabelStyle>();
    let prevChainage: number | null = null;
    for (const st of sorted) {
      labelById.set(
        st.id,
        buildStationLabel(st.name, st.chainage, maxPos, prevChainage),
      );
      prevChainage = st.chainage;
    }

    return stations.map((st) => {
      const style = labelById.get(st.id)!;
      return {
        yAxis: st.chainage,
        label: {
          formatter: style.formatter,
          color: '#a0a0a0',
          fontSize: style.fontSize,
          lineHeight: STATION_LABEL_LINE_HEIGHT,
          width: STATION_LABEL_WIDTH,
          overflow: 'breakAll' as const,
          // ECharts 6 默认 middle 会把站名堆在图中央；end = 参考线右端
          position: 'end' as const,
          ...(style.offset ? { offset: style.offset } : {}),
        },
        lineStyle: { color: '#3a3a5a', type: 'dashed' as const },
      };
    });
  }, [stations, maxPos]);

  const option = useMemo(
    (): EChartsOption => ({
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' as const, formatter: axisTooltip(1) },
      grid: { left: 55, right: 84, top: 20, bottom: 52 },
      xAxis: {
        type: 'value' as const,
        name: '时间 (s)',
        nameLocation: 'middle' as const,
        nameGap: 30,
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        max: xMax,
      },
      yAxis: {
        type: 'value' as const,
        name: '位置 (m)',
        nameTextStyle: { color: '#a0a0a0' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        max: maxPos,
      },
      series: [
        {
          name: '运行轨迹',
          type: 'line',
          smooth: true,
          data: chartHistory.positionTime,
          lineStyle: { color: '#1890ff', width: 2 },
          itemStyle: { color: '#1890ff' },
          showSymbol: false,
          markLine: {
            silent: true,
            symbol: 'none',
            data: stationMarkLines,
          },
        },
      ],
    }),
    [chartHistory.positionTime, xMax, maxPos, stationMarkLines],
  );

  const deviationText = deviation
    ? `最近到站偏差 ${deviation.delay_arrival >= 0 ? '+' : ''}${deviation.delay_arrival.toFixed(1)} s（${deviation.station_id}）`
    : '';

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📅 运行图</div>
      {/* 固定占位，避免 ATS 偏差出现时插入新节点导致 ECharts DOM 与 React 不同步 */}
      <div
        style={{
          fontSize: 11,
          color: '#fa8c16',
          padding: '0 8px 4px',
          minHeight: 20,
          flexShrink: 0,
          visibility: deviation ? 'visible' : 'hidden',
        }}
        aria-hidden={!deviation}
      >
        {deviationText || '\u00a0'}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <SimEChart option={option} style={{ height: '100%' }} />
      </div>
    </div>
  );
}
