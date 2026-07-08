# 车辆系统前后端联调 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `VITE_USE_MOCK=false` 时，车辆视图通过 WebSocket/REST 驱动后端真实仿真，完成迭代一 UI-VHC-01~03 联调验收。

**Architecture:** 在前端新增 `apiAdapter` 层将 API 文档 camelCase 消息转换为现有 `SimulationSnapshot` snake_case 状态；扩展 `useWebSocket` 处理完整消息生命周期；启动时 REST 引导参数；倍率走 REST `/simulation/speed`。Mock 路径不变。

**Tech Stack:** React 19, TypeScript, Vite, Vitest, FastAPI WebSocket (已有), fetch REST

## Global Constraints

- API 消息格式以 `docs/API接口文档.md` 8.4 节 camelCase 为准，前端内部保持 snake_case
- 不修改 `frontend/src/mock/*` 与 `useMockReplay.ts` 行为
- `TrainMode` 扩展 `stopped` 时 Mock 帧仍用 traction/coasting/braking
- 联调默认步长 0.1s，倍率选项 1 | 5 | 10
- 所有新增逻辑需有 Vitest 单测；`npm test` 与 `npm run build` 必须通过

---

## File Map

| 文件 | 职责 |
|------|------|
| `frontend/src/utils/apiAdapter.ts` | camelCase ↔ SimulationSnapshot/Params 转换 |
| `frontend/src/utils/apiAdapter.test.ts` | 适配器单测 |
| `frontend/src/hooks/useBootstrap.ts` | 启动时 REST 拉取 params |
| `frontend/src/hooks/useWebSocket.ts` | 扩展 WS 消息分发 |
| `frontend/src/hooks/useSimulation.ts` | 出站 param 适配 |
| `frontend/src/services/api.ts` | 新增 setSimulationSpeed |
| `frontend/src/components/control/SpeedSelector.tsx` | REST 倍率 |
| `frontend/src/components/views/vehicle/ModeIndicator.tsx` | stopped 态 |
| `frontend/src/types/simulation.ts` | TrainMode + ServerMessage 扩展 |
| `frontend/src/App.tsx` | 挂载 bootstrap |

---

### Task 1: API 入站适配器

**Files:**
- Create: `frontend/src/utils/apiAdapter.ts`
- Create: `frontend/src/utils/apiAdapter.test.ts`
- Modify: `frontend/src/types/simulation.ts`

**Interfaces:**
- Produces: `parseServerSnapshot(raw: ApiSimulationSnapshot): SimulationSnapshot`
- Produces: `parseInitState(raw: ApiInitState): { params: Partial<SimulationParams>; config?: Partial<SimulationConfig> }`

- [ ] **Step 1: 扩展 TrainMode 与 API 原始类型**

在 `frontend/src/types/simulation.ts` 中：

```typescript
export type TrainMode = 'traction' | 'coasting' | 'braking' | 'stopped';

/** 后端 WS 推送的 camelCase 列车状态（适配前） */
export interface ApiTrainState {
  id: string;
  position: number;
  speed: number;
  acceleration: number;
  mode: TrainMode;
  mass: number;
  passengerCount: number;
  pantographVoltage: number;
  powerDemand: number;
  doorStatus: DoorStatus;
  faultAlarm: FaultAlarm | null;
}

export interface ApiSimulationSnapshot {
  clock: { elapsed: number; speedMultiplier: SpeedMultiplier };
  trains: ApiTrainState[];
  power: {
    substations: unknown[];
    voltageProfile: unknown[];
    totalConsumption: number;
    totalRegeneration: number;
  };
  signaling: { commands: unknown[]; emergencyBrakes: unknown[] };
  track: { occupancy: unknown[]; switchStates: unknown[] };
  events: SimulationEvent[];
}
```

- [ ] **Step 2: 写失败测试**

`frontend/src/utils/apiAdapter.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseServerSnapshot } from './apiAdapter';

describe('parseServerSnapshot', () => {
  it('converts camelCase train fields to snake_case', () => {
    const raw = {
      clock: { elapsed: 12.3, speedMultiplier: 5 as const },
      trains: [{
        id: 'TRAIN_01',
        position: 500,
        speed: 64,
        acceleration: 0,
        mode: 'coasting' as const,
        mass: 254000,
        passengerCount: 900,
        pantographVoltage: 1500,
        powerDemand: 0,
        doorStatus: 'closed' as const,
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: { commands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const snap = parseServerSnapshot(raw);
    expect(snap.clock.speed_multiplier).toBe(5);
    expect(snap.trains[0].passenger_count).toBe(900);
    expect(snap.trains[0].pantograph_voltage).toBe(1500);
  });

  it('preserves stopped mode from backend', () => {
    const raw = {
      clock: { elapsed: 0, speedMultiplier: 1 as const },
      trains: [{
        id: 'T1', position: 1500, speed: 0, acceleration: 0,
        mode: 'stopped' as const, mass: 200000, passengerCount: 0,
        pantographVoltage: 1500, powerDemand: 0, doorStatus: 'closed' as const,
        faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
      signaling: { commands: [], emergencyBrakes: [] },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    expect(parseServerSnapshot(raw).trains[0].mode).toBe('stopped');
  });
});
```

- [ ] **Step 3: 运行测试确认失败**

Run: `cd frontend && npm test -- src/utils/apiAdapter.test.ts`  
Expected: FAIL — module not found

- [ ] **Step 4: 实现 parseServerSnapshot**

`frontend/src/utils/apiAdapter.ts`:

```typescript
import type { ApiSimulationSnapshot, SimulationSnapshot, TrainState } from '../types/simulation';

function mapTrain(t: ApiSimulationSnapshot['trains'][0]): TrainState {
  return {
    id: t.id,
    position: t.position,
    speed: t.speed,
    acceleration: t.acceleration,
    mode: t.mode,
    mass: t.mass,
    passenger_count: t.passengerCount,
    door_status: t.doorStatus,
    pantograph_voltage: t.pantographVoltage,
    power_demand: t.powerDemand,
    fault_alarm: t.faultAlarm,
  };
}

export function parseServerSnapshot(raw: ApiSimulationSnapshot): SimulationSnapshot {
  return {
    clock: {
      elapsed: raw.clock.elapsed,
      speed_multiplier: raw.clock.speedMultiplier,
    },
    trains: raw.trains.map(mapTrain),
    power: {
      substations: [],
      voltage_profile: [],
      total_consumption: raw.power.totalConsumption,
      total_regeneration: raw.power.totalRegeneration,
      regeneration_rate: 0,
    },
    signaling: { commands: [], emergency_brake: [], train_intervals: [] },
    track: { occupancy: [], switch_states: [] },
    events: raw.events ?? [],
  };
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd frontend && npm test -- src/utils/apiAdapter.test.ts`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts
git commit -m "feat(frontend): 新增 WS 快照 camelCase 适配器"
```

---

### Task 2: 出站参数适配 + REST 倍率

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts`
- Modify: `frontend/src/utils/apiAdapter.test.ts`
- Modify: `frontend/src/services/api.ts`

**Interfaces:**
- Produces: `toApiParamUpdate(params: Partial<SimulationParams>): object`

- [ ] **Step 1: 写失败测试 toApiParamUpdate**

```typescript
import { toApiParamUpdate } from './apiAdapter';

it('converts vehicle snake_case to camelCase for WS', () => {
  const out = toApiParamUpdate({
    vehicle: { empty_mass: 220000, max_traction_force: 400000 },
    signal: { dwell_time: 35, target_speed_ratio: 0.8 },
  });
  expect(out).toEqual({
    vehicle: { emptyMass: 220000, maxTractionForce: 400000 },
    signal: { dwellTime: 35, targetSpeedRatio: 0.8 },
  });
});
```

- [ ] **Step 2: 运行确认失败**

Run: `cd frontend && npm test -- src/utils/apiAdapter.test.ts -t "converts vehicle"`

- [ ] **Step 3: 实现 toApiParamUpdate**

在 `apiAdapter.ts` 添加字段映射（MVP 范围）：

```typescript
const VEHICLE_KEY_MAP: Record<string, string> = {
  empty_mass: 'emptyMass',
  passenger_capacity: 'passengerCapacity',
  max_speed: 'maxSpeed',
  max_traction_force: 'maxTractionForce',
  max_brake_force: 'maxBrakeForce',
  davis_A: 'davisA',
  davis_B: 'davisB',
  davis_C_front_area: 'davisCFrontArea',
  davis_C_drag_coeff: 'davisCDragCoeff',
  curve_resist_coeff: 'curveResistCoeff',
  tunnel_resist_factor: 'tunnelResistFactor',
  regeneration_efficiency: 'regenerationEfficiency',
};

export function toApiParamUpdate(params: Partial<SimulationParams>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  if (params.vehicle) {
    const v: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(params.vehicle)) {
      if (val === undefined) continue;
      const apiKey = VEHICLE_KEY_MAP[k] ?? k;
      v[apiKey] = val;
    }
    result.vehicle = v;
  }
  if (params.signal) {
    result.signal = {
      ...(params.signal.dwell_time !== undefined && { dwellTime: params.signal.dwell_time }),
      ...(params.signal.target_speed_ratio !== undefined && { targetSpeedRatio: params.signal.target_speed_ratio }),
      ...(params.signal.departure_interval !== undefined && { departureInterval: params.signal.departure_interval }),
    };
  }
  if (params.track) {
    result.track = {
      ...(params.track.gradient !== undefined && { gradient: params.track.gradient }),
      ...(params.track.curvature !== undefined && { curvature: params.track.curvature }),
      ...(params.track.speed_limit !== undefined && { speedLimit: params.track.speed_limit }),
    };
  }
  return result;
}
```

- [ ] **Step 4: 新增 setSimulationSpeed REST**

`frontend/src/services/api.ts`:

```typescript
export async function setSimulationSpeed(multiplier: SpeedMultiplier): Promise<void> {
  await request('/simulation/speed', {
    method: 'PUT',
    body: JSON.stringify({ speedMultiplier: multiplier }),
  });
}
```

需 import `SpeedMultiplier` 类型。

- [ ] **Step 5: 测试通过 + build**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts frontend/src/services/api.ts
git commit -m "feat(frontend): 出站参数 camelCase 与倍率 REST"
```

---

### Task 3: 扩展 useWebSocket 消息处理

**Files:**
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/types/simulation.ts`（ServerMessage 联合类型）

**Interfaces:**
- Consumes: `parseServerSnapshot` from Task 1

- [ ] **Step 1: 扩展 ServerMessage 类型**

```typescript
export type ServerMessage =
  | { type: 'simulation_snapshot'; timestamp: number; data: ApiSimulationSnapshot }
  | { type: 'init_state'; config: Record<string, unknown>; params?: Record<string, unknown> }
  | { type: 'simulation_status'; status: RunState }
  | { type: 'simulation_complete' }
  | { type: 'heartbeat' };
```

- [ ] **Step 2: 修改 useWebSocket onmessage**

```typescript
import { parseServerSnapshot } from '../utils/apiAdapter';

// inside onmessage:
switch (message.type) {
  case 'simulation_snapshot':
    dispatch({
      type: 'RUNTIME_UPDATE',
      payload: parseServerSnapshot(message.data),
    });
    break;
  case 'simulation_status':
    dispatch({ type: 'SET_RUN_STATE', payload: message.status });
    break;
  case 'simulation_complete':
    dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
    break;
  case 'init_state':
    // Task 4 补充 parseInitState；此处先 dispatch INIT_DEFAULT_PARAMS 或占位
    break;
  default:
    break;
}
```

- [ ] **Step 3: start 时清空 chartHistory**

在 `useSimulation.ts` 的 `start()` 中已有 `CLEAR_CHART_HISTORY`（若无则添加），确保与 mock 行为一致。

- [ ] **Step 4: 手动验证**

Run 后端 + 前端 `VITE_USE_MOCK=false`，打开车辆视图，Start 后 Network WS 帧应被解析无 console error。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useWebSocket.ts frontend/src/types/simulation.ts frontend/src/hooks/useSimulation.ts
git commit -m "feat(frontend): WebSocket 快照适配与状态消息处理"
```

---

### Task 4: 启动引导 useBootstrap

**Files:**
- Create: `frontend/src/hooks/useBootstrap.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/context/SimulationContext.tsx`（若无 INIT_PARAMS action 则添加）

- [ ] **Step 1: 添加 INIT_PARAMS reducer**

```typescript
case 'INIT_PARAMS':
  return {
    ...state,
    params: {
      vehicle: { ...DEFAULT_VEHICLE_PARAMS, ...action.payload.vehicle },
      track: { ...state.params.track, ...action.payload.track },
      power: { ...state.params.power, ...action.payload.power },
      signal: { ...state.params.signal, ...action.payload.signal },
    },
  };
```

- [ ] **Step 2: 实现 useBootstrap**

```typescript
import { useEffect } from 'react';
import { getParams } from '../services/api';
import { useSimulationDispatch } from '../context/SimulationContext';
import { USE_MOCK } from '../utils/constants';

export function useBootstrap() {
  const dispatch = useSimulationDispatch();
  useEffect(() => {
    if (USE_MOCK) return;
    getParams()
      .then((params) => dispatch({ type: 'INIT_PARAMS', payload: params }))
      .catch((err) => console.warn('[Bootstrap] 无法加载后端参数，使用默认值', err));
  }, [dispatch]);
}
```

- [ ] **Step 3: App.tsx 调用**

```typescript
import { useBootstrap } from './hooks/useBootstrap';

function App() {
  useBootstrap();
  // ...existing
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useBootstrap.ts frontend/src/App.tsx frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): 启动时 REST 引导仿真参数"
```

---

### Task 5: 倍率选择与参数发送

**Files:**
- Modify: `frontend/src/components/control/SpeedSelector.tsx`
- Modify: `frontend/src/hooks/useSimulation.ts`

- [ ] **Step 1: SpeedSelector 双路径**

```typescript
import { USE_MOCK } from '../../utils/constants';
import { setSimulationSpeed } from '../../services/api';

const handleChange = async (multiplier: SpeedMultiplier) => {
  dispatch({ type: 'SET_SPEED_MULTIPLIER', payload: multiplier });
  if (USE_MOCK) {
    send({ type: 'speed_multiplier', value: multiplier });
  } else {
    try {
      await setSimulationSpeed(multiplier);
    } catch (e) {
      console.error('[SpeedSelector] REST 倍率设置失败', e);
    }
  }
};
```

- [ ] **Step 2: useSimulation updateParams 走适配器**

```typescript
import { toApiParamUpdate } from '../utils/apiAdapter';
import { USE_MOCK } from '../utils/constants';

const updateParams = (params: Partial<SimulationParams>) => {
  dispatch({ type: 'UPDATE_PARAMS', payload: params });
  if (USE_MOCK) {
    send({ type: 'param_update', params });
  } else {
    send({ type: 'param_update', params: toApiParamUpdate(params) });
  }
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/control/SpeedSelector.tsx frontend/src/hooks/useSimulation.ts
git commit -m "feat(frontend): 倍率 REST 与 param_update camelCase"
```

---

### Task 6: ModeIndicator stopped 态

**Files:**
- Modify: `frontend/src/components/views/vehicle/ModeIndicator.tsx`

- [ ] **Step 1: 添加 stopped 样式**

在 MODE_CONFIG 中增加：

```typescript
stopped: { label: '停稳', color: '#8c8c8c', icon: '⏹' },
```

零速且 mode 非 braking 时也可 fallback 显示 stopped。

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/views/vehicle/ModeIndicator.tsx
git commit -m "feat(frontend): 工况指示器支持 stopped 态"
```

---

### Task 7: 联调验收与文档

**Files:**
- Modify: `frontend/.env.example`
- Modify: `frontend/README.md`（若存在联调说明段落）

- [ ] **Step 1: 更新 .env.example 注释**

```bash
# false = 连接后端 WebSocket；true = 本地 Mock 回放
VITE_USE_MOCK=true
```

- [ ] **Step 2: 全量测试**

Run: `cd frontend && npm test && npm run build`  
Expected: 全部 PASS

- [ ] **Step 3: E2E 手动清单**

1. 终端 1：`cd backend && uv run uvicorn sim_engine.app:app --reload`
2. 终端 2：`cd frontend && set VITE_USE_MOCK=false && npm run dev`
3. 车辆视图 → Start → 速度/加速度曲线更新
4. 切换 5×/10× → 状态栏倍率变化
5. 停止 → 导出 CSV → 文件含数据行
6. 改 `VITE_USE_MOCK=true` → Mock 回归正常

- [ ] **Step 4: Commit**

```bash
git add frontend/.env.example
git commit -m "docs(frontend): 补充 Mock/联调环境变量说明"
```

---

## Spec Coverage Checklist

| 规格要求 | Task |
|----------|------|
| parseServerSnapshot camelCase→snake_case | Task 1 |
| toApiParamUpdate 出站 | Task 2 |
| init_state / simulation_status / complete | Task 3 |
| REST 引导 params | Task 4 |
| 倍率 REST | Task 5 |
| stopped 工况 | Task 6 |
| E2E 验收 | Task 7 |
| Mock 不回归 | Task 5 双路径 + Task 7 Step 3.6 |

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-08-vehicle-backend-integration.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — 每 Task 派生子 agent，Task 间审查
2. **Inline Execution** — 本会话用 executing-plans 批量执行，检查点暂停

Which approach?
