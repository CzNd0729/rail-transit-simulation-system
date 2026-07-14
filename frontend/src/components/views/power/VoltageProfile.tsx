/**
 * VoltageProfile — 接触网电压分布图（每车独立图表，纵向堆叠）
 * 基于《需求文档》UI-PWR-01
 * 各列车独立网压曲线 + 变电所标记，选中列车置顶
 */
import ReactECharts from 'echarts-for-react';
import { useMemo, useRef } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { getTrainChartHistory } from '../../../utils/chartHistory';
import { trainColorById } from '../../../utils/constants';
import { axisTooltip } from '../../../utils/format';
import { downsample } from '../../../utils/downsample';
import React from 'react';

/** 图例 / 标签用短车号 */
function shortTrainLabel(trainId: string): string {
  const num = trainId.replace(/\D/g, '');
  return num ? `#${num}` : trainId;
}

const VoltageProfile = React.memo(function VoltageProfile() {
  const { power, trains, chartHistory, lineLayout, selectedTrainId, chartVersion } =
    useSimulationState();
  const totalLength = lineLayout?.total_length ?? 3200;

  // 记住当前展示的列车，不随新车发车自动切换
  const pinnedTrainRef = useRef<string | null>(null);
  // 用户手动选车时更新锚定
  if (selectedTrainId && selectedTrainId !== pinnedTrainRef.current) {
    pinnedTrainRef.current = selectedTrainId;
  }
  // 初始化：无锚定时取首车
  if (!pinnedTrainRef.current && trains.length > 0) {
    pinnedTrainRef.current = trains[0].id;
  }
  // 锚定车已消失才回退
  const pinnedId = pinnedTrainRef.current;
  const trainExists = pinnedId && trains.some((t) => t.id === pinnedId);
  if (!trainExists && trains.length > 0) {
    pinnedTrainRef.current = trains[0].id;
  }

  const targetId = pinnedTrainRef.current;
  const selectedTrain = targetId ? trains.find((t) => t.id === targetId) : trains[0];
  const filteredTrains = selectedTrain ? [selectedTrain] : [];

  // Y 轴范围（仅选中列车）
  const yRange = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const train of filteredTrains) {
      min = Math.min(min, train.pantograph_voltage);
      max = Math.max(max, train.pantograph_voltage);
      const vp = getTrainChartHistory(chartHistory, train.id).voltagePosition;
      for (const p of vp) {
        if (p[1] < min) min = p[1];
        if (p[1] > max) max = p[1];
      }
    }
    if (!isFinite(min)) { min = 1500; max = 1500; }
    return {
      yMin: Math.floor(Math.min(1000, min - 100) / 100) * 100,
      yMax: Math.ceil(Math.max(1600, max + 100) / 100) * 100,
    };
  }, [filteredTrains, chartHistory]);

  // 变电所标记（所有子图共享）
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

  // 生成选中列车的 ECharts option
  const trainOptions = useMemo(
    () =>
      filteredTrains.map((train, idx) => {
        const color = trainColorById(train.id, train.direction);
        const vp =
          getTrainChartHistory(chartHistory, train.id).voltagePosition;

        const lineSeries = {
          name: train.id,
          type: 'line' as const,
          data: downsample(vp, 500),
          lineStyle: { color, width: 2 },
          itemStyle: { color },
          showSymbol: false,
          emphasis: { focus: 'series' as const },
        };

        const markerSeries = {
          name: `${train.id}·当前`,
          type: 'scatter' as const,
          data: [[train.position, train.pantograph_voltage]],
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
              `${train.id}<br/>位置 ${train.position.toFixed(0)} m<br/>网压 ${train.pantograph_voltage.toFixed(0)} V`,
          },
          z: 10,
        };

        return {
          option: {
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
              min: yRange.yMin,
              max: yRange.yMax,
              nameTextStyle: { color: '#a0a0a0' },
              axisLabel: { color: '#a0a0a0' },
              axisLine: { lineStyle: { color: '#2a2a4a' } },
            },
            series: [lineSeries, markerSeries, substationSeries],
          },
          train,
          idx,
        };
      }),
    [filteredTrains, trains, chartHistory, totalLength, yRange, substationSeries, chartVersion],
  );

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
        {trainOptions.map(({ option, train }) => (
          <div key={train.id} style={{ height: '100%' }}>
            <ReactECharts
              option={option}
              style={{ height: '100%', width: '100%' }}
              notMerge={true}
            />
          </div>
        ))}
      </div>
    </div>
  );
});

export default VoltageProfile;
