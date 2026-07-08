# 参数驱动 Mock 轨迹生成实现规划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在 Mock 模式下修改车辆/线路/信号参数后，重新运行时速度-时间、加速度-时间曲线能按 MVP 物理规律变化，而不是播放固定 JSON。

**Architecture:** 放弃「多套预录 JSON」和「事后缩放曲线」两条死路，改为 **运行时轨迹生成器**：保留线路蓝图（车站/区间/坡度/限速）为静态配置，每次点击「运行」时用当前 `params.vehicle` + `params.track` + `params.signal` 做简化单质点积分（F=ma + Davis 阻力 + 坡度阻力 + 三段式工况），输出 `MockReplayFrame[]` 交给现有 `mockReplayer` 播放。`scenario-default.json` 降级为回归测试金标准，不再作为运行时数据源。

**Tech Stack:** React 19, TypeScript 6, Vitest, 现有 mockReplayer / chartHistory 链路不变

## 为什么不用「多套预录」或「参数缩放」

| 方案 | 问题 |
|------|------|
| 多套预录 JSON | 空车质量、牵引力、制动力、迎风面积、Davis 系数、牵引曲线、限速…组合爆炸，无法穷举 |
| 事后缩放近似 | 只能处理单一维度近似（如质量∝加速度），无法表达 Davis 二次项、牵引曲线折点、限速截断、坡度附加阻力等非线性耦合 |

**正确做法：** 参数进入 **生成器输入**，在积分循环里每步重算阻力/牵引/加速度，与后端 MVP 车辆系统（VHC-01~08）语义对齐。

## Global Constraints

- 所有新增/修改文件放在 `frontend/src/` 下，遵循现有目录结构
- 组件使用 inline `styles` 对象
- 类型追加到 `types/simulation.ts`，不新建类型文件
- Mock 相关纯函数放在 `frontend/src/mock/` 目录（新建）
- 字段命名前端内部统一 snake_case
- 仿真步长 `dt = 0.1` s（与 MVP `timeStep` 一致）
- 目标速度 `v_target = speed_limit × target_speed_ratio`（默认 ratio=0.8，来自 `params.signal`）
- AW2 载客：`passenger_count = passenger_capacity × 0.6`（MVP 验收场景 1）
- 参数修改在 **下次点击「运行」** 时生效（运行中改参不热更新，避免状态混乱）
- 后期接 API 时：删除生成器调用，保留 `mockReplayer` 消费 WebSocket snapshot 的路径

## 方案对比（已决策）

```
❌ 方案 1：N 套 JSON（default / heavy / low-drag …）
❌ 方案 2：base JSON + 速度/加速度线性缩放
✅ 方案 3：运行时参数化积分生成（本计划）
```

## File Structure

| 文件 | 职责 | 操作 |
|---|---|---|
| `src/mock/mockTrackBlueprint.ts` | MVP 三站两区间静态线路（A0-B1500-C3200，含 B→C 上坡 30‰） | 新增 |
| `src/mock/mockDynamics.ts` | 质量、Davis 阻力、坡度阻力、牵引力查表、制动力 | 新增 |
| `src/mock/mockThreeStage.ts` | 三段式工况判定（牵引/惰行/制动） | 新增 |
| `src/mock/generateMockTrajectory.ts` | 主积分循环 → `MockReplayFrame[]` | 新增 |
| `src/mock/mockDynamics.test.ts` | 动力学纯函数单测 | 新增 |
| `src/mock/generateMockTrajectory.test.ts` | 轨迹生成集成单测（验收场景 4） | 新增 |
| `src/hooks/useMockReplay.ts` | start 时用当前 params 生成轨迹，再交给 replayer | 修改 |
| `src/services/mockReplayer.ts` | 新增 `loadScenario(scenario)` 热替换帧数据 | 修改 |
| `src/data/mockReplay/scenario-default.json` | 仅作金标准 fixture，运行时不再 import | 保留 |
| `src/components/param/VehicleParams.tsx` | 追加提示「参数在下次运行时生效」 | 修改 |
| `scripts/generate-mock-replay.mjs` | 改为调用 TS 生成器输出金标准（或标注 deprecated） | 修改 |

---

### Task 1: 线路蓝图与仿真输入类型

**Files:**
- Create: `frontend/src/mock/mockTrackBlueprint.ts`
- Modify: `frontend/src/types/simulation.ts`

**Interfaces:**
- Consumes: `Segment`, `Station` from `types/simulation.ts`
- Produces: `MOCK_TRACK_BLUEPRINT` 常量；`MockSimInput` 接口

- [ ] **Step 1: 追加 MockSimInput 类型**

在 `types/simulation.ts` 的 `MockReplayScenario` 附近追加：

```typescript
/** Mock 轨迹生成器输入（车辆 + 线路 + 信号参数快照） */
export interface MockSimInput {
  vehicle: VehicleParams;
  track: {
    gradient: number;      // ‰，上坡为正；MVP 先支持全局坡度覆盖 B→C 段
    curvature: number;     // m，MVP 弯道阻力可简化为 0
    speed_limit: number;   // km/h
  };
  signal: {
    dwell_time: number;           // s，默认 30
    target_speed_ratio: number;   // 默认 0.8
  };
  passenger_load_ratio: number;   // 0~1，默认 0.6 (AW2)
}
```

- [ ] **Step 2: 创建 mockTrackBlueprint.ts**

```typescript
import type { Station, Segment } from '../types/simulation';

/** MVP 验收线路：A(0) → B(1500) → C(3200)，2 区间 */
export const MOCK_STATIONS: Station[] = [
  { id: 'ST01', name: 'A站', chainage: 0, dwell_time: 30, platform_half_length: 15, is_terminus: true, sort_order: 1 },
  { id: 'ST02', name: 'B站', chainage: 1500, dwell_time: 30, platform_half_length: 15, is_terminus: false, sort_order: 2 },
  { id: 'ST03', name: 'C站', chainage: 3200, dwell_time: 30, platform_half_length: 15, is_terminus: true, sort_order: 3 },
];

export const MOCK_SEGMENTS: Segment[] = [
  { id: 'SEC01', start_chainage: 0, end_chainage: 1500, gradient: 5, curvature: 800, speed_limit: 80, is_tunnel: false, sort_order: 1 },
  { id: 'SEC02', start_chainage: 1500, end_chainage: 3200, gradient: 30, curvature: 1200, speed_limit: 80, is_tunnel: false, sort_order: 2 },
];

export function getSegmentAt(position: number, gradientOverride?: number): Segment {
  const seg = MOCK_SEGMENTS.find(s => position >= s.start_chainage && position < s.end_chainage) ?? MOCK_SEGMENTS[MOCK_SEGMENTS.length - 1];
  if (gradientOverride !== undefined && seg.id === 'SEC02') {
    return { ...seg, gradient: gradientOverride };
  }
  return seg;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/mock/mockTrackBlueprint.ts
git commit -m "feat(frontend): add mock track blueprint and sim input types"
```

---

### Task 2: 动力学纯函数（多参数耦合）

**Files:**
- Create: `frontend/src/mock/mockDynamics.ts`
- Create: `frontend/src/mock/mockDynamics.test.ts`

**Interfaces:**
- Consumes: `VehicleParams`, `MockSimInput`
- Produces:
  - `computeMass(vehicle, passengerLoadRatio): number`
  - `computeDavisResistance(speedMs, mass, vehicle): number`
  - `computeGradeResistance(gradientPermil, mass): number`
  - `lookupTractionForce(speedKmh, vehicle): number`
  - `computeAcceleration({ mode, speedKmh, mass, vehicle, gradient }): number`

- [ ] **Step 1: 写失败测试 — 质量影响加速度**

```typescript
import { describe, it, expect } from 'vitest';
import { computeMass, computeAcceleration } from './mockDynamics';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';

describe('computeAcceleration respects mass', () => {
  it('heavier train has lower traction acceleration', () => {
    const light = { ...DEFAULT_VEHICLE_PARAMS, empty_mass: 200_000 };
    const heavy = { ...DEFAULT_VEHICLE_PARAMS, empty_mass: 220_000 };
    const aLight = computeAcceleration({ mode: 'traction', speedKmh: 20, mass: computeMass(light, 0.6), vehicle: light, gradient: 0 });
    const aHeavy = computeAcceleration({ mode: 'traction', speedKmh: 20, mass: computeMass(heavy, 0.6), vehicle: heavy, gradient: 0 });
    expect(aHeavy).toBeLessThan(aLight);
  });
});
```

- [ ] **Step 2: 写失败测试 — 迎风面积影响惰行减速度**

```typescript
it('larger frontal area increases resistance deceleration', () => {
  const small = { ...DEFAULT_VEHICLE_PARAMS, davis_C_front_area: 8 };
  const large = { ...DEFAULT_VEHICLE_PARAMS, davis_C_front_area: 14 };
  const m = computeMass(small, 0.6);
  const aSmall = computeAcceleration({ mode: 'coasting', speedKmh: 60, mass: m, vehicle: small, gradient: 0 });
  const aLarge = computeAcceleration({ mode: 'coasting', speedKmh: 60, mass: m, vehicle: large, gradient: 0 });
  expect(aLarge).toBeLessThan(aSmall); // 更负
});
```

- [ ] **Step 3: 写失败测试 — 牵引力上限影响加速**

```typescript
it('lower max traction reduces acceleration', () => {
  const base = DEFAULT_VEHICLE_PARAMS;
  const weak = { ...base, max_traction_force: 300_000 };
  const m = computeMass(base, 0.6);
  const aBase = computeAcceleration({ mode: 'traction', speedKmh: 10, mass: m, vehicle: base, gradient: 0 });
  const aWeak = computeAcceleration({ mode: 'traction', speedKmh: 10, mass: m, vehicle: weak, gradient: 0 });
  expect(aWeak).toBeLessThan(aBase);
});
```

- [ ] **Step 4: 实现 mockDynamics.ts**

核心公式（与 MVP 2.3 对齐）：

```typescript
const G = 9.81;
const RHO = 1.2;

export function kmhToMs(v: number) { return v / 3.6; }
export function msToKmh(v: number) { return v * 3.6; }

export function computeMass(vehicle: VehicleParams, passengerLoadRatio: number): number {
  const passengers = vehicle.passenger_capacity * passengerLoadRatio * 60; // 60 kg/人
  return vehicle.empty_mass + passengers;
}

export function computeDavisResistance(speedMs: number, mass: number, vehicle: VehicleParams): number {
  const A = vehicle.davis_A * mass * G;
  const B = vehicle.davis_B * mass * G;
  const C = 0.5 * RHO * vehicle.davis_C_drag_coeff * vehicle.davis_C_front_area;
  return A + B * speedMs + C * speedMs * speedMs;
}

export function computeGradeResistance(gradientPermil: number, mass: number): number {
  return mass * G * (gradientPermil / 1000);
}

export function lookupTractionForce(speedKmh: number, vehicle: VehicleParams): number {
  const curve = [...vehicle.traction_curve].sort((a, b) => a.speed - b.speed);
  let percent = curve[0]?.force_percent ?? 1;
  for (let i = 1; i < curve.length; i++) {
    if (speedKmh <= curve[i].speed) {
      const prev = curve[i - 1];
      const t = (speedKmh - prev.speed) / (curve[i].speed - prev.speed);
      percent = prev.force_percent + t * (curve[i].force_percent - prev.force_percent);
      break;
    }
    percent = curve[i].force_percent;
  }
  return vehicle.max_traction_force * percent;
}

export function computeAcceleration(args: {
  mode: 'traction' | 'coasting' | 'braking';
  speedKmh: number;
  mass: number;
  vehicle: VehicleParams;
  gradient: number;
}): number {
  const v = kmhToMs(args.speedKmh);
  const resist = computeDavisResistance(v, args.mass, args.vehicle)
    + computeGradeResistance(args.gradient, args.mass);
  let force = 0;
  if (args.mode === 'traction') force = lookupTractionForce(args.speedKmh, args.vehicle);
  if (args.mode === 'braking') force = -args.vehicle.max_brake_force;
  return (force - resist) / args.mass;
}
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm test -- src/mock/mockDynamics.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/mock/mockDynamics.ts frontend/src/mock/mockDynamics.test.ts
git commit -m "feat(frontend): add parametric mock dynamics"
```

---

### Task 3: 三段式工况 + 轨迹积分主循环

**Files:**
- Create: `frontend/src/mock/mockThreeStage.ts`
- Create: `frontend/src/mock/generateMockTrajectory.ts`
- Create: `frontend/src/mock/generateMockTrajectory.test.ts`

**Interfaces:**
- Consumes: `MockSimInput`, `MOCK_STATIONS`, `MOCK_SEGMENTS`, `mockDynamics`
- Produces: `generateMockTrajectory(input): MockReplayFrame[]`

- [ ] **Step 1: 写失败测试 — 验收场景 4（质量变大 → 站间时间变长）**

```typescript
import { describe, it, expect } from 'vitest';
import { generateMockTrajectory } from './generateMockTrajectory';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';
import type { MockSimInput } from '../types/simulation';

function makeInput(emptyMass: number): MockSimInput {
  return {
    vehicle: { ...DEFAULT_VEHICLE_PARAMS, empty_mass: emptyMass },
    track: { gradient: 30, curvature: 1200, speed_limit: 80 },
    signal: { dwell_time: 30, target_speed_ratio: 0.8 },
    passenger_load_ratio: 0.6,
  };
}

describe('generateMockTrajectory', () => {
  it('heavier train takes longer between A and B', () => {
    const light = generateMockTrajectory(makeInput(200_000));
    const heavy = generateMockTrajectory(makeInput(220_000));
    const lightArriveB = light.find(f => f.position >= 1490 && f.speed < 1)?.t ?? Infinity;
    const heavyArriveB = heavy.find(f => f.position >= 1490 && f.speed < 1)?.t ?? Infinity;
    expect(heavyArriveB).toBeGreaterThan(lightArriveB);
  });
});
```

- [ ] **Step 2: 写失败测试 — 限速/目标速度影响最高速度**

```typescript
it('lower speed limit caps cruise speed', () => {
  const input = makeInput(200_000);
  const fast = generateMockTrajectory(input);
  const slow = generateMockTrajectory({
    ...input,
    track: { ...input.track, speed_limit: 60 },
  });
  const maxFast = Math.max(...fast.map(f => f.speed));
  const maxSlow = Math.max(...slow.map(f => f.speed));
  expect(maxSlow).toBeLessThan(maxFast);
  expect(maxSlow).toBeLessThanOrEqual(60 * 0.8 + 1); // v_target + 容差
});
```

- [ ] **Step 3: 实现 mockThreeStage.ts**

按 MVP 2.5.1：
- `v_target = min(segment.speed_limit, track.speed_limit 覆盖) × target_speed_ratio`
- 制动触发距离 `d_brake = v² / (2 × a_brake)`（`a_brake = max_brake_force / mass`）
- 距下一站台中心 ≤ `d_brake` → 制动；`v < v_target` → 牵引；否则惰行

```typescript
export function decideMode(state: {
  speedKmh: number;
  position: number;
  nextStationChainage: number;
  vTarget: number;
  mass: number;
  maxBrakeForce: number;
}): 'traction' | 'coasting' | 'braking' {
  const vMs = state.speedKmh / 3.6;
  const aBrake = state.maxBrakeForce / state.mass;
  const dBrake = (vMs * vMs) / (2 * aBrake);
  const distToStation = state.nextStationChainage - state.position;
  if (distToStation <= dBrake) return 'braking';
  if (state.speedKmh < state.vTarget - 0.5) return 'traction';
  return 'coasting';
}
```

- [ ] **Step 4: 实现 generateMockTrajectory.ts**

```typescript
import { MOCK_STATIONS, getSegmentAt } from './mockTrackBlueprint';
import { computeMass, computeAcceleration, msToKmh, kmhToMs } from './mockDynamics';
import { decideMode } from './mockThreeStage';
import type { MockReplayFrame, MockSimInput } from '../types/simulation';

const DT = 0.1;

export function generateMockTrajectory(input: MockSimInput): MockReplayFrame[] {
  const frames: MockReplayFrame[] = [];
  const mass = computeMass(input.vehicle, input.passenger_load_ratio);
  let t = 0;
  let position = MOCK_STATIONS[0].chainage;
  let speedKmh = 0;
  let stationIdx = 0;

  while (stationIdx < MOCK_STATIONS.length) {
    const nextStation = MOCK_STATIONS[stationIdx + 1];
    if (!nextStation) break;

    const seg = getSegmentAt(position, input.track.gradient);
    const speedLimit = input.track.speed_limit ?? seg.speed_limit;
    const vTarget = speedLimit * input.signal.target_speed_ratio;

    const mode = decideMode({
      speedKmh, position,
      nextStationChainage: nextStation.chainage,
      vTarget, mass,
      maxBrakeForce: input.vehicle.max_brake_force,
    });

    const gradient = seg.id === 'SEC02' ? input.track.gradient : seg.gradient;
    const acceleration = computeAcceleration({ mode, speedKmh, mass, vehicle: input.vehicle, gradient });

    frames.push({
      t: Math.round(t * 10) / 10,
      position: Math.round(position * 10) / 10,
      speed: Math.round(speedKmh * 10) / 10,
      acceleration: Math.round(acceleration * 100) / 100,
      mode,
      mass,
      passenger_count: Math.round(input.vehicle.passenger_capacity * input.passenger_load_ratio),
      pantograph_voltage: 1500,
      power_demand: mode === 'traction' ? 3200 : 0,
    });

    const vMs = kmhToMs(speedKmh);
    const vNext = Math.max(0, vMs + acceleration * DT);
    speedKmh = msToKmh(vNext);
    position += ((kmhToMs(speedKmh) + vMs) / 2) * DT;
    t += DT;

    if (speedKmh < 0.5 && Math.abs(position - nextStation.chainage) < 1) {
      // 到站停车 + dwell
      for (let d = 0; d < input.signal.dwell_time; d += DT) {
        frames.push({ t, position: nextStation.chainage, speed: 0, acceleration: 0, mode: 'coasting', mass, passenger_count: frames.at(-1)!.passenger_count, pantograph_voltage: 1500, power_demand: 0 });
        t += DT;
      }
      stationIdx++;
      position = nextStation.chainage;
      speedKmh = 0;
    }

    if (t > 600) break; // 安全阀
  }
  return frames;
}
```

- [ ] **Step 5: 运行测试并调参**

Run: `cd frontend && npm test -- src/mock/`
Expected: PASS（若制动距离导致过冲，调 `d_brake` 系数或停车判定容差）

- [ ] **Step 6: Commit**

```bash
git add frontend/src/mock/mockThreeStage.ts frontend/src/mock/generateMockTrajectory.ts frontend/src/mock/generateMockTrajectory.test.ts
git commit -m "feat(frontend): parametric mock trajectory generator"
```

---

### Task 4: 接入回放器（params → 曲线）

**Files:**
- Modify: `frontend/src/services/mockReplayer.ts`
- Modify: `frontend/src/hooks/useMockReplay.ts`
- Modify: `frontend/src/context/SimulationContext.tsx`

**Interfaces:**
- Consumes: `generateMockTrajectory`, `useSimulationState().params`
- Produces: `MockReplayer.loadScenario(scenario: MockReplayScenario): void`

- [ ] **Step 1: mockReplayer 新增 loadScenario**

```typescript
export function createMockReplayer(initial: MockReplayScenario, callbacks: MockReplayerCallbacks): MockReplayer {
  let scenario = initial;
  // ...existing code uses scenario.frames...
  const loadScenario = (next: MockReplayScenario) => {
    pause();
    scenario = next;
    frameIndex = 0;
  };
  return { start, pause, resume, stop, step, setSpeedMultiplier, getFrameIndex, getTotalFrames, loadScenario };
}
```

- [ ] **Step 2: useMockReplay 在 start 时生成轨迹**

```typescript
import { generateMockTrajectory } from '../mock/generateMockTrajectory';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';
import { useSimulationState } from '../context/SimulationContext';

// 在 hook 内：
const { params } = useSimulationState();

function buildScenario() {
  const input: MockSimInput = {
    vehicle: { ...DEFAULT_VEHICLE_PARAMS, ...params.vehicle },
    track: {
      gradient: params.track.gradient ?? 30,
      curvature: params.track.curvature ?? 1200,
      speed_limit: params.track.speed_limit ?? 80,
    },
    signal: {
      dwell_time: params.signal.dwell_time ?? 30,
      target_speed_ratio: params.signal.target_speed_ratio ?? 0.8,
    },
    passenger_load_ratio: 0.6,
  };
  const frames = generateMockTrajectory(input);
  return { meta: { name: 'generated', description: '', timeStep: 0.1, totalDuration: frames.at(-1)?.t ?? 0 }, vehicleParams: input.vehicle, frames };
}

// sim_control start 分支：
case 'start': {
  dispatch({ type: 'CLEAR_CHART_HISTORY' });
  replayer.stop();
  replayer.loadScenario(buildScenario());
  dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
  replayer.start();
  break;
}
```

- [ ] **Step 3: 移除 useMockReplay 对 scenario-default.json 的运行时 import**

初始化 replayer 时用空帧或默认单帧占位，真正数据在 start 时注入。

- [ ] **Step 4: 手动验证**

1. 空车质量 200000 → 运行 → 记录 A→B 时间
2. 改为 220000 → 停止 → 再运行
3. 预期：第二次曲线加速段更平缓、到站更晚

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/mockReplayer.ts frontend/src/hooks/useMockReplay.ts
git commit -m "feat(frontend): regenerate mock trajectory from params on start"
```

---

### Task 5: UI 提示与参数面板默认值

**Files:**
- Modify: `frontend/src/components/param/VehicleParams.tsx`
- Modify: `frontend/src/components/param/TrackParams.tsx`
- Modify: `frontend/src/context/SimulationContext.tsx`

- [ ] **Step 1: 初始化 track/signal 默认值**

```typescript
// SimulationContext initialState.params
track: { gradient: 30, curvature: 1200, speed_limit: 80 },
signal: { dwell_time: 30, target_speed_ratio: 0.8 },
```

- [ ] **Step 2: 参数面板追加提示**

在 `VehicleParams` legend 下方：

```tsx
<div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
  参数在下次点击「运行」时生效
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/param/VehicleParams.tsx frontend/src/components/param/TrackParams.tsx frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): default track/signal params and apply-on-run hint"
```

---

### Task 6: 金标准 JSON 与脚本同步

**Files:**
- Modify: `frontend/scripts/generate-mock-replay.mjs`
- Create: `frontend/src/mock/exportScenarioFixture.ts`（可选，供脚本调用）

- [ ] **Step 1: 用 vitest 导出金标准**

在 `generateMockTrajectory.test.ts` 追加：

```typescript
it('exports golden fixture matching scenario-default shape', () => {
  const frames = generateMockTrajectory(makeInput(200_000));
  expect(frames.length).toBeGreaterThan(100);
  expect(frames[0].speed).toBe(0);
});
```

- [ ] **Step 2: 更新 generate-mock-replay.mjs 注释**

标注：运行时不再读取此文件；仅用于离线生成回归 fixture。后续可用 `npx tsx src/mock/cli-export-fixture.ts` 替代。

- [ ] **Step 3: Commit**

```bash
git add frontend/scripts/generate-mock-replay.mjs frontend/src/mock/
git commit -m "chore(frontend): document mock json as test fixture only"
```

---

### Task 7: MVP 验收自测清单

- [ ] **场景 4：改空车质量 200t→220t**

| 检查 | 预期 |
|------|------|
| 牵引段加速度峰值 | 220t 更低 |
| A→B 运行时间 | 220t 更长 |
| 速度最高值 | 可能略低（阻力+质量） |

- [ ] **改最大牵引力 400k→300k**

加速度峰值明显下降。

- [ ] **改迎风面积 10→14**

惰行段减速更陡（速度掉得更快）。

- [ ] **改限速 80→60**

巡航平台速度降至约 48 km/h（60×0.8）。

- [ ] **改坡度 30‰→5‰（B→C 段）**

B→C 段加速度负偏移减小，运行时间缩短。

- [ ] **全量测试 + 构建**

Run: `cd frontend && npm test && npm run build`
Expected: PASS

---

## Spec Coverage Self-Review

| 需求 | Task | 覆盖 |
|------|------|------|
| MVP 场景 4 参数编辑验证 | Task 3 测试 + Task 7 | ✅ |
| VHC-01 F=ma | Task 2 | ✅ |
| VHC-02 牵引曲线 | Task 2 lookupTractionForce | ✅ |
| VHC-03 Davis 阻力 | Task 2 | ✅ |
| VHC-04 坡度阻力 | Task 2 | ✅ |
| VHC-07 限速约束 | Task 3 vTarget | ✅ |
| UI-PARAM-01/02 参数影响仿真 | Task 4 | ✅ |
| 多参数耦合（非单质量缩放） | Task 2 全部测试 | ✅ |

## 后期接 API 时怎么切换

1. `VITE_USE_MOCK=false`
2. 删除/跳过 `buildScenario()` 调用
3. WebSocket `simulation_snapshot` 继续走 `RUNTIME_UPDATE` → `chartHistory`
4. `generateMockTrajectory` 保留用于单元测试与离线演示

## 参数 → 物理效应速查（给前端开发对照）

| 参数 | 影响的曲线特征 |
|------|----------------|
| `empty_mass` ↑ | 加速度幅值 ↓，站间时间 ↑ |
| `max_traction_force` ↓ | 牵引段加速度 ↓，达到 v_target 更慢 |
| `max_brake_force` ↓ | 制动段更平缓，制动距离更长 |
| `davis_C_front_area` ↑ | 高速段阻力 ↑，惰行减速更快 |
| `davis_A/B` ↑ | 全速域阻力 ↑ |
| `traction_curve` 折点 | 高速段牵引力 ↓，巡航速度可能降低 |
| `max_speed` / `speed_limit` | 速度平台上限 |
| `gradient` ↑ | 上坡段加速度额外负偏移 |
| `target_speed_ratio` ↓ | 巡航目标速度降低 |
