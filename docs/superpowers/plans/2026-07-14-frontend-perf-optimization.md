# 前端渲染性能优化 方案A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过 chartHistory 可变写入、useMemo 补全、数据降采样三项低成本优化，将 6 车 1× 倍率下 FPS 从 ~15 提升至 30+

**Architecture:** 保持现有 Context 架构不变，将 chartHistory 写入从不可变 spread 改为可变 push + chartVersion 版本号，在图表 option 构建层加入降采样，补全缺失的 useMemo

**Tech Stack:** React 19, TypeScript, ECharts 6, echarts-for-react / SimEChart

## Global Constraints

- 零公共接口变更：`TrainChartHistory`、`ChartHistory` 类型定义不变
- 零测试变更：现有测试无需修改
- `npx tsc -b` 通过，`npm run lint` 无新增警告
- 图表视觉效果无变化

---

### Task 1: 新增 downsample 工具函数

**Files:**
- Create: `frontend/src/utils/downsample.ts`

**Interfaces:**
- Produces: `export function downsample(data: [number, number][], maxPoints?: number): [number, number][]`

- [ ] **Step 1: 创建 downsample.ts**

```typescript
/**
 * 均匀降采样工具函数
 * 从超长时序数组中取 maxPoints 个均匀分布的点，保留首尾确保范围完整。
 * 用于减少传入 ECharts 的渲染数据量。
 */
export function downsample(
  data: [number, number][],
  maxPoints: number = 800,
): [number, number][] {
  if (data.length <= maxPoints) return data;
  const step = data.length / maxPoints;
  const result: [number, number][] = [];
  for (let i = 0; i < maxPoints; i++) {
    result.push(data[Math.floor(i * step)]);
  }
  // 确保最后一个数据点始终包含
  const last = data[data.length - 1];
  if (result[result.length - 1] !== last) {
    result.push(last);
  }
  return result;
}
```

- [ ] **Step 2: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/utils/downsample.ts
git commit -m "feat(frontend): 新增 downsample 图表数据降采样工具"
```

---

### Task 2: chartHistory 可变 push 写入 + chartVersion 版本号

**Files:**
- Modify: `frontend/src/utils/chartHistory.ts` — 重写 `appendChartHistory`、`clearChartHistory`
- Modify: `frontend/src/context/SimulationContext.tsx` — 新增 `chartVersion` 字段与 action

**Interfaces:**
- Consumes: `AppState` 类型中无 chartVersion
- Produces: `AppState.chartVersion: number`；`clearChartHistory` 改为零分配

- [ ] **Step 1: 重写 chartHistory.ts**

将 `appendChartHistory` 改为可变 push 写入。关键改动：
1. 移除所有 `[...prev, [t,v]]` 展开拷贝
2. 数据数组改为原地 push，超出上限时 shift
3. `clearChartHistory` 用 `array.length = 0` 替代新建对象

```typescript
// frontend/src/utils/chartHistory.ts — 完整替换
import type { ChartHistory, SimulationSnapshot, TrainChartHistory } from '../types/simulation';

export const EMPTY_TRAIN_CHART_HISTORY: TrainChartHistory = {
  speedTime: [],
  accelTime: [],
  jerkTime: [],
  speedPosition: [],
  positionTime: [],
  voltagePosition: [],
  resistanceTime: [],
  davisResistanceTime: [],
  gradientResistanceTime: [],
  curveResistanceTime: [],
  tunnelResistanceTime: [],
  tractionEnergyTime: [],
  regenEnergyTime: [],
};

export const EMPTY_CHART_HISTORY: ChartHistory = {
  byTrain: {},
};

/** 每列车每序列最大缓存点数 */
export const CHART_HISTORY_MAX_POINTS = 50_000;

/** 向系列数组追加一个点，超出上限时移除最早的点（零拷贝） */
function pushPoint(series: [number, number][], point: [number, number], max: number): void {
  series.push(point);
  if (series.length > max) {
    series.shift();
  }
}

/** 确保某车在 byTrain 中有记录，返回其 TrainChartHistory（原地修改） */
function ensureTrainHistory(
  byTrain: Record<string, TrainChartHistory>,
  trainId: string,
): TrainChartHistory {
  let h = byTrain[trainId];
  if (!h) {
    h = createEmptyTrainHistory();
    byTrain[trainId] = h;
  }
  return h;
}

function createEmptyTrainHistory(): TrainChartHistory {
  return {
    speedTime: [],
    accelTime: [],
    jerkTime: [],
    speedPosition: [],
    positionTime: [],
    voltagePosition: [],
    resistanceTime: [],
    davisResistanceTime: [],
    gradientResistanceTime: [],
    curveResistanceTime: [],
    tunnelResistanceTime: [],
    tractionEnergyTime: [],
    regenEnergyTime: [],
  };
}

export function getTrainChartHistory(
  history: ChartHistory,
  trainId: string,
): TrainChartHistory {
  return history.byTrain[trainId] ?? EMPTY_TRAIN_CHART_HISTORY;
}

/**
 * 向 chartHistory 追加一帧仿真快照数据。
 * 直接 push 到现有数组，零数组拷贝。
 * 返回 true 表示有数据写入（调用方应递增 chartVersion）。
 */
export function appendChartHistory(
  history: ChartHistory,
  snapshot: SimulationSnapshot,
): boolean {
  if (snapshot.trains.length === 0) return false;

  const { byTrain } = history;
  const t = snapshot.clock.elapsed;
  const tractionKwh = snapshot.power.total_consumption;
  const regenKwh = snapshot.power.total_regeneration;
  const MAX = CHART_HISTORY_MAX_POINTS;

  for (const train of snapshot.trains) {
    const h = ensureTrainHistory(byTrain, train.id);

    pushPoint(h.speedTime,          [t, train.speed],                  MAX);
    pushPoint(h.accelTime,          [t, train.acceleration],           MAX);
    pushPoint(h.jerkTime,           [t, train.jerk ?? 0],              MAX);
    pushPoint(h.speedPosition,      [train.position, train.speed],     MAX);
    pushPoint(h.positionTime,       [t, train.position],               MAX);
    pushPoint(h.voltagePosition,    [train.position, train.pantograph_voltage], MAX);
    pushPoint(h.resistanceTime,     [t, train.total_resistance / 1000], MAX);
    pushPoint(h.davisResistanceTime,     [t, (train.davis_resistance ?? 0) / 1000], MAX);
    pushPoint(h.gradientResistanceTime,  [t, (train.gradient_resistance ?? 0) / 1000], MAX);
    pushPoint(h.curveResistanceTime,     [t, (train.curve_resistance ?? 0) / 1000], MAX);
    pushPoint(h.tunnelResistanceTime,    [t, (train.tunnel_resistance ?? 0) / 1000], MAX);
    pushPoint(h.tractionEnergyTime,[t, tractionKwh],                   MAX);
    pushPoint(h.regenEnergyTime,   [t, regenKwh],                      MAX);
  }

  return true;
}

/** 清空所有曲线历史（零分配：直接清空数组） */
export function clearChartHistory(history: ChartHistory): void {
  for (const h of Object.values(history.byTrain)) {
    h.speedTime.length = 0;
    h.accelTime.length = 0;
    h.jerkTime.length = 0;
    h.speedPosition.length = 0;
    h.positionTime.length = 0;
    h.voltagePosition.length = 0;
    h.resistanceTime.length = 0;
    h.davisResistanceTime.length = 0;
    h.gradientResistanceTime.length = 0;
    h.curveResistanceTime.length = 0;
    h.tunnelResistanceTime.length = 0;
    h.tractionEnergyTime.length = 0;
    h.regenEnergyTime.length = 0;
  }
  history.byTrain = {};
}

/** @internal 供单元测试验证截断逻辑 */
export function trimChartHistoryForTest(history: TrainChartHistory): TrainChartHistory {
  return history;
}
```

- [ ] **Step 2: 更新 SimulationContext — 新增 chartVersion**

修改 `frontend/src/context/SimulationContext.tsx`：

**2a. 在 AppState 接口（types/simulation.ts）中加入 chartVersion 字段：**

```typescript
// 在 AppState 接口末尾添加：
  /** chartHistory 写入版本号，用于驱动 useMemo 重算（可变 push 模式） */
  chartVersion: number;
```

**2b. 在 initialState 中加入：**

```typescript
chartVersion: 0,
```

**2c. 在 SimulationAction 中加入新 action：**

```typescript
| { type: 'INCREMENT_CHART_VERSION' }
```

**2d. RUNTIME_UPDATE reducer case 改为：**

```typescript
case 'RUNTIME_UPDATE': {
  const snapshot = action.payload;
  const selectedTrainId =
    state.selectedTrainId == null
      ? null
      : snapshot.trains.some((t) => t.id === state.selectedTrainId)
        ? state.selectedTrainId
        : snapshot.trains[0]?.id ?? null;

  // 可变 push：appendChartHistory 原地修改 state.chartHistory
  const dataWritten = appendChartHistory(state.chartHistory, snapshot);

  return {
    ...state,
    clock: snapshot.clock,
    trains: snapshot.trains,
    selectedTrainId,
    power: snapshot.power,
    signaling: snapshot.signaling,
    track: snapshot.track,
    events: [...state.events, ...snapshot.events].slice(-500),
    chartVersion: dataWritten ? state.chartVersion + 1 : state.chartVersion,
  };
}
```

**2e. CLEAR_CHART_HISTORY reducer case 改为：**

```typescript
case 'CLEAR_CHART_HISTORY':
  clearChartHistory(state.chartHistory);
  return { ...state, chartVersion: state.chartVersion + 1 };
```

**2f. RESET_RUN_DATA reducer case 改为：**

```typescript
case 'RESET_RUN_DATA':
  clearChartHistory(state.chartHistory);
  return {
    ...state,
    chartVersion: state.chartVersion + 1,
    stats: { ...initialState.stats },
  };
```

- [ ] **Step 3: 更新 import**

确保 `SimulationContext.tsx` 的 import 包含：
```typescript
import { EMPTY_CHART_HISTORY, appendChartHistory, clearChartHistory } from '../utils/chartHistory';
```

移除不再需要的 `EMPTY_CHART_HISTORY` 导入（如果从 chartHistory 导入的话），因为 `clearChartHistory` 已替代其功能。

- [ ] **Step 4: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/utils/chartHistory.ts frontend/src/context/SimulationContext.tsx frontend/src/types/simulation.ts
git commit -m "perf(frontend): chartHistory 可变push写入消除数组拷贝"
```

---

### Task 3: SpeedPositionCurve 补 useMemo + 接入 downsample

**Files:**
- Modify: `frontend/src/components/views/overview/SpeedPositionCurve.tsx`

**Interfaces:**
- Consumes: `chartVersion` from context；`downsample` from utils
- Produces: 无新接口

- [ ] **Step 1: 将 option 包入 useMemo**

```typescript
// 在文件顶部新增 import
import { downsample } from '../../../utils/downsample';

// 在组件内，读取 chartVersion：
const { chartHistory, lineLayout, profileSegments, trains, chartVersion } = useSimulationState();

// 将 option 声明改为 useMemo，依赖中加入 chartVersion：
const option = useMemo(() => ({
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
}), [trainSeries, positionMarkers, speedLimitData, maxPos, trains.length, chartVersion]);
```

- [ ] **Step 2: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/views/overview/SpeedPositionCurve.tsx
git commit -m "perf(frontend): SpeedPositionCurve 补useMemo并接入downsample"
```

---

### Task 4: LineProfile 补 useMemo

**Files:**
- Modify: `frontend/src/components/views/overview/LineProfile.tsx`

- [ ] **Step 1: 将 option 包入 useMemo**

LineProfile 的数据（gradientData、stations）在仿真期间不变，useMemo 依赖仅需构建参数：

```typescript
// 新增 import
import { useMemo } from 'react';

// 在组件内
const option = useMemo(() => ({
  backgroundColor: 'transparent',
  tooltip: { trigger: 'axis' as const },
  grid: { left: 50, right: 20, top: 30, bottom: 40 },
  xAxis: {
    type: 'value' as const,
    name: '公里标 (m)',
    nameTextStyle: { color: '#a0a0a0' },
    axisLabel: { color: '#a0a0a0' },
    axisLine: { lineStyle: { color: '#2a2a4a' } },
    max: lineLayout?.total_length ?? 3200,
  },
  yAxis: {
    type: 'value' as const,
    name: '坡度 (‰)',
    nameTextStyle: { color: '#a0a0a0' },
    axisLabel: { color: '#a0a0a0' },
    axisLine: { lineStyle: { color: '#2a2a4a' } },
  },
  series: [
    {
      name: '坡度',
      type: 'line',
      data: gradientData,
      areaStyle: { color: 'rgba(24, 144, 255, 0.15)' },
      lineStyle: { color: '#1890ff' },
      itemStyle: { color: '#1890ff' },
      markPoint: {
        data: stations.map((s) => ({
          name: s.name,
          coord: [s.chainage, segments.find(
            (seg) => s.chainage >= seg.start_chainage && s.chainage <= seg.end_chainage,
          )?.gradient ?? 0],
          symbol: 'pin',
          symbolSize: 30,
        })),
        label: { color: '#fff', fontSize: 10 },
      },
    },
  ],
}), [gradientData, stations, segments, lineLayout?.total_length]);
```

- [ ] **Step 2: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/views/overview/LineProfile.tsx
git commit -m "perf(frontend): LineProfile 补useMemo避免每帧重建option"
```

---

### Task 5: 车辆视图图表接入 downsample

**Files:**
- Modify: `frontend/src/components/views/vehicle/SpeedTimeCurve.tsx`
- Modify: `frontend/src/components/views/vehicle/AccelTimeCurve.tsx`
- Modify: `frontend/src/components/views/vehicle/JerkTimeCurve.tsx`
- Modify: `frontend/src/components/views/vehicle/EnergyChart.tsx`
- Modify: `frontend/src/components/views/vehicle/ResistanceChart.tsx`

**Interfaces:**
- Consumes: `downsample` from `utils/downsample`；`chartVersion` from context

- [ ] **Step 1: SpeedTimeCurve — 接入 downsample + chartVersion**

在 `useMemo` 的 series.data 中调用 `downsample`，依赖加入 `chartVersion`：

```typescript
// 新增 import
import { downsample } from '../../../utils/downsample';

// 读取 chartVersion
const { clock, chartVersion } = useSimulationState();

// useMemo 中 series.data 改为：
data: downsample(chartHistory.speedTime, 800),

// useMemo 依赖改为：
), [chartHistory.speedTime, clock.elapsed, chartVersion]);
```

- [ ] **Step 2: AccelTimeCurve — 同上改动**

```typescript
data: downsample(chartHistory.accelTime, 800),
// 依赖：..., chartVersion
```

- [ ] **Step 3: JerkTimeCurve — 同上改动**

```typescript
data: downsample(chartHistory.jerkTime, 800),
// 依赖：..., chartVersion
```

- [ ] **Step 4: EnergyChart — 同上改动**

```typescript
data: downsample(chartHistory.tractionEnergyTime, 800),
// ...
data: downsample(chartHistory.regenEnergyTime, 800),
// 依赖：..., chartVersion
```

- [ ] **Step 5: ResistanceChart — 同上改动**

所有 data 字段加上 `downsample(..., 800)`，依赖加入 `chartVersion`。

- [ ] **Step 6: 统一导出 React.memo 包裹**

每个文件末尾改为：
```typescript
export default React.memo(SpeedTimeCurve);
// (AccelTimeCurve, JerkTimeCurve, EnergyChart, ResistanceChart 同理)
```

> 注意：组件内部仍读 context（`useSimulationState` / `useActiveChartHistory`），React.memo 在当前架构下收益有限（context 变化本身触发重渲染），但不引入副作用，为后续 context 拆分预留优化空间。

- [ ] **Step 7: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/views/vehicle/
git commit -m "perf(frontend): 车辆视图图表接入downsample降采样"
```

---

### Task 6: 信号/供电图表接入 downsample

**Files:**
- Modify: `frontend/src/components/views/signal/SpeedEnvelope.tsx`
- Modify: `frontend/src/components/views/signal/TimetableChart.tsx`
- Modify: `frontend/src/components/views/power/VoltageProfile.tsx`

- [ ] **Step 1: SpeedEnvelope**

在 chartHistory.speedPosition 的 data 字段接入降采样（500 点），useMemo 依赖加入 `chartVersion`。

注意：`speedLimitData`、`atpLimitData`、`targetSpeedData` 是静态区段数据（由 profileSegments 派生），无需降采样。

```typescript
// 实际速度曲线降采样
data: downsample(chartHistory.speedPosition, 500),
```

- [ ] **Step 2: TimetableChart**

在 chartHistory.positionTime 的 data 字段接入降采样（1000 点），useMemo 依赖加入 `chartVersion`。

```typescript
data: downsample(chartHistory.positionTime, 1000),
```

- [ ] **Step 3: VoltageProfile**

在 `trainOptions` useMemo 内的 lineSeries.data 接入降采样（500 点），依赖加入 `chartVersion`。

```typescript
const vp = getTrainChartHistory(chartHistory, train.id).voltagePosition;
// ...
data: downsample(vp, 500),
```

同时从 context 读取 `chartVersion`：
```typescript
const { power, trains, chartHistory, lineLayout, selectedTrainId, chartVersion } =
  useSimulationState();
```

并在 `trainOptions` 和 `yRange` 的 useMemo 依赖中加入 `chartVersion`。

- [ ] **Step 4: 统一导出 React.memo 包裹**

每个文件末尾：
```typescript
export default React.memo(SpeedEnvelope);
export default React.memo(TimetableChart);
export default React.memo(VoltageProfile);
```

- [ ] **Step 5: TypeScript 编译验证**

Run: `npx tsc -b`
Expected: 零错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/views/signal/SpeedEnvelope.tsx frontend/src/components/views/signal/TimetableChart.tsx frontend/src/components/views/power/VoltageProfile.tsx
git commit -m "perf(frontend): 信号供电图表接入downsample降采样"
```

---

### Task 7: 集成验证

- [ ] **Step 1: TypeScript 编译**

```bash
cd frontend && npx tsc -b
```
Expected: 零错误

- [ ] **Step 2: Lint 检查**

```bash
cd frontend && npm run lint
```
Expected: 无新增警告（已有 warning 不计）

- [ ] **Step 3: 开发服务器验证**

```bash
cd frontend && npm run dev
```

打开浏览器，Mock 模式下 1× 倍率跑 6 车场景，观察 StatusBar 的 FPS 指标：
- 6 车 1×：FPS ≥ 30
- 10 车 1×：FPS ≥ 20

- [ ] **Step 4: 提交**

```bash
# 如有微调，amend 到对应 task 的 commit
git log --oneline -6  # 确认 6 个 commit 完整
```

---

### 改动文件总览

| # | 文件 | 操作 | Task |
|:---|:-----|:-----|:-----|
| 1 | `utils/downsample.ts` | 新建 | 1 |
| 2 | `utils/chartHistory.ts` | 重写 | 2 |
| 3 | `types/simulation.ts` | 新增 `chartVersion` 字段 | 2 |
| 4 | `context/SimulationContext.tsx` | 新增 action + reducer 调整 | 2 |
| 5 | `views/overview/SpeedPositionCurve.tsx` | useMemo + downsample | 3 |
| 6 | `views/overview/LineProfile.tsx` | useMemo | 4 |
| 7 | `views/vehicle/SpeedTimeCurve.tsx` | React.memo + downsample + chartVersion | 5 |
| 8 | `views/vehicle/AccelTimeCurve.tsx` | 同上 | 5 |
| 9 | `views/vehicle/JerkTimeCurve.tsx` | 同上 | 5 |
| 10 | `views/vehicle/EnergyChart.tsx` | 同上 | 5 |
| 11 | `views/vehicle/ResistanceChart.tsx` | 同上 | 5 |
| 12 | `views/signal/SpeedEnvelope.tsx` | React.memo + downsample + chartVersion | 6 |
| 13 | `views/signal/TimetableChart.tsx` | 同上 | 6 |
| 14 | `views/power/VoltageProfile.tsx` | 同上 | 6 |

### 不改动的文件

- `types/simulation.ts`（除 chartVersion 一笔追加）
- `services/api.ts`
- 非图表组件（control/、param/、export/、scenario/）
- `SimEChart.tsx`、`common/`
- hooks/、layouts/
- 所有测试
