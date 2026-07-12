/**
 * VoltageProfile — 接触网电压分布图
 * 基于《需求文档》UI-PWR-01
 * 全线电压曲线，标示变电所位置和列车当前位置
 */
import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useSelectedTrain } from '../../../hooks/useSelectedTrain';
import { axisTooltip } from '../../../utils/format';
import type { VoltagePoint } from '../../../types/simulation';

// 模块级缓存，组件切换时不丢失累积数据
let accumulatedCache: VoltagePoint[] = [];
let prevRunState: string = 'idle';

export default function VoltageProfile() {
  const { power, lineLayout, runState } = useSimulationState();
  const train = useSelectedTrain();
  const trainPosition = train?.position;
  const trainVoltage = train?.pantograph_voltage;
  const totalLength = lineLayout?.total_length ?? 3200;

  // 新仿真启动时清空上一次的曲线（仅 idle/stopped → running，不含 resumed）
  if ((prevRunState === 'idle' || prevRunState === 'stopped') && runState === 'running') {
    accumulatedCache = [];
  }
  prevRunState = runState;

  if (power.voltage_profile.length > 0) {
    const newPoint = power.voltage_profile[0];
    const last = accumulatedCache[accumulatedCache.length - 1];
    if (!last || last.chainage !== newPoint.chainage || last.voltage !== newPoint.voltage) {
      accumulatedCache.push(newPoint);
      if (accumulatedCache.length > 2000) {
        accumulatedCache.shift();
      }
    }
  }

  // 确保曲线始终从 0 公里处开始
  const voltageCurve = accumulatedCache.length > 0
    ? [{ chainage: 0, voltage: 1500 }, ...accumulatedCache]
    : power.voltage_profile;

  // 列车位置在 X 轴的百分比
  const trainPercent = totalLength > 0 && trainPosition != null
    ? (trainPosition / totalLength) * 100
    : null;

  const option = useMemo(() => ({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: any) => {
        const formatted = axisTooltip(2)(params);
        return formatted.replace(/:\s*([\d.]+)$/, ': $1 V');
      },
    },
    grid: { left: 50, right: 20, top: 30, bottom: 40 },
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
      min: 1000,
      max: 1600,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '接触网电压',
        type: 'line',
        smooth: true,
        data: voltageCurve.map((p) => [p.chainage, p.voltage]),
        lineStyle: { color: '#faad14', width: 2 },
        itemStyle: { color: '#faad14' },
        areaStyle: { color: 'rgba(250, 173, 20, 0.1)' },
        showSymbol: false,
        markLine: trainPosition != null ? {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'solid', color: '#ff4d4f', width: 2, opacity: 0.6 },
          label: { show: false },
          data: [{ xAxis: trainPosition }],
        } : undefined,
        markPoint: trainPosition != null && trainVoltage != null ? {
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: { color: '#ff4d4f', borderColor: '#fff', borderWidth: 1 },
          data: [{ coord: [trainPosition, trainVoltage] }],
        } : undefined,
      },
      {
        name: '变电所',
        type: 'scatter',
        data: power.substations.map(sub => [sub.chainage, sub.rated_voltage, sub.name]),
        symbolSize: 12,
        itemStyle: { color: '#52c41a' },
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => params.data[2],
          fontSize: 10,
          color: '#a0a0a0',
        },
      },
    ],
  }), [voltageCurve, power.substations, trainPosition, totalLength]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📊 接触网电压分布</div>
      <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <ReactECharts
          option={option}
          style={{ height: '100%' }}
          notMerge={false}
        />
        {/* 列车标注：公里标 + 网压值 */}
        {trainPercent != null && trainVoltage != null && (
          <>
            {/* 公里标标注 */}
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: `calc(50px + ${(trainPosition ?? 0) / totalLength} * (100% - 70px))`,
                transform: 'translateX(-50%)',
                fontSize: '10px',
                color: '#ff4d4f',
                fontWeight: 600,
                pointerEvents: 'none',
                zIndex: 2,
                whiteSpace: 'nowrap',
              }}
            >
              {trainPosition != null ? (trainPosition / 1000).toFixed(2) : '-'} km
            </div>
            {/* 网压标注 — 在图表上方外部，避免与变电所标签重叠 */}
            <div
              style={{
                position: 'absolute',
                top: 8,
                left: `calc(50px + ${(trainPosition ?? 0) / totalLength} * (100% - 70px))`,
                transform: 'translateX(-50%)',
                fontSize: '10px',
                color: '#faad14',
                fontWeight: 600,
                pointerEvents: 'none',
                zIndex: 2,
                whiteSpace: 'nowrap',
              }}
            >
              {trainVoltage != null ? trainVoltage.toFixed(0) : '-'} V
            </div>
          </>
        )}
      </div>
    </div>
  );
}
