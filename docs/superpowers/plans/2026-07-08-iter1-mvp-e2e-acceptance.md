# 迭代一 MVP E2E 验收闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `VITE_USE_MOCK=false` 下完成迭代一验收场景 1~4 的可演示闭环，修复 Overview 线路数据不一致、停止统计缺失、Mock CSV 不可用、FPS 恒为 0 等阻塞项。

**Architecture:** 新增 `lineLayoutAdapter` 将后端 `GET /config/line` 与 Mock `mockTrackBlueprint` 统一转为 `LineLayout` 写入 Context；Overview 组件消费 `state.lineLayout`；`simulation_complete.summary` 写入 `stats` 并由 `RunSummaryPanel` 展示；Mock 模式 CSV 从 `chartHistory` 本地导出；`useFps` 驱动状态栏帧率。

**Tech Stack:** React 19 + TypeScript, Vitest, ECharts, FastAPI WebSocket/REST（已有）, Vite env `VITE_USE_MOCK`

## Global Constraints

- 验收线路为 MVP 3 站 2 区间：A(0m) → B(1500m) → C(3200m)，与 `backend/sim_engine/config/track.yaml` 一致
- Mock 模式行为不得回归：`npm test` 与 `VITE_USE_MOCK=true` 演示路径保持可用
- API 消息 camelCase ↔ 内部 snake_case 约定不变（沿用 `apiAdapter.ts`）
- 不修改 `frontend/src/mock/*` 核心动力学逻辑；不实现 TrackView 新功能（迭代二范围）
- 每个 Task 结束：`cd frontend && npm test && npm run build` 必须通过
- 联调环境：`frontend/.env.local` 设 `VITE_USE_MOCK=false`，后端 `uv run uvicorn sim_engine.app:app --reload --port 8000`

## File Map

| 文件 | 职责 |
|------|------|
| `frontend/src/data/mvpLineLayout.ts` | 从 `mockTrackBlueprint` 构建 MVP `LineLayout`（Mock/离线 fallback） |
| `frontend/src/utils/lineLayoutAdapter.ts` | 后端 camelCase line config → `LineLayout` + 剖面 segment 参数 |
| `frontend/src/utils/chartHistoryExport.ts` | `chartHistory` → CSV 字符串 |
| `frontend/src/hooks/useFps.ts` | rAF 计数 → `SET_FPS` |
| `frontend/src/hooks/useLineLayout.ts` | Mock 初始化 / Live REST 拉取线路 |
| `frontend/src/components/export/RunSummaryPanel.tsx` | 停止后统计摘要 UI |
| `frontend/src/context/SimulationContext.tsx` | 新增 `SET_LINE_LAYOUT`、`SET_STATS` |
| `frontend/src/hooks/useWebSocket.ts` | `init_state.config.line` + `simulation_complete.summary` |
| Overview 组件 | 消费统一 `lineLayout` |

---

### Task 1: MVP 线路布局构建器

**Files:**
- Create: `frontend/src/data/mvpLineLayout.ts`
- Create: `frontend/src/utils/lineLayoutAdapter.test.ts`（先写 layout 部分测试）
- Modify: `frontend/src/types/simulation.ts`（如需导出 `ProfileSegment` 类型）

**Interfaces:**
- Produces: `buildMvpLineLayout(gradientSec02?: number): LineLayout`
- Produces: `buildProfileSegments(gradientSec02?: number): ProfileSegment[]` — `{ start_chainage, end_chainage, gradient, speed_limit, is_tunnel }[]`

- [ ] **Step 1: 写失败测试**

`frontend/src/utils/lineLayoutAdapter.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { buildMvpLineLayout, buildProfileSegments } from '../data/mvpLineLayout';

describe('buildMvpLineLayout', () => {
  it('builds 3-station layout matching track.yaml chainages', () => {
    const layout = buildMvpLineLayout();
    expect(layout.total_length).toBe(3200);
    expect(layout.stations.map((s) => s.chainage)).toEqual([0, 1500, 3200]);
    expect(layout.stations[0].name).toBe('A站');
  });

  it('applies gradient override on SEC02 for scenario 2', () => {
    const segs = buildProfileSegments(30);
    const sec02 = segs.find((s) => s.start_chainage === 1500);
    expect(sec02?.gradient).toBe(30);
  });
});
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd frontend && npx vitest run src/utils/lineLayoutAdapter.test.ts`  
Expected: FAIL — module not found

- [ ] **Step 3: 实现 mvpLineLayout.ts**

`frontend/src/data/mvpLineLayout.ts`:

```typescript
import { MOCK_STATIONS, MOCK_SEGMENTS } from '../mock/mockTrackBlueprint';
import type { LineLayout, StationLayout, InterStationSegment } from '../types/simulation';

export interface ProfileSegment {
  start_chainage: number;
  end_chainage: number;
  gradient: number;
  speed_limit: number;
  is_tunnel: boolean;
}

const DEFAULT_STATION_LENGTH = 120;

function toStationLayout(station: (typeof MOCK_STATIONS)[0]): StationLayout {
  return {
    ...station,
    length: DEFAULT_STATION_LENGTH,
    tracks: [{ track_id: 'MAIN', name: '正线', type: 'main', occupied: false }],
    occupancy_rate: 0,
  };
}

function toInterStationSegment(seg: (typeof MOCK_SEGMENTS)[0]): InterStationSegment {
  return {
    start_chainage: seg.start_chainage,
    end_chainage: seg.end_chainage,
    circuits: [{
      id: `${seg.id}_C1`,
      start_chainage: seg.start_chainage,
      end_chainage: seg.end_chainage,
      occupied: false,
      occupied_by: null,
    }],
  };
}

export function buildProfileSegments(gradientSec02?: number): ProfileSegment[] {
  return MOCK_SEGMENTS.map((seg) => ({
    start_chainage: seg.start_chainage,
    end_chainage: seg.end_chainage,
    gradient: seg.id === 'SEC02' && gradientSec02 !== undefined ? gradientSec02 : seg.gradient,
    speed_limit: seg.speed_limit,
    is_tunnel: seg.is_tunnel,
  }));
}

export function buildMvpLineLayout(gradientSec02?: number): LineLayout {
  const profile = buildProfileSegments(gradientSec02);
  return {
    name: '1号线',
    stations: MOCK_STATIONS.map(toStationLayout),
    segments: MOCK_SEGMENTS.map(toInterStationSegment),
    total_length: profile[profile.length - 1].end_chainage,
  };
}
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd frontend && npx vitest run src/utils/lineLayoutAdapter.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/data/mvpLineLayout.ts frontend/src/utils/lineLayoutAdapter.test.ts
git commit -m "feat(frontend): 新增 MVP 线路布局构建器"
```

---

### Task 2: 后端线路配置适配器 + Context 动作

**Files:**
- Create: `frontend/src/utils/lineLayoutAdapter.ts`
- Modify: `frontend/src/context/SimulationContext.tsx`
- Modify: `frontend/src/utils/lineLayoutAdapter.test.ts`

**Interfaces:**
- Produces: `parseApiLineConfig(raw: Record<string, unknown>): LineLayout`
- Produces: `parseApiLineConfig(raw): { layout: LineLayout; profileSegments: ProfileSegment[] }`
- Consumes: `buildMvpLineLayout` as fallback shape reference

- [ ] **Step 1: 写失败测试**

追加到 `lineLayoutAdapter.test.ts`:

```typescript
import { parseApiLineConfig } from './lineLayoutAdapter';

describe('parseApiLineConfig', () => {
  it('converts camelCase backend line to LineLayout', () => {
    const raw = {
      name: '1号线',
      totalLength: 3200,
      stations: [
        { id: 'ST01', name: 'A站', chainage: 0, dwellTime: 30 },
        { id: 'ST02', name: 'B站', chainage: 1500, dwellTime: 30 },
        { id: 'ST03', name: 'C站', chainage: 3200, dwellTime: 30 },
      ],
      segments: [
        { id: 'SEC01', startChainage: 0, endChainage: 1500, gradient: 5, curvature: 800, speedLimit: 80, isTunnel: false },
        { id: 'SEC02', startChainage: 1500, endChainage: 3200, gradient: 0, curvature: 1200, speedLimit: 80, isTunnel: false },
      ],
    };
    const { layout, profileSegments } = parseApiLineConfig(raw);
    expect(layout.total_length).toBe(3200);
    expect(profileSegments[0].gradient).toBe(5);
    expect(layout.stations[1].chainage).toBe(1500);
  });
});
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd frontend && npx vitest run src/utils/lineLayoutAdapter.test.ts`  
Expected: FAIL — parseApiLineConfig not defined

- [ ] **Step 3: 实现 lineLayoutAdapter.ts**

```typescript
import { buildMvpLineLayout, type ProfileSegment } from '../data/mvpLineLayout';
import type { LineLayout, StationLayout, InterStationSegment } from '../types/simulation';

function toStationLayout(raw: Record<string, unknown>): StationLayout {
  const chainage = Number(raw.chainage ?? 0);
  return {
    id: String(raw.id),
    name: String(raw.name),
    chainage,
    dwell_time: Number(raw.dwellTime ?? raw.dwell_time ?? 30),
    platform_half_length: 15,
    is_terminus: chainage === 0,
    sort_order: 0,
    length: 120,
    tracks: [{ track_id: 'MAIN', name: '正线', type: 'main', occupied: false }],
    occupancy_rate: 0,
  };
}

export function parseApiLineConfig(raw: Record<string, unknown>): {
  layout: LineLayout;
  profileSegments: ProfileSegment[];
} {
  const stations = (raw.stations as Record<string, unknown>[] | undefined) ?? [];
  const segments = (raw.segments as Record<string, unknown>[] | undefined) ?? [];

  const profileSegments: ProfileSegment[] = segments.map((s) => ({
    start_chainage: Number(s.startChainage ?? s.start_chainage),
    end_chainage: Number(s.endChainage ?? s.end_chainage),
    gradient: Number(s.gradient),
    speed_limit: Number(s.speedLimit ?? s.speed_limit),
    is_tunnel: Boolean(s.isTunnel ?? s.is_tunnel),
  }));

  const layout: LineLayout = {
    name: String(raw.name ?? '1号线'),
    stations: stations.map(toStationLayout),
    segments: segments.map((s) => ({
      start_chainage: Number(s.startChainage ?? s.start_chainage),
      end_chainage: Number(s.endChainage ?? s.end_chainage),
      circuits: [{
        id: `${s.id}_C1`,
        start_chainage: Number(s.startChainage ?? s.start_chainage),
        end_chainage: Number(s.endChainage ?? s.end_chainage),
        occupied: false,
        occupied_by: null,
      }],
    })),
    total_length: Number(raw.totalLength ?? raw.total_length ?? profileSegments.at(-1)?.end_chainage ?? 3200),
  };

  return { layout, profileSegments };
}

export function getDefaultLineLayout(): LineLayout {
  return buildMvpLineLayout();
}
```

- [ ] **Step 4: 扩展 SimulationContext**

在 `SimulationAction` 增加：

```typescript
| { type: 'SET_LINE_LAYOUT'; payload: LineLayout }
| { type: 'SET_STATS'; payload: Partial<SimulationStats> }
```

Reducer cases:

```typescript
case 'SET_LINE_LAYOUT':
  return { ...state, lineLayout: action.payload };

case 'SET_STATS':
  return { ...state, stats: { ...state.stats, ...action.payload } };
```

`RUNTIME_UPDATE` 中当 `runState === 'running'` 时不覆盖 stats；`CLEAR_CHART_HISTORY` 时可选 `stats` 归零（与 `useSimulation` stop 对齐）。

- [ ] **Step 5: 运行测试 + build**

Run: `cd frontend && npx vitest run src/utils/lineLayoutAdapter.test.ts && npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/lineLayoutAdapter.ts frontend/src/context/SimulationContext.tsx frontend/src/utils/lineLayoutAdapter.test.ts
git commit -m "feat(frontend): 线路配置适配与 Context lineLayout/stats"
```

---

### Task 3: 线路初始化 Hook（Mock + Live）

**Files:**
- Create: `frontend/src/hooks/useLineLayout.ts`
- Modify: `frontend/src/hooks/useBootstrap.ts`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `parseApiLineConfig`, `buildMvpLineLayout`, `getLineConfig()` from `api.ts`
- Produces: dispatch `SET_LINE_LAYOUT` on mount

- [ ] **Step 1: 实现 useLineLayout.ts**

```typescript
import { useEffect } from 'react';
import { useSimulationDispatch, useSimulationState } from '../context/SimulationContext';
import { getLineConfig } from '../services/api';
import { parseApiLineConfig } from '../utils/lineLayoutAdapter';
import { buildMvpLineLayout } from '../data/mvpLineLayout';
import { USE_MOCK } from '../utils/constants';

export function useLineLayout() {
  const dispatch = useSimulationDispatch();
  const { lineLayout, params } = useSimulationState();

  useEffect(() => {
    if (lineLayout) return;

    if (USE_MOCK) {
      dispatch({
        type: 'SET_LINE_LAYOUT',
        payload: buildMvpLineLayout(params.track.gradient),
      });
      return;
    }

    getLineConfig()
      .then((raw) => {
        const { layout } = parseApiLineConfig(raw as Record<string, unknown>);
        dispatch({ type: 'SET_LINE_LAYOUT', payload: layout });
      })
      .catch((err) => {
        console.warn('[LineLayout] 无法加载后端线路，使用 MVP 默认', err);
        dispatch({ type: 'SET_LINE_LAYOUT', payload: buildMvpLineLayout() });
      });
  }, [dispatch, lineLayout, params.track.gradient]);
}
```

- [ ] **Step 2: App.tsx 挂载**

```typescript
import { useLineLayout } from './hooks/useLineLayout';

function AppInner() {
  useBootstrap();
  useLineLayout();
  // ...
}
```

- [ ] **Step 3: params.track.gradient 变化时重建 Mock 布局**

在 `useLineLayout` 增加：Mock 模式下监听 `params.track.gradient`，dispatch 更新 layout（Scenario 2）。

- [ ] **Step 4: 验证**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useLineLayout.ts frontend/src/App.tsx
git commit -m "feat(frontend): Mock/Live 线路布局启动引导"
```

---

### Task 4: Overview 纵断面与线路图对齐

**Files:**
- Modify: `frontend/src/components/views/overview/LineProfile.tsx`
- Modify: `frontend/src/components/views/overview/LineDiagram.tsx`
- Modify: `frontend/src/components/views/overview/SpeedPositionCurve.tsx`
- Create: `frontend/src/utils/profileChart.ts`（共享 `toStepData`）

**Interfaces:**
- Consumes: `state.lineLayout`, `buildProfileSegments(params.track.gradient)` in Mock
- Consumes: `parseApiLineConfig` profile segments when live (store in module-level or derive from layout + GET config cache)

**简化方案：** 在 Context 增加 `profileSegments: ProfileSegment[] | null` 或在 `lineLayoutAdapter` 返回后存于 ref。最小改动：LineProfile 直接从 `mockTrackBlueprint` + `params.track.gradient` 在 Mock 模式读取；Live 模式从 `getLineConfig` 结果缓存到 Context 新字段 `profileSegments`。

- [ ] **Step 1: Context 增加 profileSegments（可选字段）**

`AppState.profileSegments: ProfileSegment[] | null`  
`SET_LINE_LAYOUT` payload 扩展为 `{ layout, profileSegments }` 或单独 action `SET_PROFILE_SEGMENTS`。

- [ ] **Step 2: 重写 LineProfile.tsx**

从 `useSimulationState()` 读取 `profileSegments ?? buildProfileSegments(params.track.gradient)`，复用 `toStepData` 生成 ECharts option（参考 `LineProfileDetail.tsx`，单 Y 轴坡度 + 车站 markPoint）。

- [ ] **Step 3: LineDiagram 改用 context.lineLayout**

```typescript
const { lineLayout, trains } = useSimulationState();
const layout = lineLayout ?? buildMvpLineLayout();
// 移除 useState(mockLineData) 和 useMockTrain fallback
const displayTrains = trains;
if (!lineLayout) return <div className="panel">加载线路...</div>;
```

- [ ] **Step 4: SpeedPositionCurve xAxis.max 动态化**

```typescript
const maxPos = lineLayout?.total_length ?? 3200;
xAxis: { max: maxPos }
```

- [ ] **Step 5: 手动验证 Mock**

Run: `cd frontend && npm run dev`（默认 Mock）  
Expected: 综合视图线路图 3 站、纵断面 A/B/C 标注、列车动画范围 0~3200m

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/views/overview/*.tsx frontend/src/utils/profileChart.ts frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): Overview 线路与 MVP 3 站数据对齐"
```

---

### Task 5: simulation_complete 统计摘要

**Files:**
- Create: `frontend/src/components/export/RunSummaryPanel.tsx`
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/utils/apiAdapter.ts`（`parseSimulationSummary`）
- Modify: `frontend/src/App.tsx` 或 `ExportPanel.tsx` 挂载摘要面板

**Interfaces:**
- Produces: `parseSimulationSummary(data: Record<string, unknown>): Partial<SimulationStats>`

后端 `simulation_complete.data.summary` 字段：`steps`, `totalTime`, `avgSpeed`, `maxSpeed`（camelCase）

- [ ] **Step 1: 写失败测试**

`frontend/src/utils/apiAdapter.test.ts` 追加：

```typescript
import { parseSimulationSummary } from './apiAdapter';

it('maps complete summary to SimulationStats fields', () => {
  const stats = parseSimulationSummary({
    steps: 100,
    totalTime: 120.5,
    avgSpeed: 45.2,
    maxSpeed: 64,
  });
  expect(stats.trip_time).toBe(120.5);
  expect(stats.avg_speed).toBe(45.2);
  expect(stats.max_speed).toBe(64);
});
```

- [ ] **Step 2: 实现 parseSimulationSummary + useWebSocket 扩展**

`useWebSocket.ts` case `simulation_complete`:

```typescript
case 'simulation_complete': {
  dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
  const summary = message.data?.summary;
  if (summary && typeof summary === 'object') {
    dispatch({
      type: 'SET_STATS',
      payload: parseSimulationSummary(summary as Record<string, unknown>),
    });
  }
  break;
}
```

- [ ] **Step 3: RunSummaryPanel 组件**

在 `ExportPanel` 上方或内部，当 `runState === 'stopped' && stats.trip_time > 0` 显示：

```
运行摘要
总时长: {formatSimTime(stats.trip_time)}
平均速度: {stats.avg_speed.toFixed(1)} km/h
最高速度: {stats.max_speed.toFixed(1)} km/h
```

Mock 模式：`useMockReplay` 在 replay 结束时 dispatch 本地 stats（从 frames 最后一帧计算）。

- [ ] **Step 4: 运行测试**

Run: `cd frontend && npm test`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/export/RunSummaryPanel.tsx frontend/src/hooks/useWebSocket.ts frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts
git commit -m "feat(frontend): 仿真完成统计摘要面板"
```

---

### Task 6: Mock CSV 导出 + FPS 状态栏

**Files:**
- Create: `frontend/src/utils/chartHistoryExport.ts`
- Create: `frontend/src/utils/chartHistoryExport.test.ts`
- Create: `frontend/src/hooks/useFps.ts`
- Modify: `frontend/src/components/export/ExportPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: chartHistoryExport 测试与实现**

```typescript
export function chartHistoryToCsv(history: ChartHistory): string {
  const header = 'time,position,speed,acceleration\n';
  const rows = history.speedTime.map(([t, speed], i) => {
    const pos = history.speedPosition[i]?.[0] ?? '';
    const accel = history.accelTime[i]?.[1] ?? '';
    return `${t},${pos},${speed},${accel}`;
  });
  return header + rows.join('\n');
}
```

- [ ] **Step 2: ExportPanel 双路径**

```typescript
import { USE_MOCK } from '../../utils/constants';
import { useSimulationState } from '../../context/SimulationContext';
import { chartHistoryToCsv } from '../../utils/chartHistoryExport';

const { chartHistory } = useSimulationState();

const handleExportCSV = async () => {
  if (USE_MOCK) {
    if (chartHistory.speedTime.length === 0) {
      alert('暂无仿真数据，请先运行仿真');
      return;
    }
    const csv = chartHistoryToCsv(chartHistory);
    // blob download...
    return;
  }
  // 现有 REST exportCSV()
};
```

- [ ] **Step 3: useFps hook**

```typescript
export function useFps() {
  const dispatch = useSimulationDispatch();
  useEffect(() => {
    let frames = 0;
    let last = performance.now();
    let raf = 0;
    const tick = (now: number) => {
      frames++;
      if (now - last >= 1000) {
        dispatch({ type: 'SET_FPS', payload: frames });
        frames = 0;
        last = now;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [dispatch]);
}
```

在 `App.tsx` 调用 `useFps()`。

- [ ] **Step 4: 测试 + build**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS；StatusBar FPS 显示非 0

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/chartHistoryExport.ts frontend/src/utils/chartHistoryExport.test.ts frontend/src/hooks/useFps.ts frontend/src/components/export/ExportPanel.tsx frontend/src/App.tsx
git commit -m "feat(frontend): Mock CSV 导出与 FPS 计数"
```

---

### Task 7: E2E 验收执行与 gap 修复

**Files:**
- Modify: `frontend/.env.example`（补充 `.env.local` 联调说明）
- Create: `docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md`（验收记录模板）

- [ ] **Step 1: 启动联调环境**

终端 1:
```bash
cd backend && uv run uvicorn sim_engine.app:app --reload --port 8000
```

终端 2 — 创建 `frontend/.env.local`:
```
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000/ws
```
```bash
cd frontend && npm run dev
```

- [ ] **Step 2: 场景 1 清单**

| 步骤 | 预期 |
|------|------|
| 综合视图 → 运行 | 3 站线路图、列车从 A 移动、速度-位置曲线更新 |
| 车辆视图 | 速度/加速度曲线上升→平→降，工况牵引→惰行→制动 |
| 到 B/C 站 | 停稳 30s，时钟继续 |
| 终到 C | runState=stopped，摘要面板有数据 |

- [ ] **Step 3: 场景 2 — 坡度 30‰**

参数面板 SEC02 坡度改 30（或 `params.track.gradient=30`）→ 重新运行 → B→C 段运行时间变长、加速度曲线差异可见

- [ ] **Step 4: 场景 3 — 控制交互**

暂停 → 曲线冻结；继续 → 恢复；停止 → 摘要；10× 倍率 → 明显加速

- [ ] **Step 5: 场景 4 — 质量 220t**

暂停/空闲改质量 → 运行 → 加速度降低、站间时间变长

- [ ] **Step 6: Mock 回归**

`VITE_USE_MOCK=true` → 车辆视图 + Overview + CSV 本地导出正常

- [ ] **Step 7: 后端测试**

Run: `cd backend && uv run pytest`  
Expected: 全部 PASS

- [ ] **Step 8: 填写验收记录并 Commit**

```bash
git add docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md frontend/.env.example
git commit -m "docs: 迭代一 MVP E2E 验收清单与环境说明"
```

---

## Spec Coverage Checklist

| MVP 需求 | Task |
|----------|------|
| 场景 1 综合+车辆双视图联调 | Task 3~5, 7 |
| 场景 2 坡度影响 | Task 3~4（gradient 驱动 profile + mock 动力学已有） |
| 场景 3 启停暂停 + 停止摘要 | Task 5, 7 |
| 场景 4 参数编辑 | 已有 UI-PARAM + Task 7 验证 |
| UI-VW-01 纵断面 | Task 4 |
| UI-VW-02 列车动画 | Task 4 |
| UI-VW-03 速度-位置曲线 | Task 4（max 动态） |
| UI-EXPORT-01 CSV | Task 6 |
| UI-BAR-02 FPS | Task 6 |
| vehicle-backend-integration E2E | Task 7 |

## Self-Review Notes

- **Coverage:** 四条验收场景均在 Task 7 有明确步骤；Overview 对齐覆盖场景 1 综合视图部分。
- **Placeholder scan:** 无 TBD；profileSegments 存储方案在 Task 4 已给出两种可选实现，实施时选 Context 字段方案。
- **Type consistency:** `parseApiLineConfig` / `buildMvpLineLayout` 均产出 `LineLayout`；summary 映射使用 snake_case `SimulationStats`。
- **Scope:** 不含 TrackView 深化、VHC-04/05、后端 VHC-08 精度测试增强（可另开任务）。

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-08-iter1-mvp-e2e-acceptance.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每 Task 派生子 agent，Task 间审查
2. **Inline Execution** — 本会话用 executing-plans 批量执行，检查点暂停

**Which approach?**
