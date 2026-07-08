# 车辆系统前端 Mock 回放实现规划（方案 B）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用预录 JSON 时序数据驱动车辆视图（速度-时间、加速度-时间、工况指示器）和车辆参数面板，在后端 API 未就绪时完成 MVP 验收场景的可视化闭环。

**Architecture:** 将预录的 `MockReplayScenario` JSON 通过 `mockReplayer` 按固定步长逐帧 dispatch `RUNTIME_UPDATE`，与 WebSocket 推送走同一条 reducer 路径。`SimulationContext` 新增 `chartHistory` 缓冲区累积曲线历史。`VITE_USE_MOCK=true` 时启用回放器并跳过 WebSocket；`false` 时保持现有 WS 逻辑。后期接 API 时只切换数据源，UI 组件不改。

**Tech Stack:** React 19, TypeScript 6, Vite 8, ECharts 6, Vitest（仅纯函数测试）

## Global Constraints

- 所有新增/修改文件放在 `frontend/src/` 下，遵循现有目录结构
- 组件使用 inline `styles` 对象（与现有组件风格一致，不引入 CSS 模块或 UI 框架）
- 类型定义追加到 `types/simulation.ts`，不创建新类型文件
- Mock 数据放在 `frontend/src/data/` 目录
- 颜色使用 CSS 变量（`var(--xxx)`）或 `utils/format.ts` 工具函数
- MVP P0 范围：UI-VHC-01、UI-VHC-02、UI-VHC-03、UI-PARAM-01、UI-PARAM-05；UI-VHC-04/05 保持占位
- 迭代一验收场景：3 站 2 区间（A→B→C），空车 200t，AW2 载客 60%，限速 80km/h，三段式牵引→惰行→制动
- 仿真步长默认 0.1s（与后端 `timeStep` 一致）
- 字段命名前端内部统一 snake_case（与现有 `simulation.ts` 一致）

## File Structure

| 文件 | 职责 | 操作 |
|---|---|---|
| `src/types/simulation.ts` | 新增 `ChartHistory`、`MockReplayFrame`、`MockReplayScenario`；`AppState` 新增 `chartHistory` | 修改 |
| `src/data/mockVehicleParams.ts` | 默认车辆参数常量（对齐 MVP + API 文档） | 新增 |
| `src/data/mockReplay/scenario-default.json` | 预录 A→B→C 运行时序（~180s，1s 间隔） | 新增 |
| `src/utils/chartHistory.ts` | 纯函数：追加/清空曲线历史 | 新增 |
| `src/utils/frameToSnapshot.ts` | 纯函数：MockReplayFrame → SimulationSnapshot | 新增 |
| `src/services/mockReplayer.ts` | 回放控制器：start/pause/resume/stop/step | 新增 |
| `src/hooks/useMockReplay.ts` | React Hook：绑定回放器与 dispatch | 新增 |
| `src/context/SimulationContext.tsx` | chartHistory 初始值、RUNTIME_UPDATE 追加、CLEAR_CHART_HISTORY、INIT_VEHICLE_PARAMS | 修改 |
| `src/hooks/useSimulation.ts` | Mock 模式下 stop/reset 时清空 chartHistory | 修改 |
| `src/App.tsx` | `VITE_USE_MOCK` 分支：Mock 回放 vs WebSocket | 修改 |
| `src/utils/constants.ts` | 新增 `USE_MOCK`、`MOCK_REPLAY_INTERVAL_MS` | 修改 |
| `src/components/views/vehicle/SpeedTimeCurve.tsx` | 读 `chartHistory.speedTime` | 修改 |
| `src/components/views/vehicle/AccelTimeCurve.tsx` | 读 `chartHistory.accelTime` | 修改 |
| `src/components/views/overview/SpeedPositionCurve.tsx` | 读 `chartHistory.speedPosition` | 修改 |
| `src/components/param/VehicleParams.tsx` | 补全参数字段 + 牵引曲线表格 | 修改 |
| `src/components/param/ParamPanel.tsx` | 车辆参数重置按钮 | 修改 |
| `scripts/generate-mock-replay.mjs` | 一次性生成 `scenario-default.json` | 新增 |
| `.env.example` | 新增 `VITE_USE_MOCK=true` | 修改 |
| `vitest.config.ts` + `package.json` | 纯函数单元测试基础设施 | 修改 |

---

### Task 1: 类型定义与默认车辆参数

**Files:**
- Modify: `frontend/src/types/simulation.ts`
- Create: `frontend/src/data/mockVehicleParams.ts`

**Interfaces:**
- Consumes: 无
- Produces: `ChartHistory` 接口；`MockReplayFrame` 接口；`MockReplayScenario` 接口；`DEFAULT_VEHICLE_PARAMS` 常量

- [ ] **Step 1: 在 simulation.ts 追加 ChartHistory 和 Mock 回放类型**

在 `AppState` 接口之前追加：

```typescript
// ==================== 图表历史缓冲 ====================

/** 实时曲线历史数据（前端累积，供 ECharts 绘制） */
export interface ChartHistory {
  speedTime: [number, number][];       // [时间s, 速度km/h]
  accelTime: [number, number][];       // [时间s, 加速度m/s²]
  speedPosition: [number, number][];   // [位置m, 速度km/h]
}

// ==================== Mock 回放数据 ====================

/** 预录回放单帧（紧凑格式，比完整 SimulationSnapshot 小） */
export interface MockReplayFrame {
  t: number;                // 仿真时间 (s)
  position: number;         // 公里标 (m)
  speed: number;            // 速度 (km/h)
  acceleration: number;     // 加速度 (m/s²)
  mode: TrainMode;
  mass: number;
  passenger_count: number;
  pantograph_voltage: number;
  power_demand: number;
}

/** 预录回放场景 */
export interface MockReplayScenario {
  meta: {
    name: string;
    description: string;
    timeStep: number;       // 帧间隔 (s)，默认 1.0
    totalDuration: number;  // 总时长 (s)
  };
  vehicleParams: VehicleParams;
  frames: MockReplayFrame[];
}
```

在 `AppState` 接口中 `lineLayout` 字段之前追加：

```typescript
  /** 曲线历史缓冲 */
  chartHistory: ChartHistory;
```

- [ ] **Step 2: 创建 mockVehicleParams.ts**

```typescript
import type { VehicleParams } from '../types/simulation';

/** 默认车辆参数 — 对齐迭代一 MVP 验收场景 1 + API 文档 3.1 */
export const DEFAULT_VEHICLE_PARAMS: VehicleParams = {
  id: 'TYPE_A',
  name: 'A型车',
  empty_mass: 200_000,
  passenger_capacity: 1500,
  max_speed: 80,
  max_traction_force: 400_000,
  max_brake_force: 350_000,
  davis_A: 0.01,
  davis_B: 0.0001,
  davis_C_front_area: 10,
  davis_C_drag_coeff: 0.5,
  curve_resist_coeff: 600,
  tunnel_resist_factor: 1.2,
  regeneration_efficiency: 0.3,
  traction_curve: [
    { speed: 0, force_percent: 1.0, sort_order: 0 },
    { speed: 40, force_percent: 1.0, sort_order: 1 },
    { speed: 80, force_percent: 0.5, sort_order: 2 },
  ],
};
```

- [ ] **Step 3: 验证 TypeScript 编译**

Run: `cd frontend && npm run build`
Expected: 报错 `chartHistory` 缺失（Task 2 会修复），但新类型文件本身无语法错误

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/data/mockVehicleParams.ts
git commit -m "feat(frontend): add chart history and mock replay types"
```

---

### Task 2: 纯函数工具层（chartHistory + frameToSnapshot）

**Files:**
- Create: `frontend/src/utils/chartHistory.ts`
- Create: `frontend/src/utils/frameToSnapshot.ts`
- Create: `frontend/vitest.config.ts`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: `ChartHistory`, `SimulationSnapshot`, `MockReplayFrame`, `SpeedMultiplier` from `types/simulation.ts`
- Produces: `EMPTY_CHART_HISTORY` 常量；`appendChartHistory(history, snapshot): ChartHistory`；`clearChartHistory(): ChartHistory`；`frameToSnapshot(frame, speedMultiplier): SimulationSnapshot`

- [ ] **Step 1: 安装 Vitest**

```bash
cd frontend && npm install -D vitest
```

在 `package.json` 的 `scripts` 中追加：

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 2: 创建 vitest.config.ts**

```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
```

- [ ] **Step 3: 写失败测试 chartHistory.test.ts**

Create: `frontend/src/utils/chartHistory.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { EMPTY_CHART_HISTORY, appendChartHistory, clearChartHistory } from './chartHistory';
import type { SimulationSnapshot } from '../types/simulation';

const makeSnapshot = (t: number, speed: number, accel: number, pos: number): SimulationSnapshot => ({
  clock: { elapsed: t, speed_multiplier: 1 },
  trains: [{
    id: 'TRAIN_01', position: pos, speed, acceleration: accel,
    mode: 'traction', mass: 200000, passenger_count: 900,
    door_status: 'closed', pantograph_voltage: 1500, power_demand: 100,
    fault_alarm: null,
  }],
  power: { substations: [], voltage_profile: [], total_consumption: 0, total_regeneration: 0, regeneration_rate: 0 },
  signaling: { commands: [], emergency_brake: [], train_intervals: [] },
  track: { occupancy: [], switch_states: [] },
  events: [],
});

describe('appendChartHistory', () => {
  it('appends one point per snapshot', () => {
    const result = appendChartHistory(EMPTY_CHART_HISTORY, makeSnapshot(1.0, 50, 0.8, 100));
    expect(result.speedTime).toEqual([[1.0, 50]]);
    expect(result.accelTime).toEqual([[1.0, 0.8]]);
    expect(result.speedPosition).toEqual([[100, 50]]);
  });

  it('accumulates multiple snapshots', () => {
    let h = EMPTY_CHART_HISTORY;
    h = appendChartHistory(h, makeSnapshot(1.0, 50, 0.8, 100));
    h = appendChartHistory(h, makeSnapshot(2.0, 60, 0.5, 200));
    expect(h.speedTime).toHaveLength(2);
    expect(h.speedTime[1]).toEqual([2.0, 60]);
  });
});

describe('clearChartHistory', () => {
  it('returns empty arrays', () => {
    expect(clearChartHistory()).toEqual(EMPTY_CHART_HISTORY);
  });
});
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd frontend && npm test`
Expected: FAIL — `chartHistory` module not found

- [ ] **Step 5: 实现 chartHistory.ts**

```typescript
import type { ChartHistory, SimulationSnapshot } from '../types/simulation';

export const EMPTY_CHART_HISTORY: ChartHistory = {
  speedTime: [],
  accelTime: [],
  speedPosition: [],
};

const MAX_POINTS = 10_000;

export function appendChartHistory(
  history: ChartHistory,
  snapshot: SimulationSnapshot,
): ChartHistory {
  const train = snapshot.trains[0];
  if (!train) return history;

  const t = snapshot.clock.elapsed;
  const next: ChartHistory = {
    speedTime: [...history.speedTime, [t, train.speed]],
    accelTime: [...history.accelTime, [t, train.acceleration]],
    speedPosition: [...history.speedPosition, [train.position, train.speed]],
  };

  if (next.speedTime.length > MAX_POINTS) {
    return {
      speedTime: next.speedTime.slice(-MAX_POINTS),
      accelTime: next.accelTime.slice(-MAX_POINTS),
      speedPosition: next.speedPosition.slice(-MAX_POINTS),
    };
  }
  return next;
}

export function clearChartHistory(): ChartHistory {
  return { ...EMPTY_CHART_HISTORY };
}
```

- [ ] **Step 6: 写失败测试 frameToSnapshot.test.ts**

Create: `frontend/src/utils/frameToSnapshot.test.ts`

```typescript
import { describe, it, expect } from 'vitest';
import { frameToSnapshot } from './frameToSnapshot';
import type { MockReplayFrame } from '../types/simulation';

const frame: MockReplayFrame = {
  t: 10.0, position: 500, speed: 64, acceleration: 0.3,
  mode: 'coasting', mass: 215000, passenger_count: 900,
  pantograph_voltage: 1500, power_demand: 0,
};

describe('frameToSnapshot', () => {
  it('maps frame fields to SimulationSnapshot', () => {
    const snap = frameToSnapshot(frame, 5);
    expect(snap.clock.elapsed).toBe(10.0);
    expect(snap.clock.speed_multiplier).toBe(5);
    expect(snap.trains[0].speed).toBe(64);
    expect(snap.trains[0].mode).toBe('coasting');
    expect(snap.trains[0].position).toBe(500);
  });
});
```

- [ ] **Step 7: 实现 frameToSnapshot.ts**

```typescript
import type { MockReplayFrame, SimulationSnapshot, SpeedMultiplier } from '../types/simulation';
import { DEFAULT_PANTOGRAPH_VOLTAGE } from './constants';

export function frameToSnapshot(
  frame: MockReplayFrame,
  speedMultiplier: SpeedMultiplier = 1,
): SimulationSnapshot {
  return {
    clock: { elapsed: frame.t, speed_multiplier: speedMultiplier },
    trains: [{
      id: 'TRAIN_01',
      position: frame.position,
      speed: frame.speed,
      acceleration: frame.acceleration,
      mode: frame.mode,
      mass: frame.mass,
      passenger_count: frame.passenger_count,
      door_status: 'closed',
      pantograph_voltage: frame.pantograph_voltage,
      power_demand: frame.power_demand,
      fault_alarm: null,
    }],
    power: {
      substations: [],
      voltage_profile: [{ chainage: frame.position, voltage: frame.pantograph_voltage }],
      total_consumption: 0,
      total_regeneration: 0,
      regeneration_rate: 0,
    },
    signaling: { commands: [], emergency_brake: [], train_intervals: [] },
    track: { occupancy: [], switch_states: [] },
    events: [],
  };
}
```

- [ ] **Step 8: 运行测试确认通过**

Run: `cd frontend && npm test`
Expected: PASS (2 test files, 3 tests)

- [ ] **Step 9: Commit**

```bash
git add frontend/src/utils/chartHistory.ts frontend/src/utils/chartHistory.test.ts frontend/src/utils/frameToSnapshot.ts frontend/src/utils/frameToSnapshot.test.ts frontend/vitest.config.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): add chart history and frame conversion utils"
```

---

### Task 3: 生成预录 JSON 时序数据

**Files:**
- Create: `frontend/scripts/generate-mock-replay.mjs`
- Create: `frontend/src/data/mockReplay/scenario-default.json`

**Interfaces:**
- Consumes: 无（独立脚本）
- Produces: `scenario-default.json` 文件，符合 `MockReplayScenario` 结构

- [ ] **Step 1: 创建生成脚本**

`frontend/scripts/generate-mock-replay.mjs`：

```javascript
/**
 * 生成 A→B→C 三站运行的预录时序数据
 * 速度曲线按 MVP 三段式模式手工建模（非物理引擎，但形状正确）
 *
 * Run: node scripts/generate-mock-replay.mjs
 */
import { writeFileSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dirname, '../src/data/mockReplay/scenario-default.json');

// 线路：A(0) → B(1500) → C(3200)
const STATIONS = [0, 1500, 3200];
const DWELL = 30; // 站停 30s
const DT = 1.0;   // 1s 一帧

function segmentProfile(from, to, startT, mode) {
  const frames = [];
  const dist = to - from;
  const duration = dist / 20; // 简化：平均 20 m/s ≈ 72 km/h
  const steps = Math.ceil(duration / DT);
  for (let i = 0; i <= steps; i++) {
    const ratio = i / steps;
    const pos = from + dist * ratio;
    let speed, accel, trainMode;
    if (mode === 'run') {
      if (ratio < 0.3)       { speed = 64 * (ratio / 0.3); accel = 0.8; trainMode = 'traction'; }
      else if (ratio < 0.7)  { speed = 64; accel = 0; trainMode = 'coasting'; }
      else                   { speed = 64 * (1 - (ratio - 0.7) / 0.3); accel = -0.9; trainMode = 'braking'; }
    } else {
      speed = 0; accel = 0; trainMode = 'coasting';
    }
    frames.push({
      t: startT + i * DT,
      position: Math.round(pos * 10) / 10,
      speed: Math.round(speed * 10) / 10,
      acceleration: Math.round(accel * 100) / 100,
      mode: trainMode,
      mass: 215000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: trainMode === 'traction' ? 3200 : 0,
    });
  }
  return frames;
}

let frames = [];
let t = 0;

// A→B
frames.push(...segmentProfile(STATIONS[0], STATIONS[1], t, 'run'));
t = frames[frames.length - 1].t + DWELL;
// 站停 B
for (let i = 0; i < DWELL; i++) {
  frames.push({ t: t + i, position: STATIONS[1], speed: 0, acceleration: 0,
    mode: 'coasting', mass: 215000, passenger_count: 900, pantograph_voltage: 1500, power_demand: 0 });
}
t += DWELL;

// B→C（上坡段，加速度略低）
const bToC = segmentProfile(STATIONS[1], STATIONS[2], t, 'run');
bToC.forEach((f, i) => {
  if (f.mode === 'traction' && i > 0) f.acceleration = 0.5; // 上坡段加速度降低
});
frames.push(...bToC);
t = frames[frames.length - 1].t + DWELL;
// 站停 C
for (let i = 0; i < DWELL; i++) {
  frames.push({ t: t + i, position: STATIONS[2], speed: 0, acceleration: 0,
    mode: 'coasting', mass: 215000, passenger_count: 900, pantograph_voltage: 1500, power_demand: 0 });
}

const scenario = {
  meta: {
    name: 'A站→B站→C站 标准运行',
    description: '迭代一验收场景1：三段式牵引-惰行-制动，B→C含上坡段',
    timeStep: DT,
    totalDuration: frames[frames.length - 1].t,
  },
  vehicleParams: {
    id: 'TYPE_A', name: 'A型车', empty_mass: 200000, passenger_capacity: 1500,
    max_speed: 80, max_traction_force: 400000, max_brake_force: 350000,
    davis_A: 0.01, davis_B: 0.0001, davis_C_front_area: 10, davis_C_drag_coeff: 0.5,
    curve_resist_coeff: 600, tunnel_resist_factor: 1.2, regeneration_efficiency: 0.3,
    traction_curve: [
      { speed: 0, force_percent: 1.0, sort_order: 0 },
      { speed: 40, force_percent: 1.0, sort_order: 1 },
      { speed: 80, force_percent: 0.5, sort_order: 2 },
    ],
  },
  frames,
};

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify(scenario, null, 2));
console.log(`Generated ${frames.length} frames, duration ${scenario.meta.totalDuration}s → ${OUT}`);
```

- [ ] **Step 2: 运行脚本生成 JSON**

Run: `cd frontend && node scripts/generate-mock-replay.mjs`
Expected: 输出 `Generated ~200 frames, duration ~180s → ...scenario-default.json`

- [ ] **Step 3: 验证 JSON 结构**

Run: `cd frontend && node -e "const d=require('./src/data/mockReplay/scenario-default.json'); console.log(d.frames.length, d.meta.totalDuration, d.frames[0].mode)"`
Expected: 打印帧数、总时长、`traction`

- [ ] **Step 4: Commit**

```bash
git add frontend/scripts/generate-mock-replay.mjs frontend/src/data/mockReplay/scenario-default.json
git commit -m "feat(frontend): add pre-recorded mock replay scenario data"
```

---

### Task 4: Mock 回放控制器

**Files:**
- Create: `frontend/src/services/mockReplayer.ts`
- Create: `frontend/src/services/mockReplayer.test.ts`

**Interfaces:**
- Consumes: `MockReplayScenario`, `frameToSnapshot`, `SpeedMultiplier`
- Produces: `createMockReplayer(scenario, callbacks): MockReplayer` 接口：

```typescript
interface MockReplayerCallbacks {
  onTick: (snapshot: SimulationSnapshot) => void;
  onComplete: () => void;
}

interface MockReplayer {
  start: () => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  step: () => void;
  setSpeedMultiplier: (m: SpeedMultiplier) => void;
  getFrameIndex: () => number;
  getTotalFrames: () => number;
}
```

- [ ] **Step 1: 写失败测试**

`frontend/src/services/mockReplayer.test.ts`：

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createMockReplayer } from './mockReplayer';
import type { MockReplayScenario } from '../types/simulation';

const miniScenario: MockReplayScenario = {
  meta: { name: 'test', description: '', timeStep: 1, totalDuration: 2 },
  vehicleParams: {} as MockReplayScenario['vehicleParams'],
  frames: [
    { t: 0, position: 0, speed: 0, acceleration: 0, mode: 'traction', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 0 },
    { t: 1, position: 10, speed: 5, acceleration: 0.5, mode: 'traction', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 100 },
    { t: 2, position: 20, speed: 10, acceleration: 0.5, mode: 'coasting', mass: 200000, passenger_count: 0, pantograph_voltage: 1500, power_demand: 0 },
  ],
};

describe('createMockReplayer', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it('step advances one frame', () => {
    const onTick = vi.fn();
    const replayer = createMockReplayer(miniScenario, { onTick, onComplete: vi.fn() });
    replayer.step();
    expect(onTick).toHaveBeenCalledOnce();
    expect(onTick.mock.calls[0][0].clock.elapsed).toBe(0);
    replayer.step();
    expect(onTick).toHaveBeenCalledTimes(2);
  });

  it('calls onComplete when all frames played', () => {
    const onComplete = vi.fn();
    const replayer = createMockReplayer(miniScenario, { onTick: vi.fn(), onComplete });
    replayer.step(); replayer.step(); replayer.step();
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd frontend && npm test -- src/services/mockReplayer.test.ts`
Expected: FAIL

- [ ] **Step 3: 实现 mockReplayer.ts**

```typescript
import type { MockReplayScenario, SimulationSnapshot, SpeedMultiplier } from '../types/simulation';
import { frameToSnapshot } from '../utils/frameToSnapshot';

export interface MockReplayerCallbacks {
  onTick: (snapshot: SimulationSnapshot) => void;
  onComplete: () => void;
}

export interface MockReplayer {
  start: () => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  step: () => void;
  setSpeedMultiplier: (m: SpeedMultiplier) => void;
  getFrameIndex: () => number;
  getTotalFrames: () => number;
}

export function createMockReplayer(
  scenario: MockReplayScenario,
  callbacks: MockReplayerCallbacks,
): MockReplayer {
  let frameIndex = 0;
  let speedMultiplier: SpeedMultiplier = 1;
  let timer: ReturnType<typeof setInterval> | null = null;
  let running = false;

  const baseIntervalMs = scenario.meta.timeStep * 1000;

  const emitFrame = () => {
    if (frameIndex >= scenario.frames.length) {
      pause();
      callbacks.onComplete();
      return;
    }
    const frame = scenario.frames[frameIndex];
    callbacks.onTick(frameToSnapshot(frame, speedMultiplier));
    frameIndex++;
  };

  const pause = () => {
    running = false;
    if (timer) { clearInterval(timer); timer = null; }
  };

  const start = () => {
    if (frameIndex >= scenario.frames.length) frameIndex = 0;
    running = true;
    const interval = baseIntervalMs / speedMultiplier;
    timer = setInterval(emitFrame, interval);
  };

  const resume = () => {
    if (!running && frameIndex < scenario.frames.length) start();
  };

  const stop = () => {
    pause();
    frameIndex = 0;
  };

  const step = () => {
    pause();
    emitFrame();
  };

  const setSpeedMultiplier = (m: SpeedMultiplier) => {
    speedMultiplier = m;
    if (running) { pause(); start(); }
  };

  return {
    start, pause, resume, stop, step,
    setSpeedMultiplier,
    getFrameIndex: () => frameIndex,
    getTotalFrames: () => scenario.frames.length,
  };
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd frontend && npm test`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/mockReplayer.ts frontend/src/services/mockReplayer.test.ts
git commit -m "feat(frontend): add mock replay controller"
```

---

### Task 5: SimulationContext 集成 chartHistory

**Files:**
- Modify: `frontend/src/context/SimulationContext.tsx`

**Interfaces:**
- Consumes: `appendChartHistory`, `clearChartHistory`, `EMPTY_CHART_HISTORY` from `utils/chartHistory.ts`；`DEFAULT_VEHICLE_PARAMS` from `data/mockVehicleParams.ts`
- Produces: `CLEAR_CHART_HISTORY` action；`INIT_DEFAULT_PARAMS` action；`chartHistory` 在 `RUNTIME_UPDATE` 中自动追加

- [ ] **Step 1: 更新 initialState**

在 `params` 之后追加 `chartHistory`，并将 `params.vehicle` 初始化为 `DEFAULT_VEHICLE_PARAMS`：

```typescript
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';
import { EMPTY_CHART_HISTORY, appendChartHistory, clearChartHistory } from '../utils/chartHistory';

// initialState 中：
  params: {
    vehicle: { ...DEFAULT_VEHICLE_PARAMS },
    track: {},
    power: {},
    signal: {},
  },
  chartHistory: { ...EMPTY_CHART_HISTORY },
```

- [ ] **Step 2: 扩展 Action 类型**

```typescript
  | { type: 'CLEAR_CHART_HISTORY' }
  | { type: 'INIT_DEFAULT_PARAMS' }
```

- [ ] **Step 3: 更新 RUNTIME_UPDATE reducer 分支**

```typescript
    case 'RUNTIME_UPDATE': {
      const snapshot = action.payload;
      return {
        ...state,
        clock: snapshot.clock,
        trains: snapshot.trains,
        power: snapshot.power,
        signaling: snapshot.signaling,
        track: snapshot.track,
        events: [...state.events, ...snapshot.events].slice(-500),
        chartHistory: appendChartHistory(state.chartHistory, snapshot),
      };
    }
```

- [ ] **Step 4: 追加新 action 处理**

```typescript
    case 'CLEAR_CHART_HISTORY':
      return { ...state, chartHistory: clearChartHistory() };

    case 'INIT_DEFAULT_PARAMS':
      return {
        ...state,
        params: {
          ...state.params,
          vehicle: { ...DEFAULT_VEHICLE_PARAMS },
        },
      };
```

- [ ] **Step 5: 验证编译**

Run: `cd frontend && npm run build`
Expected: PASS（或仅剩其他无关警告）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): integrate chart history in simulation context"
```

---

### Task 6: useMockReplay Hook 与 App 集成

**Files:**
- Create: `frontend/src/hooks/useMockReplay.ts`
- Modify: `frontend/src/hooks/useSimulation.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/utils/constants.ts`
- Modify: `frontend/.env.example`

**Interfaces:**
- Consumes: `createMockReplayer`, `MockReplayScenario`, `SimulationContext` dispatch
- Produces: `useMockReplay(): { send: (data: object) => void }` — 与 `useWebSocket` 返回相同签名，可互换

- [ ] **Step 1: 更新 constants.ts**

```typescript
/** 是否使用 Mock 回放模式（预录 JSON 数据） */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';
```

- [ ] **Step 2: 更新 .env.example**

```
# 是否使用 Mock 回放（true=预录JSON，false=WebSocket）
VITE_USE_MOCK=true
```

- [ ] **Step 3: 创建 useMockReplay.ts**

```typescript
import { useEffect, useRef, useCallback } from 'react';
import { useSimulationDispatch } from '../context/SimulationContext';
import { createMockReplayer, type MockReplayer } from '../services/mockReplayer';
import scenarioData from '../data/mockReplay/scenario-default.json';
import type { MockReplayScenario, SpeedMultiplier } from '../types/simulation';

export function useMockReplay() {
  const dispatch = useSimulationDispatch();
  const replayerRef = useRef<MockReplayer | null>(null);

  useEffect(() => {
    dispatch({ type: 'WS_CONNECTED' });
    const scenario = scenarioData as MockReplayScenario;

    replayerRef.current = createMockReplayer(scenario, {
      onTick: (snapshot) => {
        dispatch({ type: 'RUNTIME_UPDATE', payload: snapshot });
      },
      onComplete: () => {
        dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
      },
    });

    return () => {
      replayerRef.current?.stop();
      dispatch({ type: 'WS_DISCONNECTED' });
    };
  }, [dispatch]);

  const send = useCallback((data: Record<string, unknown>) => {
    const replayer = replayerRef.current;
    if (!replayer) return;

    if (data.type === 'sim_control') {
      const action = data.action as string;
      switch (action) {
        case 'start':
          dispatch({ type: 'CLEAR_CHART_HISTORY' });
          replayer.stop();
          dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
          replayer.start();
          break;
        case 'pause':
          replayer.pause();
          dispatch({ type: 'SET_RUN_STATE', payload: 'paused' });
          break;
        case 'resume':
          replayer.resume();
          dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
          break;
        case 'stop':
          replayer.stop();
          dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
          break;
        case 'step':
          replayer.step();
          break;
      }
    }

    if (data.type === 'param_update') {
      dispatch({ type: 'UPDATE_PARAMS', payload: data.params as Partial<import('../types/simulation').SimulationParams> });
    }
  }, [dispatch]);

  return { send };
}
```

- [ ] **Step 4: 在 vite-env.d.ts 或 tsconfig 中启用 JSON import**

确认 `tsconfig.app.json` 包含 `"resolveJsonModule": true`（Vite 默认支持）。若无，追加：

```json
"resolveJsonModule": true
```

- [ ] **Step 5: 修改 App.tsx**

```typescript
import { USE_MOCK } from './utils/constants';
import { useMockReplay } from './hooks/useMockReplay';

function AppContent() {
  const { activeView } = useSimulationState();
  const ws = useWebSocket();
  const mock = useMockReplay();
  const { send } = USE_MOCK ? mock : ws;
  // ... rest unchanged
}
```

注意：`useMockReplay` 和 `useWebSocket` 都是 Hook，必须无条件调用。用 `USE_MOCK` 只决定用哪个 `send`。

- [ ] **Step 6: 修改 useSimulation.ts — stop 时清空历史**

在 `stopSimulation` 中追加：

```typescript
    dispatch({ type: 'CLEAR_CHART_HISTORY' });
```

在 `startSimulation` 中 Mock 模式由 `useMockReplay.send` 处理清空，REST/WS 模式需在 `startSimulation` 也清空：

```typescript
    dispatch({ type: 'CLEAR_CHART_HISTORY' });
```

- [ ] **Step 7: 手动验证 Mock 回放**

Run: `cd frontend && echo "VITE_USE_MOCK=true" > .env.local && npm run dev`
操作：
1. 打开浏览器 `http://localhost:5173`
2. 切换到「车辆视图」
3. 点击「运行」
4. 确认：速度-时间曲线开始绘制连续折线；工况指示器在牵引/惰行/制动间切换
Expected: 曲线连续增长，列车速度 0→64→0 循环

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useMockReplay.ts frontend/src/hooks/useSimulation.ts frontend/src/App.tsx frontend/src/utils/constants.ts frontend/.env.example
git commit -m "feat(frontend): wire mock replay into app entry"
```

---

### Task 7: 车辆视图曲线组件改造

**Files:**
- Modify: `frontend/src/components/views/vehicle/SpeedTimeCurve.tsx`
- Modify: `frontend/src/components/views/vehicle/AccelTimeCurve.tsx`
- Modify: `frontend/src/components/views/overview/SpeedPositionCurve.tsx`

**Interfaces:**
- Consumes: `chartHistory` from `useSimulationState()`
- Produces: 三个曲线组件读取历史数组而非单点

- [ ] **Step 1: 修改 SpeedTimeCurve.tsx**

将 `const { trains, clock }` 改为 `const { chartHistory, clock }`，series data 改为：

```typescript
data: chartHistory.speedTime,
```

xAxis max 改为动态：

```typescript
max: chartHistory.speedTime.length > 0
  ? Math.max(clock.elapsed + 10, chartHistory.speedTime[chartHistory.speedTime.length - 1][0] + 10)
  : 600,
```

- [ ] **Step 2: 修改 AccelTimeCurve.tsx**

同样改为 `chartHistory.accelTime`。

- [ ] **Step 3: 修改 SpeedPositionCurve.tsx**

改为 `chartHistory.speedPosition`，删除 TODO 注释。

- [ ] **Step 4: 手动验证**

Run Mock 模式 → 运行仿真 → 检查三个曲线均有连续折线
Expected: 速度-时间呈上升-平台-下降-归零；加速度有正/零/负；速度-位置沿 X 轴延伸

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/vehicle/SpeedTimeCurve.tsx frontend/src/components/views/vehicle/AccelTimeCurve.tsx frontend/src/components/views/overview/SpeedPositionCurve.tsx
git commit -m "feat(frontend): charts read accumulated history buffer"
```

---

### Task 8: 车辆参数表单补全（UI-PARAM-01）

**Files:**
- Modify: `frontend/src/components/param/VehicleParams.tsx`

**Interfaces:**
- Consumes: `DEFAULT_VEHICLE_PARAMS`, `VehicleParams`, `TractionCurvePoint`
- Produces: 完整车辆参数编辑表单（含牵引曲线表格）

- [ ] **Step 1: 扩展 VehicleParams.tsx 字段**

在现有 3 个字段基础上追加：

| 字段 | label |
|---|---|
| `max_traction_force` | 最大牵引力 (N) |
| `max_brake_force` | 最大制动力 (N) |
| `davis_A` | Davis A 系数 |
| `davis_B` | Davis B 系数 |
| `davis_C_front_area` | 迎风面积 (m²) |

- [ ] **Step 2: 追加牵引特性曲线表格**

在 fieldset 底部追加只读/可编辑表格，显示 `params.vehicle.traction_curve`：

```typescript
function TractionCurveTable({ curve, onChange }: {
  curve: TractionCurvePoint[] | undefined;
  onChange: (curve: TractionCurvePoint[]) => void;
}) {
  const points = curve ?? DEFAULT_VEHICLE_PARAMS.traction_curve;
  return (
    <table style={styles.table}>
      <thead><tr><th>速度 (km/h)</th><th>牵引力 %</th></tr></thead>
      <tbody>
        {points.map((pt, i) => (
          <tr key={i}>
            <td><input type="number" value={pt.speed}
              onChange={(e) => {
                const next = [...points];
                next[i] = { ...pt, speed: Number(e.target.value) };
                onChange(next);
              }} style={styles.input} /></td>
            <td><input type="number" step="0.1" min="0" max="1" value={pt.force_percent}
              onChange={(e) => {
                const next = [...points];
                next[i] = { ...pt, force_percent: Number(e.target.value) };
                onChange(next);
              }} style={styles.input} /></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

在 `handleChange` 旁新增 `handleCurveChange`：

```typescript
const handleCurveChange = (traction_curve: TractionCurvePoint[]) => {
  updateParams({ vehicle: { ...params.vehicle, traction_curve } });
};
```

- [ ] **Step 3: 手动验证**

打开参数面板 → 确认所有字段有默认值（来自 `DEFAULT_VEHICLE_PARAMS`）→ 修改空车质量 → 值实时更新
Expected: 表单显示 200000、1500、80、400000 等默认值

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/param/VehicleParams.tsx
git commit -m "feat(frontend): complete vehicle params form with traction curve"
```

---

### Task 9: 参数重置按钮（UI-PARAM-05）

**Files:**
- Modify: `frontend/src/components/param/VehicleParams.tsx`

**Interfaces:**
- Consumes: `INIT_DEFAULT_PARAMS` action 或 `updateParams({ vehicle: DEFAULT_VEHICLE_PARAMS })`
- Produces: 「恢复默认」按钮

- [ ] **Step 1: 在 VehicleParamsForm 底部追加重置按钮**

```typescript
import { DEFAULT_VEHICLE_PARAMS } from '../../data/mockVehicleParams';

// 在 </fieldset> 之前：
<button
  type="button"
  className="btn"
  style={styles.resetBtn}
  onClick={() => updateParams({ vehicle: { ...DEFAULT_VEHICLE_PARAMS } })}
>
  恢复默认
</button>

// styles 追加：
resetBtn: { marginTop: '6px', width: '100%', fontSize: '12px' },
```

- [ ] **Step 2: 手动验证**

修改几个参数 → 点击「恢复默认」→ 所有字段回到初始值
Expected: 空车质量回到 200000，牵引曲线回到 3 个折点

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/param/VehicleParams.tsx
git commit -m "feat(frontend): add vehicle params reset button"
```

---

### Task 10: 倍率选择与单步在 Mock 模式下的联动

**Files:**
- Modify: `frontend/src/components/control/SpeedSelector.tsx`
- Modify: `frontend/src/hooks/useMockReplay.ts`

**Interfaces:**
- Consumes: `MockReplayer.setSpeedMultiplier`
- Produces: 倍率选择器在 Mock 模式下加速回放

- [ ] **Step 1: 在 useMockReplay 的 send 中处理倍率**

在 `send` 函数中追加对自定义消息的处理，或扩展 `sim_control`：

当收到 `{ type: 'speed_multiplier', value: 5 }` 时调用 `replayer.setSpeedMultiplier(5)`。

- [ ] **Step 2: 修改 SpeedSelector.tsx**

在倍率变更时除发送 WS 消息外，也 dispatch 更新 clock：

```typescript
send({ type: 'speed_multiplier', value: multiplier });
```

- [ ] **Step 3: 手动验证**

选 10× 倍率 → 运行 → 曲线绘制速度明显加快
Expected: 回放帧间隔缩短为 1/10

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useMockReplay.ts frontend/src/components/control/SpeedSelector.tsx
git commit -m "feat(frontend): mock replay respects speed multiplier"
```

---

### Task 11: MVP 验收自测清单

**Files:** 无代码变更

- [ ] **Step 1: 场景 1 — 单列车一站直达**

| 检查项 | 操作 | 预期 |
|---|---|---|
| 速度-时间曲线 | 车辆视图 → 运行 | 上升→平台→下降→归零，循环 3 站 |
| 加速度曲线 | 同上 | 正→零→负→零 |
| 工况指示器 | 同上 | 牵引(绿)→惰行(灰)→制动(红) 交替 |
| 仿真时钟 | 顶部栏 | 数字递增，站停时继续走 |

- [ ] **Step 2: 场景 2 — 坡度影响（视觉确认）**

B→C 段加速度在数据生成时已设为 0.5（低于 A→B 的 0.8），确认上坡段加速度曲线更低。

- [ ] **Step 3: 场景 3 — 仿真控制**

| 操作 | 预期 |
|---|---|
| 暂停 | 曲线停止增长，数值冻结 |
| 继续 | 从断点继续 |
| 停止 | 状态变 stopped，回放归零 |
| 单步 | 每次推进 1 帧 |

- [ ] **Step 4: 场景 4 — 参数编辑**

修改空车质量 200000→220000 → 本地 state 更新（Mock 模式不影响预录曲线，但表单功能正常）。后期接 API 后此参数将影响仿真。

- [ ] **Step 5: 构建验证**

Run: `cd frontend && npm run build && npm test`
Expected: build PASS, all tests PASS

- [ ] **Step 6: Commit（如有验收中修复）**

```bash
git add -A
git commit -m "fix(frontend): address issues found in MVP acceptance testing"
```

---

## Spec Coverage Self-Review

| MVP 需求 | 对应 Task | 状态 |
|---|---|---|
| UI-VHC-01 速度-时间曲线 | Task 5 + 7 | ✅ |
| UI-VHC-02 加速度-时间曲线 | Task 5 + 7 | ✅ |
| UI-VHC-03 工况指示器 | 已实现，Task 11 验收 | ✅ |
| UI-PARAM-01 车辆参数编辑 | Task 8 | ✅ |
| UI-PARAM-05 参数重置 | Task 9 | ✅ |
| UI-VW-03 速度-位置曲线 | Task 7 | ✅ |
| 验收场景 1-4 | Task 11 | ✅ |
| UI-VHC-04/05 | 不在范围，保持占位 | ⏭️ |
| WebSocket 接 API | Task 6 通过 `VITE_USE_MOCK=false` 切换 | ✅ |

## Placeholder Scan

- 无 TBD / TODO / "implement later" 残留
- 所有代码步骤均包含完整实现
- 类型命名前后一致：`MockReplayFrame.t` → `SimulationSnapshot.clock.elapsed`

## 后期接 API 切换指南

1. 设置 `.env.local` 中 `VITE_USE_MOCK=false`
2. 启动后端 WebSocket 服务
3. `useWebSocket` 自动接管，`RUNTIME_UPDATE` 路径不变
4. 可选：在 `useWebSocket` 中处理 `init_state`，调用 `dispatch({ type: 'INIT_DEFAULT_PARAMS' })` 从后端加载车辆配置
5. 预录 JSON 文件保留，用于离线演示和回归测试
