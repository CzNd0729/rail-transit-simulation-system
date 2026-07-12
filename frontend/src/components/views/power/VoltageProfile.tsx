/**
 * VoltageProfile — 接触网电压分布图
 * 基于《需求文档》UI-PWR-01
 * 全线电压曲线，标示变电所位置和列车当前位置
 */
import { useMemo, useState, useCallback, useEffect } from 'react';
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';
import { axisTooltip } from '../../../utils/format';
import type { VoltagePoint } from '../../../types/simulation';

// 模块级缓存，组件切换时不丢失累积数据
let accumulatedCache: VoltagePoint[] = [];
let prevRunState: string = 'idle';

export default function VoltageProfile() {
  const { power, trains, lineLayout, runState } = useSimulationState();
  const trainPosition = trains[0]?.position;
  const trainVoltage = trains[0]?.pantograph_voltage;
  const totalLength = lineLayout?.total_length ?? 3200;

  // 用版本号触发 React 重新渲染
  const [tick, setTick] = useState(0);
  const scheduleTick = useCallback(() => setTick(t => t + 1), []);

  // 新仿真启动时清空上一次的曲线（仅 idle/stopped → running，不含 resumed）
  useEffect(() => {
    if ((prevRunState === 'idle' || prevRunState === 'stopped') && runState === 'running') {
      accumulatedCache = [];
      scheduleTick();
    }
    prevRunState = runState;
  }, [runState, scheduleTick]);

  // 累积新数据点（在 effect 中执行，避免渲染期间触发无限循环）
  useEffect(() => {
    if (power.voltage_profile.length === 0) return;
    const newPoint = power.voltage_profile[0];
    const last = accumulatedCache[accumulatedCache.length - 1];
    if (!last || last.chainage !== newPoint.chainage || last.voltage !== newPoint.voltage) {
      accumulatedCache.push(newPoint);
      scheduleTick();
    }
  }, [power.voltage_profile, scheduleTick]);

  // 按距离排序 + 去重，然后在前段补点填满空白区域
  const voltageCurve = useMemo(() => {
    if (accumulatedCache.length === 0) return power.voltage_profile;

    // 排序 + 去重（用展开避免修改原数组）
    const sorted = [...accumulatedCache].sort((a, b) => a.chainage - b.chainage);
    const deduped: VoltagePoint[] = [];
    for (const p of sorted) {
      const last = deduped[deduped.length - 1];
      if (!last || last.chainage !== p.chainage) deduped.push(p);
    }

    if (deduped.length === 0) return power.voltage_profile;

    // 在第一个真实数据点之前填充插值点，确保从 0 开始有连续曲线
    const firstPoint = deduped[0];
    const fillPoints: VoltagePoint[] = [];
    if (firstPoint.chainage > 0) {
      const step = 50; // 每 50m 插一个点
      let pos = 0;
      while (pos < firstPoint.chainage) {
        const t = pos / firstPoint.chainage;
        const voltage = 1500 + (firstPoint.voltage - 1500) * t;
        fillPoints.push({ chainage: pos, voltage: Math.round(voltage * 10) / 10 });
        pos += step;
      }
    }
    return [...fillPoints, ...deduped];
  }, [power.voltage_profile, tick]);

  // 列车位置在 X 轴的百分比
  const trainPercent = totalLength > 0 && trainPosition != null
    ? (trainPosition / totalLength) * 100
    : null;

  const option = useMemo(() => {
    // 动态 Y 轴：默认 1000-1600，数据超出时自动扩展
    const voltages = voltageCurve.map(p => p.voltage);
    const dataMin = voltages.length > 0 ? Math.min(...voltages) : 1500;
    const dataMax = voltages.length > 0 ? Math.max(...voltages) : 1500;
    const yMin = Math.floor(Math.min(1000, dataMin - 100) / 100) * 100;
    const yMax = Math.ceil(Math.max(1600, dataMax + 100) / 100) * 100;

    return {
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
      min: yMin,
      max: yMax,
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    series: [
      {
        name: '接触网电压',
        type: 'line',
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
    };
  }, [voltageCurve, power.substations, trainPosition, totalLength]);

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">📊 接触网电压分布</div>
      <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        <ReactECharts
          option={option}
          style={{ height: '100%' }}
          notMerge={true}
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
