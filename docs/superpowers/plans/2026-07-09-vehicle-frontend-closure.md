# 车辆系统前端闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复车辆视图停止/摘要生命周期 Bug，完成迭代一 UI-VHC-01~03 + UI-PARAM-01 的 Mock/Live 验收（场景 1、3、4）。

**Architecture:** 拆分 chart 与 stats 清除逻辑；start 清数据、stop 保留曲线并写 stats；Mock stop 补摘要；VehicleView 隐藏 iter3 占位；清理重复 hook。

**Tech Stack:** React 19, TypeScript, Vitest, ECharts, Vite env `VITE_USE_MOCK`

## Global Constraints

- **仅改 `frontend/`**，不修改后端
- Mock 模式必须保持可用：`VITE_USE_MOCK=true` 时全部 `npm test` PASS
- 不实现 UI-VHC-04/05（阻力/能耗图表）
- 不实现线路区段选择（Track 模块负责，场景 2 只读验证）
- 每个 Task 结束：`cd frontend && npm test && npm run build`
- Live 联调：`frontend/.env.local` 设 `VITE_USE_MOCK=false`，后端 `uv run uvicorn sim_engine.app:app --reload --port 8000`

## File Map

| 文件 | 职责 |
|------|------|
| `frontend/src/context/SimulationContext.tsx` | 拆分 CLEAR_CHART / RESET_RUN_DATA |
| `frontend/src/hooks/useSimulation.ts` | start/stop 生命周期 |
| `frontend/src/hooks/useMockReplay.ts` | Mock stop 摘要 |
| `frontend/src/pages/VehicleView.tsx` | 隐藏 iter3 占位 |
| `frontend/src/components/views/vehicle/ModeIndicator.tsx` | 站停显示 |
| `frontend/src/utils/format.ts` | `getDisplayMode` 工具 |
| `frontend/src/components/param/VehicleParams.tsx` | Live/Mock 提示 |
| `frontend/src/hooks/useParamSubmit.ts` | **删除**（重复） |
| `frontend/src/utils/apiAdapter.test.ts` | 扩展测试 |

---

### Task 1: 拆分 chart 与 stats 清除

**Files:**
- Modify: `frontend/src/context/SimulationContext.tsx`
- Create: `frontend/src/context/SimulationContext.test.ts`

**Interfaces:**
- Produces: action `{ type: 'RESET_RUN_DATA' }` — 清 chartHistory + stats
- Changes: `CLEAR_CHART_HISTORY` 仅清 chartHistory，**不**重置 stats

- [ ] **Step 1: 写失败测试**

`frontend/src/context/SimulationContext.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { simulationReducer, initialState } from './SimulationContext';

describe('simulationReducer lifecycle', () => {
  it('CLEAR_CHART_HISTORY does not reset stats', () => {
    const withStats = {
      ...initialState,
      stats: { trip_time: 120, avg_speed: 45, max_speed: 64, energy: 0, stop_count: 2 },
      chartHistory: {
        speedTime: [[1, 50], [2, 60]],
        accelTime: [[1, 0.5]],
        speedPosition: [[100, 50]],
      },
    };
    const next = simulationReducer(withStats, { type: 'CLEAR_CHART_HISTORY' });
    expect(next.stats.trip_time).toBe(120);
    expect(next.chartHistory.speedTime).toEqual([]);
  });

  it('RESET_RUN_DATA clears both chart and stats', () => {
    const withData = {
      ...initialState,
      stats: { trip_time: 120, avg_speed: 45, max_speed: 64, energy: 0, stop_count: 2 },
      chartHistory: {
        speedTime: [[1, 50]],
        accelTime: [[1, 0.5]],
        speedPosition: [[100, 50]],
      },
    };
    const next = simulationReducer(withData, { type: 'RESET_RUN_DATA' });
    expect(next.stats.trip_time).toBe(0);
    expect(next.chartHistory.speedTime).toEqual([]);
  });
});
```

> 注：需 export `simulationReducer` 与 `initialState`（若尚未 export，在 `SimulationContext.tsx` 追加 `export`）。

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd frontend && npx vitest run src/context/SimulationContext.test.ts`  
Expected: FAIL — `RESET_RUN_DATA` unknown / stats 被 CLEAR_CHART 清掉

- [ ] **Step 3: 修改 reducer**

`SimulationContext.tsx` Action 类型追加：

```typescript
| { type: 'RESET_RUN_DATA' }
```

修改 `CLEAR_CHART_HISTORY` case：

```typescript
case 'CLEAR_CHART_HISTORY':
  return {
    ...state,
    chartHistory: clearChartHistory(),
  };
```

新增 case：

```typescript
case 'RESET_RUN_DATA':
  return {
    ...state,
    chartHistory: clearChartHistory(),
    stats: { ...initialState.stats },
  };
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd frontend && npx vitest run src/context/SimulationContext.test.ts`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/context/SimulationContext.tsx frontend/src/context/SimulationContext.test.ts
git commit -m "fix(frontend): 拆分图表与统计清除逻辑"
```

---

### Task 2: 修复 start/stop 生命周期

**Files:**
- Modify: `frontend/src/hooks/useSimulation.ts`
- Modify: `frontend/src/hooks/useMockReplay.ts`

**Interfaces:**
- Consumes: `RESET_RUN_DATA`, `SET_STATS`
- Produces: start → `RESET_RUN_DATA`；stop → 不清 chart

- [ ] **Step 1: 修改 useSimulation.ts**

```typescript
const startSimulation = useCallback(() => {
  dispatch({ type: 'RESET_RUN_DATA' });  // 替换 CLEAR_CHART_HISTORY
  send({ type: 'sim_control', action: 'start' });
}, [send, dispatch]);

const stopSimulation = useCallback(() => {
  send({ type: 'sim_control', action: 'stop' });
  // 删除 dispatch({ type: 'CLEAR_CHART_HISTORY' });
}, [send]);
```

- [ ] **Step 2: 修改 useMockReplay.ts stop 分支**

在 `case 'start':` 中将 `CLEAR_CHART_HISTORY` 改为 `RESET_RUN_DATA`。

在 `case 'stop':` 中追加 stats：

```typescript
case 'stop': {
  replayer.stop();
  const s = runStatsRef.current;
  dispatch({
    type: 'SET_STATS',
    payload: {
      trip_time: s.tripTime,
      avg_speed: s.count > 0 ? s.sumSpeed / s.count : 0,
      max_speed: s.maxSpeed,
    },
  });
  dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
  break;
}
```

- [ ] **Step 3: 手动验证 Mock 场景 3**

Run: `cd frontend && npm run dev`（Mock 默认）

1. 点「运行」→ 曲线绘制
2. 点「停止」→ **曲线仍在**，底部/ExportPanel 出现运行摘要
3. 再点「运行」→ 曲线清空重来

- [ ] **Step 4: 全量测试**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useSimulation.ts frontend/src/hooks/useMockReplay.ts
git commit -m "fix(frontend): 停止保留曲线并显示运行摘要"
```

---

### Task 3: VehicleView 布局 + 参数提示 + 清理死代码

**Files:**
- Modify: `frontend/src/pages/VehicleView.tsx`
- Modify: `frontend/src/components/param/VehicleParams.tsx`
- Delete: `frontend/src/hooks/useParamSubmit.ts`

- [ ] **Step 1: 隐藏 iter3 占位图表**

`VehicleView.tsx` — 移除或条件隐藏 ResistanceChart/EnergyChart 行，chartRow flex 给 VHC-01/02：

```tsx
export default function VehicleView() {
  return (
    <div style={styles.container}>
      <div style={styles.indicatorRow}>
        <ModeIndicator />
      </div>
      <div style={{ ...styles.chartRow, flex: 1 }}>
        <div style={styles.chartHalf}><SpeedTimeCurve /></div>
        <div style={styles.chartHalf}><AccelTimeCurve /></div>
      </div>
      {/* UI-VHC-04/05: 迭代三实现，迭代一隐藏 */}
    </div>
  );
}
```

- [ ] **Step 2: VehicleParams 分模式提示**

```typescript
import { USE_MOCK } from '../../utils/constants';

// hint 文案
{USE_MOCK
  ? '参数在下次点击「运行」时生效'
  : '参数已提交后端（运行中修改下一步生效）'}
```

牵引曲线表标题追加：`{!USE_MOCK && ' (迭代一后端暂不支持同步)'}`

- [ ] **Step 3: 删除 useParamSubmit.ts**

确认无 import 引用后删除文件。

- [ ] **Step 4: 构建验证**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/VehicleView.tsx frontend/src/components/param/VehicleParams.tsx
git rm frontend/src/hooks/useParamSubmit.ts
git commit -m "refactor(frontend): 车辆视图布局与参数提示优化"
```

---

### Task 4: ModeIndicator 站停语义

**Files:**
- Modify: `frontend/src/utils/format.ts`
- Modify: `frontend/src/components/views/vehicle/ModeIndicator.tsx`
- Create: `frontend/src/components/views/vehicle/ModeIndicator.test.tsx`

**Interfaces:**
- Produces: `getDisplayMode(mode, speed, runningPhase?) => TrainMode`

- [ ] **Step 1: 写失败测试**

`ModeIndicator.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SimulationProvider } from '../../../context/SimulationContext';
import ModeIndicator from './ModeIndicator';

describe('ModeIndicator', () => {
  it('highlights stopped when mode is stopped', () => {
    // 用 provider 注入 trains: [{ mode: 'stopped', speed: 0, ... }]
    // 断言「停稳」按钮 opacity 为 1
  });
});
```

- [ ] **Step 2: 实现 getDisplayMode**

`format.ts`:

```typescript
export function getDisplayMode(
  mode: TrainMode | undefined,
  speed: number,
  runningPhase?: string,
): TrainMode {
  if (runningPhase === 'dwell') return 'stopped';
  if (mode === 'stopped') return 'stopped';
  if (mode === 'coasting' && speed < 0.5) return 'stopped';
  return mode ?? 'coasting';
}
```

`ModeIndicator.tsx` 使用 `getDisplayMode(train?.mode, train?.speed ?? 0)`。

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npx vitest run src/components/views/vehicle/ModeIndicator.test.tsx`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/format.ts frontend/src/components/views/vehicle/ModeIndicator.tsx frontend/src/components/views/vehicle/ModeIndicator.test.tsx
git commit -m "feat(frontend): 工况指示器支持站停态"
```

---

### Task 5: apiAdapter 预留 runningPhase + Live 联调验收

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts`
- Modify: `frontend/src/utils/apiAdapter.test.ts`
- Modify: `frontend/src/hooks/useWebSocket.ts`（可选：init_state 同步 clock）

**Interfaces:**
- Produces: `parseServerSnapshot` 映射 `signaling.controlCommands[0].runningPhase` → `commands[0].running_phase`

- [ ] **Step 1: 扩展 apiAdapter 测试**

```typescript
it('maps runningPhase from controlCommands', () => {
  const raw = {
    clock: { elapsed: 30, speedMultiplier: 1 as const },
    trains: [{ id: 'T1', position: 1500, speed: 0, acceleration: 0, mode: 'stopped' as const,
      mass: 200000, passengerCount: 900, pantographVoltage: 1500, powerDemand: 0,
      doorStatus: 'closed' as const, faultAlarm: null }],
    power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
    signaling: {
      controlCommands: [{ trainId: 'T1', tractionLevel: 0, brakeLevel: 0, emergencyBrake: false, runningPhase: 'dwell' }],
      emergencyBrakes: [],
    },
    track: { occupancy: [], switchStates: [] },
    events: [],
  };
  const snap = parseServerSnapshot(raw);
  expect(snap.signaling.commands[0]?.running_phase).toBe('dwell');
});
```

- [ ] **Step 2: 实现映射**

`parseServerSnapshot` 中：

```typescript
signaling: {
  commands: (raw.signaling?.controlCommands ?? []).map((c) => ({
    train_id: c.trainId,
    traction_level: c.tractionLevel,
    brake_level: c.brakeLevel,
    emergency_brake: c.emergencyBrake,
    running_phase: (c as { runningPhase?: string }).runningPhase,
  })),
  emergency_brake: [],
  train_intervals: [],
},
```

同步更新 `ApiSimulationSnapshot` / `ControlCommand` 类型（`types/simulation.ts`）。

- [ ] **Step 3: ModeIndicator 读取 running_phase**

```typescript
const { trains, signaling } = useSimulationState();
const runningPhase = signaling.commands[0]?.running_phase;
const displayMode = getDisplayMode(train?.mode, train?.speed ?? 0, runningPhase);
```

- [ ] **Step 4: Live 联调验收（手工）**

环境：`VITE_USE_MOCK=false`，后端 `:8000`

| # | 步骤 | 预期 |
|---|------|------|
| 1 | 车辆视图 → 运行 | 速度/加速度曲线实时更新 |
| 2 | 观察工况指示器 | 牵引→惰行→制动→停稳 交替 |
| 3 | 暂停 | 曲线冻结 |
| 4 | 继续 | 曲线恢复 |
| 5 | 停止 | 曲线保留，摘要显示 |
| 6 | 质量改 220t → 重新运行 | 加速度曲线整体降低 |
| 7 | 10× 倍率运行 | 仿真明显加速 |
| 8 | 导出 CSV | 非空 |

- [ ] **Step 5: 更新 frontend/CLAUDE.md 迭代一状态表**

将 UI-VHC-01~03、UI-PARAM-01、UI-CTRL 标为「已实现」。

- [ ] **Step 6: 全量测试 + Commit**

Run: `cd frontend && npm test && npm run build`

```bash
git add frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts frontend/src/types/simulation.ts frontend/src/components/views/vehicle/ModeIndicator.tsx frontend/CLAUDE.md
git commit -m "feat(frontend): 车辆视图 Live 联调与验收完成"
```

---

## Self-Review

| 规格要求 | Task |
|---------|------|
| B1 stop 不清曲线 | Task 2 |
| B2 Mock stop 摘要 | Task 2 |
| B3 stats/chart 解耦 | Task 1 |
| UI-VHC-01~03 布局 | Task 3, 4 |
| UI-PARAM-01 提示 | Task 3 |
| 场景 3 验收 | Task 2, 5 |
| 场景 4 emptyMass | Task 5 步骤 6 |
| runningPhase 预留 | Task 4, 5 |

无 TBD。后端 `runningPhase` 未就绪时 Task 4 fallback 仍可用。

## Execution Handoff

**Plan saved to `docs/superpowers/plans/2026-07-09-vehicle-frontend-closure.md`.**

**1. Subagent-Driven (recommended)** — 每 Task 独立 subagent  
**2. Inline Execution** — 本会话批量执行

**Which approach?**

## 你的开发顺序速查

```
Task 1 → Task 2（P0，先修 Bug）
    ↓
Task 3（UX 打磨，可并行）
    ↓
Task 4 → Task 5（联调 + 签字）
```

**预计工作量：** 5 个 Task，约 1~2 天（不含等待后端 runningPhase）。
