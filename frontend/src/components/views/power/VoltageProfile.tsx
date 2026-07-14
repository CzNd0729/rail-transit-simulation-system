/**
 * VoltageProfile — 接触网电压分布图（每车独立图表，纵向堆叠）
 * 基于《需求文档》UI-PWR-01
 * 各列车独立网压曲线 + 变电所标记，选中列车置顶
 *
 * 核心设计：电压-位置数据是历史记录，列车经过某位置后不再变化，
 * 因此每帧只追加新数据，不重绘旧数据，彻底消除抖动。
 */
import ReactECharts from 'echarts-for-react';
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { getTrainChartHistory } from '../../../utils/chartHistory';
import { trainColorById } from '../../../utils/constants';
import { axisTooltip } from '../../../utils/format';
import React from 'react';

/** 图例 / 标签用短车号 */
function shortTrainLabel(trainId: string): string {
  const num = trainId.replace(/\D/g, '');
  return num ? `#${num}` : trainId;
}

/** 固定 Y 轴范围，避免每帧数据波动导致轴位移抖动 */
const Y_RANGE = { yMin: 0, yMax: 2000 };

const VoltageProfile = React.memo(function VoltageProfile() {
  const { power, trains, chartHistory, lineLayout, selectedTrainId, chartVersion } =
    useSimulationState();
  const totalLength = lineLayout?.total_length ?? 3200;

  // 锚定列车逻辑（不随新车发车自动切换）
  const pinnedTrainRef = useRef<string | null>(null);
  if (selectedTrainId && selectedTrainId !== pinnedTrainRef.current) {
    pinnedTrainRef.current = selectedTrainId;
  }
  if (!pinnedTrainRef.current && trains.length > 0) {
    pinnedTrainRef.current = trains[0].id;
  }
  const pinnedId = pinnedTrainRef.current;
  const trainExists = pinnedId && trains.some((t) => t.id === pinnedId);
  if (!trainExists && trains.length > 0) {
    pinnedTrainRef.current = trains[0].id;
  }

  const targetId = pinnedTrainRef.current;
  const selectedTrain = targetId ? trains.find((t) => t.id === targetId) : trains[0];
  const filteredTrains = selectedTrain ? [selectedTrain] : [];

  // ECharts 实例引用
  const chartRef = useRef<ReactECharts>(null);
  // 已渲染的历史数据长度（按列车 ID 记录）
  const renderedLenRef = useRef<Record<string, number>>({});
  // 上一次的 chartVersion，用于检测是否被重置
  const prevVersionRef = useRef<number>(chartVersion);
  // ECharts 就绪标志 — 解决视图切换重载时 getEchartsInstance() 时序返回 null 的问题
  const [chartReady, setChartReady] = useState(false);

  const handleChartReady = useCallback(() => {
    setChartReady(true);
  }, []);

  // 变电所标记（稳定，只在 substations 变化时重建）
  const substationSeries = useMemo(
    () => ({
      name: '变电所',
      type: 'scatter' as const,
      data: power.substations.map((sub) => [
        sub.chainage,
        sub.rated_voltage,
        sub.name,
      ]),
      symbolSize: 12,
      itemStyle: { color: '#52c41a' },
      label: {
        show: true,
        position: 'top' as const,
        formatter: (params: any) => params.data[2],
        fontSize: 10,
        color: '#a0a0a0',
      },
    }),
    [power.substations],
  );

  // 检测 chartVersion 回退（历史数据被清空重置），重置渲染计数和就绪标志
  if (chartVersion < prevVersionRef.current) {
    renderedLenRef.current = {};
    if (chartReady) setChartReady(false);
  }
  prevVersionRef.current = chartVersion;

  // 核心：每帧只追加新数据点，不重绘旧数据
  useEffect(() => {
    if (!chartRef.current || !targetId || !chartReady) return;
    const echartsInstance = chartRef.current.getEchartsInstance();
    if (!echartsInstance) return;

    const train = trains.find((t) => t.id === targetId);
    const color = trainColorById(targetId, train?.direction ?? 'up');
    const vp = getTrainChartHistory(chartHistory, targetId).voltagePosition;
    const rendered = renderedLenRef.current[targetId] ?? 0;

    // 历史数据被清空（重置场景），重置图表
    if (vp.length < rendered) {
      renderedLenRef.current[targetId] = 0;
      echartsInstance.clear();
    }

    const effectiveRendered = renderedLenRef.current[targetId] ?? 0;

    // 首次渲染：创建完整图表
    if (effectiveRendered === 0 && vp.length > 0) {
      renderedLenRef.current[targetId] = vp.length;
      const currentPos = train ? [[train.position, train.pantograph_voltage]] : [];

      echartsInstance.setOption(
        {
          backgroundColor: 'transparent',
          animation: false,
          tooltip: {
            trigger: 'axis' as const,
            formatter: (params: any) => {
              const formatted = axisTooltip(2)(params);
              return formatted.replace(/:\s*([\d.]+)$/, ': $1 V');
            },
          },
          grid: { left: 50, right: 20, top: 28, bottom: 30 },
          xAxis: {
            type: 'value' as const,
            name: '公里标 (m)',
            min: 0,
            max: totalLength,
            nameTextStyle: { color: '#a0a0a0' },
            axisLabel: { color: '#a0a0a0' },
            axisLine: { lineStyle: { color: '#2a2a4a' } },
          },
          yAxis: {
            type: 'value' as const,
            name: '电压 (V)',
            min: Y_RANGE.yMin,
            max: Y_RANGE.yMax,
            nameTextStyle: { color: '#a0a0a0' },
            axisLabel: { color: '#a0a0a0' },
            axisLine: { lineStyle: { color: '#2a2a4a' } },
          },
          series: [
            {
              name: targetId,
              type: 'line' as const,
              data: vp.slice(),
              lineStyle: { color, width: 2 },
              itemStyle: { color },
              showSymbol: false,
              sampling: 'lttb',
              emphasis: { focus: 'series' as const },
            },
            {
              name: `${targetId}·当前`,
              type: 'scatter' as const,
              data: currentPos,
              symbol: 'circle',
              symbolSize: 10,
              itemStyle: {
                color,
                borderColor: '#fff',
                borderWidth: 1.5,
                shadowBlur: 6,
                shadowColor: color,
              },
              label: {
                show: true,
                formatter: shortTrainLabel(targetId),
                position: 'top' as const,
                distance: 8,
                color,
                fontSize: 11,
                fontWeight: 600,
                backgroundColor: 'rgba(0,0,0,0.55)',
                padding: [2, 5],
                borderRadius: 3,
              },
              z: 10,
            },
            substationSeries,
          ],
        },
        { notMerge: false },
      );
      return;
    }

    // 追加新数据（增量更新）
    if (vp.length > effectiveRendered) {
      renderedLenRef.current[targetId] = vp.length;
      echartsInstance.setOption(
        {
          series: [
            { data: vp.slice() },
            { data: train ? [[train.position, train.pantograph_voltage]] : [] },
          ],
        },
        { notMerge: false },
      );
      return;
    }

    // 无新历史数据，仅更新当前标记位置
    if (train) {
      echartsInstance.setOption(
        {
          series: [
            {},
            { data: [[train.position, train.pantograph_voltage]] },
          ],
        },
        { notMerge: false },
      );
    }
  }, [chartReady, chartVersion, targetId, trains, chartHistory, totalLength, substationSeries]);

  if (filteredTrains.length === 0) {
    return (
      <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <div className="panel-title">📊 接触网电压分布</div>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#666' }}>
          暂无列车数据
        </div>
      </div>
    );
  }

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">
        📊 接触网电压分布
        {filteredTrains[0] && (
          <span style={{ color: trainColorById(filteredTrains[0].id, filteredTrains[0].direction), marginLeft: 8, fontSize: 12 }}>
            {filteredTrains[0].id}
          </span>
        )}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <ReactECharts
          ref={chartRef}
          onChartReady={handleChartReady}
          option={{}}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
        />
      </div>
    </div>
  );
});

export default VoltageProfile;
