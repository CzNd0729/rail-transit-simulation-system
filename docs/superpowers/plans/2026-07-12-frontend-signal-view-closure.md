# 信号视图前端收尾 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成迭代二信号前端 UI-SIG-01~03 的收尾与后端联调，使 Live/Mock 双模式下 MA 图、速度包络线、运行图均能消费后端 signaling 字段（`maProfile` / `speedLimits` / `timetableDeviation` / `runningPhase`），并通过验收场景 4、7、8。

**Architecture:** Phase 1（方案 A 前端自洽）已基本完成。Phase 2 在 `apiAdapter` 层扩展 `SignalState`，新增 `signalSelectors.ts` 纯函数解析后端字段；三张子图优先读后端数据、缺失时降级到现有推导逻辑；Mock 模式补齐 `frameToSnapshot` 信号字段以保持双模式一致。

**Tech Stack:** React 19 + TypeScript 6.0, Vite 8.1, ECharts 6 + echarts-for-react, vitest 4

## Global Constraints

- 分支：`feat/frontend-signal-view`（基于 `dev`）；若已在 `dev` 上开发则继续当前分支
- 不新增 npm 依赖
- 不修改后端 Python 文件（信号前端负责人范围；后端字段缺失时前端做降级，并记录协调项）
- 不修改 `SignalView.tsx` 布局结构（仅可追加状态条子组件）
- `MA_ENVELOPE_LENGTH = 300` 作为后端 `maProfile` 缺失时的 fallback
- ATP 紧急制动曲线完整版留迭代三；本计划仅增加 `atpLimit` 虚线（后端已推送）
- 组件遵循函数组件 + Hooks，暗色主题 CSS 变量
- 提交格式：`feat(frontend): <中文描述>`（≤50 字符，caveman-commit）
- 每 Task 完成后运行：`cd frontend && npm run test && npx tsc -b && npm run lint`

**设计文档：** `docs/superpowers/specs/2026-07-10-frontend-signal-view-design.md`  
**Phase 1 计划（已完成）：** `docs/superpowers/plans/2026-07-10-frontend-signal-view-plan.md`

## File Map

| 文件 | 职责 |
|------|------|
| `frontend/src/types/simulation.ts` | 扩展 `SignalState`、API 原始类型 |
| `frontend/src/utils/apiAdapter.ts` | 映射 `maProfile` / `speedLimits` / `timetableDeviation` |
| `frontend/src/utils/signalSelectors.ts` | **新增** — 从 `SignalState` 解析 MA 终点、ATP 限速、ATS 偏差 |
| `frontend/src/utils/signalSelectors.test.ts` | **新增** — selector 单元测试 |
| `frontend/src/utils/frameToSnapshot.ts` | Mock 模式补齐 signaling 字段 |
| `frontend/src/mock/generateMockTrajectory.ts` | Mock 帧扩展 `running_phase` 等（可选字段） |
| `frontend/src/components/views/signal/MAChart.tsx` | 消费 `maProfile.ma_end_chainage` |
| `frontend/src/components/views/signal/SpeedEnvelope.tsx` | 新增 ATP 限速线 |
| `frontend/src/components/views/signal/TimetableChart.tsx` | 显示 ATS 晚点标注 |
| `frontend/src/components/views/signal/SignalStatusBar.tsx` | **新增** — 相位/EB/ATS 状态条 |
| `frontend/src/pages/SignalView.tsx` | 挂载 `SignalStatusBar` |
| `frontend/src/components/param/SignalParams.tsx` | Live 模式禁用不可写参数 + 提示 |

## 后端字段契约（只读，不改后端）

编排器当前推送（`backend/sim_engine/data/snapshot.py` + `orchestrator.py`）：

```json
{
  "signaling": {
    "controlCommands": [{
      "trainId": "TRAIN_01",
      "tractionLevel": 0.3,
      "brakeLevel": 0,
      "emergencyBrake": false,
      "runningPhase": "traction"
    }],
    "speedLimits": [{
      "trainId": "TRAIN_01",
      "permanentLimit": 80,
      "atpLimit": 76
    }],
    "maProfile": [{
      "trainId": "TRAIN_01",
      "maEndChainage": 1800,
      "safetyDistance": 300
    }],
    "timetableDeviation": [{
      "trainId": "TRAIN_01",
      "stationId": "ST_B",
      "delayArrival": 2.5,
      "nominalDwell": 30,
      "adjustedDwell": 32.5
    }]
  }
}
```

---

### Task 1: Phase 1 收尾 — 验证并提交现有 WIP

**Files:**
- Verify: `frontend/src/pages/SignalView.tsx`
- Verify: `frontend/src/components/views/signal/MAChart.tsx`
- Verify: `frontend/src/components/views/signal/TimetableChart.tsx`
- Verify: `frontend/src/types/simulation.ts`
- Verify: `frontend/src/utils/constants.ts`

**Interfaces:**
- Produces: 已合并或已提交的 Phase 1 代码基线（UI-SIG-01~03 数据驱动版）

- [ ] **Step 1: 全量验证**

```bash
cd frontend && npm run test && npx tsc -b && npm run lint
```

Expected: 全部 PASS

- [ ] **Step 2: 手动 Smoke（Mock 模式）**

```bash
# .env: VITE_USE_MOCK=true
cd frontend && npm run dev
```

操作清单：
1. 切换「信号视图」→ 点击「运行」
2. MA 图列车移动、300m 包络、目标站名正确
3. 速度包络三条曲线更新
4. 运行图轨迹累积、站名参考线可见

- [ ] **Step 3: 提交未提交改动（若有）**

```bash
git status
git add frontend/src/pages/SignalView.tsx \
        frontend/src/components/views/signal/MAChart.tsx \
        frontend/src/components/views/signal/TimetableChart.tsx \
        frontend/src/types/simulation.ts \
        frontend/src/utils/constants.ts
git commit -m "feat(frontend): 信号视图 MA 与运行图优化"
```

Expected: working tree clean（或仅剩本计划后续 Task 的改动）

---

### Task 2: 扩展 SignalState 类型与 apiAdapter 映射

**Files:**
- Modify: `frontend/src/types/simulation.ts:165-187,390-414`
- Modify: `frontend/src/utils/apiAdapter.ts:48-91`
- Modify: `frontend/src/utils/apiAdapter.test.ts`（追加测试）

**Interfaces:**
- Produces: `MaProfileEntry { train_id, ma_end_chainage, safety_distance }`
- Produces: `SpeedLimitEntry { train_id, permanent_limit, atp_limit }`
- Produces: `TimetableDeviationEntry { train_id, station_id, delay_arrival, nominal_dwell, adjusted_dwell }`
- Produces: `SignalState.ma_profiles`, `speed_limits`, `timetable_deviations`
- Consumes (later): `signalSelectors.ts` 读取上述字段

- [ ] **Step 1: 写失败测试**

在 `frontend/src/utils/apiAdapter.test.ts` 末尾追加：

```typescript
  it('maps maProfile, speedLimits, timetableDeviation from backend', () => {
    const raw = {
      clock: { elapsed: 45, speedMultiplier: 1 as const },
      trains: [{
        id: 'TRAIN_01', position: 800, speed: 60, acceleration: 0,
        mode: 'traction' as const, mass: 254000, passengerCount: 900,
        pantographVoltage: 1480, powerDemand: 1200, doorStatus: 'closed' as const,
        distanceToStation: 700, targetStationId: 'ST_B', faultAlarm: null,
      }],
      power: { substations: [], voltageProfile: [], totalConsumption: 1.2, totalRegeneration: 0.3 },
      signaling: {
        controlCommands: [{
          trainId: 'TRAIN_01', tractionLevel: 0.5, brakeLevel: 0,
          emergencyBrake: false, runningPhase: 'traction',
        }],
        emergencyBrakes: [],
        maProfile: [{
          trainId: 'TRAIN_01', maEndChainage: 1500, safetyDistance: 300,
        }],
        speedLimits: [{
          trainId: 'TRAIN_01', permanentLimit: 80, atpLimit: 76,
        }],
        timetableDeviation: [{
          trainId: 'TRAIN_01', stationId: 'ST_A',
          delayArrival: 2.5, nominalDwell: 30, adjustedDwell: 32.5,
        }],
      },
      track: { occupancy: [], switchStates: [] },
      events: [],
    };
    const snap = parseServerSnapshot(raw);
    expect(snap.signaling.ma_profiles[0]).toEqual({
      train_id: 'TRAIN_01',
      ma_end_chainage: 1500,
      safety_distance: 300,
    });
    expect(snap.signaling.speed_limits[0]?.atp_limit).toBe(76);
    expect(snap.signaling.timetable_deviations[0]?.delay_arrival).toBe(2.5);
  });
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd frontend && npm run test -- src/utils/apiAdapter.test.ts
```

Expected: FAIL — `ma_profiles` 为 `undefined`

- [ ] **Step 3: 更新 simulation.ts 类型**

在 `SignalCommand` 之后、`SignalState` 之前追加：

```typescript
/** ATP 移动授权包络（后端 maProfile） */
export interface MaProfileEntry {
  train_id: string;
  ma_end_chainage: number;
  safety_distance: number;
}

/** 区段限速与 ATP 限速（后端 speedLimits） */
export interface SpeedLimitEntry {
  train_id: string;
  permanent_limit: number;
  atp_limit: number;
}

/** ATS 时刻表偏差（后端 timetableDeviation） */
export interface TimetableDeviationEntry {
  train_id: string;
  station_id: string;
  delay_arrival: number;
  nominal_dwell: number;
  adjusted_dwell: number;
}
```

更新 `SignalState`：

```typescript
export interface SignalState {
  commands: SignalCommand[];
  emergency_brake: EmergencyBrakeCommand[];
  train_intervals: number[];
  ma_profiles: MaProfileEntry[];
  speed_limits: SpeedLimitEntry[];
  timetable_deviations: TimetableDeviationEntry[];
}
```

更新 `ApiSimulationSnapshot.signaling`：

```typescript
  signaling: {
    controlCommands?: ApiControlCommand[];
    emergencyBrakes: unknown[];
    maProfile?: Array<{
      trainId: string;
      maEndChainage: number;
      safetyDistance: number;
    }>;
    speedLimits?: Array<{
      trainId: string;
      permanentLimit: number;
      atpLimit: number;
    }>;
    timetableDeviation?: Array<{
      trainId: string;
      stationId: string;
      delayArrival: number;
      nominalDwell: number;
      adjustedDwell: number;
    }>;
  };
```

同步修复所有 `SignalState` 字面量默认值（`SimulationContext.tsx`、`frameToSnapshot.ts`、`chartHistory.test.ts` 等），追加空数组：

```typescript
ma_profiles: [],
speed_limits: [],
timetable_deviations: [],
```

- [ ] **Step 4: 实现 apiAdapter.ts 映射**

在 `mapControlCommand` 之后追加三个 mapper，并在 `parseServerSnapshot` 的 `signaling` 块写入：

```typescript
function mapMaProfile(entry: NonNullable<ApiSimulationSnapshot['signaling']['maProfile']>[0]) {
  return {
    train_id: entry.trainId,
    ma_end_chainage: entry.maEndChainage,
    safety_distance: entry.safetyDistance,
  };
}

function mapSpeedLimit(entry: NonNullable<ApiSimulationSnapshot['signaling']['speedLimits']>[0]) {
  return {
    train_id: entry.trainId,
    permanent_limit: entry.permanentLimit,
    atp_limit: entry.atpLimit,
  };
}

function mapTimetableDeviation(
  entry: NonNullable<ApiSimulationSnapshot['signaling']['timetableDeviation']>[0],
) {
  return {
    train_id: entry.trainId,
    station_id: entry.stationId,
    delay_arrival: entry.delayArrival,
    nominal_dwell: entry.nominalDwell,
    adjusted_dwell: entry.adjustedDwell,
  };
}

// parseServerSnapshot 内 signaling:
    signaling: {
      commands: controlCommands.map(mapControlCommand),
      emergency_brake: [],
      train_intervals: [],
      ma_profiles: (raw.signaling?.maProfile ?? []).map(mapMaProfile),
      speed_limits: (raw.signaling?.speedLimits ?? []).map(mapSpeedLimit),
      timetable_deviations: (raw.signaling?.timetableDeviation ?? []).map(mapTimetableDeviation),
    },
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd frontend && npm run test -- src/utils/apiAdapter.test.ts && npx tsc -b
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts \
        frontend/src/context/SimulationContext.tsx frontend/src/utils/frameToSnapshot.ts \
        frontend/src/utils/chartHistory.test.ts
git commit -m "feat(frontend): 映射后端 signaling 扩展字段"
```

---

### Task 3: signalSelectors 纯函数 + 单元测试

**Files:**
- Create: `frontend/src/utils/signalSelectors.ts`
- Create: `frontend/src/utils/signalSelectors.test.ts`

**Interfaces:**
- Produces: `resolveMaEnvelope(position, totalLength, maProfile?, fallbackLength?) → { envelopeStart, envelopeEnd, safetyDistance }`
- Produces: `resolveAtpSpeedLimit(speedLimits, trainId, fallbackLimit) → number`
- Produces: `resolveLatestDeviation(deviations, trainId) → TimetableDeviationEntry | null`
- Consumes (later): `MAChart`, `SpeedEnvelope`, `TimetableChart`, `SignalStatusBar`

- [ ] **Step 1: 写失败测试**

Create `frontend/src/utils/signalSelectors.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import {
  resolveMaEnvelope,
  resolveAtpSpeedLimit,
  resolveLatestDeviation,
} from './signalSelectors';
import type { MaProfileEntry, SpeedLimitEntry, TimetableDeviationEntry } from '../types/simulation';

describe('resolveMaEnvelope', () => {
  it('uses backend ma_end_chainage when provided', () => {
    const ma: MaProfileEntry = {
      train_id: 'T1', ma_end_chainage: 1500, safety_distance: 300,
    };
    const result = resolveMaEnvelope(800, 3200, ma, 300);
    expect(result.envelopeEnd).toBe(1500);
    expect(result.safetyDistance).toBe(300);
  });

  it('falls back to position + fixed length', () => {
    const result = resolveMaEnvelope(800, 3200, undefined, 300);
    expect(result.envelopeEnd).toBe(1100);
  });

  it('clamps envelope end to total length', () => {
    const result = resolveMaEnvelope(3000, 3200, undefined, 300);
    expect(result.envelopeEnd).toBe(3200);
  });
});

describe('resolveAtpSpeedLimit', () => {
  it('returns atp_limit for matching train', () => {
    const limits: SpeedLimitEntry[] = [
      { train_id: 'T1', permanent_limit: 80, atp_limit: 76 },
    ];
    expect(resolveAtpSpeedLimit(limits, 'T1', 80)).toBe(76);
  });

  it('returns fallback when no match', () => {
    expect(resolveAtpSpeedLimit([], 'T1', 80)).toBe(80);
  });
});

describe('resolveLatestDeviation', () => {
  it('returns last deviation entry for train', () => {
    const devs: TimetableDeviationEntry[] = [
      { train_id: 'T1', station_id: 'ST_A', delay_arrival: 1, nominal_dwell: 30, adjusted_dwell: 31 },
      { train_id: 'T1', station_id: 'ST_B', delay_arrival: 3, nominal_dwell: 30, adjusted_dwell: 33 },
    ];
    expect(resolveLatestDeviation(devs, 'T1')?.station_id).toBe('ST_B');
  });

  it('returns null when empty', () => {
    expect(resolveLatestDeviation([], 'T1')).toBeNull();
  });
});
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd frontend && npm run test -- src/utils/signalSelectors.test.ts
```

Expected: FAIL — module not found

- [ ] **Step 3: 实现 signalSelectors.ts**

Create `frontend/src/utils/signalSelectors.ts`:

```typescript
import type { MaProfileEntry, SpeedLimitEntry, TimetableDeviationEntry } from '../types/simulation';

export interface MaEnvelope {
  envelopeStart: number;
  envelopeEnd: number;
  safetyDistance: number;
}

export function resolveMaEnvelope(
  position: number,
  totalLength: number,
  maProfile?: MaProfileEntry,
  fallbackLength = 300,
): MaEnvelope {
  const safetyDistance = maProfile?.safety_distance ?? fallbackLength;
  const envelopeEnd = maProfile
    ? Math.min(maProfile.ma_end_chainage, totalLength)
    : Math.min(position + fallbackLength, totalLength);
  return {
    envelopeStart: position,
    envelopeEnd,
    safetyDistance,
  };
}

export function resolveAtpSpeedLimit(
  speedLimits: SpeedLimitEntry[],
  trainId: string,
  fallbackLimit: number,
): number {
  const entry = speedLimits.find((s) => s.train_id === trainId);
  return entry?.atp_limit ?? fallbackLimit;
}

export function resolveLatestDeviation(
  deviations: TimetableDeviationEntry[],
  trainId: string,
): TimetableDeviationEntry | null {
  const matched = deviations.filter((d) => d.train_id === trainId);
  if (matched.length === 0) return null;
  return matched[matched.length - 1];
}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd frontend && npm run test -- src/utils/signalSelectors.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/signalSelectors.ts frontend/src/utils/signalSelectors.test.ts
git commit -m "feat(frontend): 新增 signalSelectors 解析工具"
```

---

### Task 4: MAChart 消费后端 maProfile

**Files:**
- Modify: `frontend/src/components/views/signal/MAChart.tsx:22-24,86-106`

**Interfaces:**
- Consumes: `resolveMaEnvelope()` from Task 3
- Consumes: `signaling.ma_profiles[0]` from Task 2

- [ ] **Step 1: 替换固定包络计算**

在 `MAChart.tsx` 顶部追加 import：

```typescript
import { resolveMaEnvelope } from '../../../utils/signalSelectors';
```

替换 `envelopeEnd` / `envelopeWidth` 计算：

```typescript
  const maEntry = signaling.ma_profiles.find((m) => m.train_id === train?.id)
    ?? signaling.ma_profiles[0];
  const { envelopeEnd, safetyDistance } = resolveMaEnvelope(
    position,
    totalLength,
    maEntry,
    MA_ENVELOPE_LENGTH,
  );
  const envelopeWidth = Math.max(envelopeEnd - position, 0);
```

更新 footer 与 labelRow 文案，将硬编码 `MA_ENVELOPE_LENGTH` 改为 `safetyDistance`：

```typescript
            安全包络 {safetyDistance.toFixed(0)} m
// footer:
        安全包络: {safetyDistance.toFixed(0)} m
        {maEntry ? ' · 后端 MA' : ' · 固定包络'}
```

- [ ] **Step 2: 类型检查**

```bash
cd frontend && npx tsc -b && npm run lint
```

Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/views/signal/MAChart.tsx
git commit -m "feat(frontend): MAChart 对接后端 maProfile"
```

---

### Task 5: SpeedEnvelope 新增 ATP 限速线

**Files:**
- Modify: `frontend/src/components/views/signal/SpeedEnvelope.tsx`

**Interfaces:**
- Consumes: `resolveAtpSpeedLimit()` from Task 3
- Consumes: `signaling.speed_limits`, `trains[0].id`

- [ ] **Step 1: 追加 ATP 限速系列**

在 `SpeedEnvelope.tsx` 顶部追加：

```typescript
import { resolveAtpSpeedLimit } from '../../../utils/signalSelectors';
```

在组件内追加：

```typescript
  const train = useSimulationState().trains[0];
  const atpLimitKmh = resolveAtpSpeedLimit(
    useSimulationState().signaling.speed_limits,
    train?.id ?? 'TRAIN_01',
    segments.length > 0 ? segments[0].speed_limit : 80,
  );

  const atpLimitData = segments.length > 0
    ? segments.flatMap((seg) => [
        [seg.start_chainage, Math.min(seg.speed_limit, atpLimitKmh)],
        [seg.end_chainage, Math.min(seg.speed_limit, atpLimitKmh)],
      ] as [number, number][])
    : ([[0, atpLimitKmh], [maxPos, atpLimitKmh]] as [number, number][]);
```

更新 legend 与 series（在「目标速度」与「实际速度」之间插入）：

```typescript
    legend: {
      data: ['区段限速', 'ATP 限速', '目标速度', '实际速度'],
      // ...
    },
    series: [
      // ... 区段限速不变 ...
      {
        name: 'ATP 限速',
        type: 'line',
        data: atpLimitData,
        lineStyle: { color: '#eb2f96', type: 'dotted' as const, width: 1 },
        itemStyle: { color: '#eb2f96' },
        showSymbol: false,
      },
      // ... 目标速度、实际速度不变 ...
    ],
```

> 注：完整 ATP 紧急制动曲线仍留迭代三；本步仅展示后端已推送的 `atpLimit` 水平线。

- [ ] **Step 2: 类型检查**

```bash
cd frontend && npx tsc -b
```

Expected: 无错误

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/views/signal/SpeedEnvelope.tsx
git commit -m "feat(frontend): 速度包络增加 ATP 限速线"
```

---

### Task 6: TimetableChart ATS 偏差标注 + SignalStatusBar

**Files:**
- Create: `frontend/src/components/views/signal/SignalStatusBar.tsx`
- Modify: `frontend/src/components/views/signal/TimetableChart.tsx`
- Modify: `frontend/src/pages/SignalView.tsx`

**Interfaces:**
- Consumes: `resolveLatestDeviation()`, `resolveSignalPhase()`, `getSignalPhaseLabel()`
- Produces: `SignalStatusBar` 展示相位、紧急制动、ATS 偏差

- [ ] **Step 1: 创建 SignalStatusBar.tsx**

```tsx
/**
 * SignalStatusBar — 信号视图底部状态条
 * 展示运行相位、紧急制动、ATS 时刻偏差
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { getSignalPhaseLabel, resolveSignalPhase } from '../../../utils/format';
import { resolveLatestDeviation } from '../../../utils/signalSelectors';

export default function SignalStatusBar() {
  const { trains, signaling } = useSimulationState();
  const train = trains[0];
  const cmd = signaling.commands[0];
  const phase = resolveSignalPhase(
    cmd?.running_phase,
    train?.mode,
    cmd?.traction_level,
    cmd?.brake_level,
  );
  const deviation = resolveLatestDeviation(
    signaling.timetable_deviations,
    train?.id ?? 'TRAIN_01',
  );
  const ebActive = cmd?.emergency_brake === true;

  return (
    <div style={styles.bar}>
      <span>相位: <strong>{getSignalPhaseLabel(phase)}</strong></span>
      <span>牵引: {(cmd?.traction_level ?? 0).toFixed(2)}</span>
      <span>制动: {(cmd?.brake_level ?? 0).toFixed(2)}</span>
      <span style={{ color: ebActive ? '#ff4d4f' : '#52c41a' }}>
        {ebActive ? '⚠ 紧急制动' : '● 正常'}
      </span>
      {deviation && (
        <span>
          ATS 偏差: {deviation.delay_arrival >= 0 ? '+' : ''}
          {deviation.delay_arrival.toFixed(1)} s
          {' · '}站停 {deviation.adjusted_dwell.toFixed(0)} s
        </span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 16,
    fontSize: 12,
    color: 'var(--text-secondary)',
    padding: '6px 12px',
    borderTop: '1px solid var(--border-color)',
    background: 'var(--panel-bg)',
  },
};
```

- [ ] **Step 2: TimetableChart 追加 subtitle**

在 `TimetableChart.tsx` 中读取 deviation 并在 `panel-title` 下方追加一行（当存在偏差时）：

```typescript
import { resolveLatestDeviation } from '../../../utils/signalSelectors';

// 组件内：
  const { chartHistory, lineLayout, trains, signaling } = useSimulationState();
  const deviation = resolveLatestDeviation(
    signaling.timetable_deviations,
    trains[0]?.id ?? 'TRAIN_01',
  );

// JSX panel-title 下方：
      {deviation && (
        <div style={{ fontSize: 11, color: '#fa8c16', padding: '0 8px 4px' }}>
          最近到站偏差 {deviation.delay_arrival >= 0 ? '+' : ''}
          {deviation.delay_arrival.toFixed(1)} s（{deviation.station_id}）
        </div>
      )}
```

- [ ] **Step 3: SignalView 挂载 SignalStatusBar**

在 `SignalView.tsx` 的 `styles.container` 内最底部追加（不改变左右列布局）：

```tsx
import SignalStatusBar from '../components/views/signal/SignalStatusBar';

// return 内 container 末尾：
      <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0 }}>
        <SignalStatusBar />
      </div>
```

同时将 `styles.container` 增加 `position: 'relative'` 与 `paddingBottom: 36` 避免遮挡图表。

- [ ] **Step 4: 验证**

```bash
cd frontend && npx tsc -b && npm run lint
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/signal/SignalStatusBar.tsx \
        frontend/src/components/views/signal/TimetableChart.tsx \
        frontend/src/pages/SignalView.tsx
git commit -m "feat(frontend): 信号状态条与 ATS 偏差展示"
```

---

### Task 7: Mock 模式信号字段补齐

**Files:**
- Modify: `frontend/src/utils/frameToSnapshot.ts`
- Modify: `frontend/src/mock/generateMockTrajectory.ts`（扩展帧字段）
- Modify: `frontend/src/types/simulation.ts` — `MockReplayFrame` 可选字段
- Test: `frontend/src/utils/frameToSnapshot.test.ts`（若无则创建）

**Interfaces:**
- Produces: Mock 模式下 `signaling.commands[0].running_phase` 非空
- Produces: Mock 模式下 `distance_to_station` / `target_station_id` 合理推导

- [ ] **Step 1: 扩展 MockReplayFrame**

在 `MockReplayFrame` 追加可选字段：

```typescript
export interface MockReplayFrame {
  // ... 现有字段 ...
  running_phase?: string;
  distance_to_station?: number;
  target_station_id?: string;
  traction_level?: number;
  brake_level?: number;
}
```

- [ ] **Step 2: 写失败测试**

Create `frontend/src/utils/frameToSnapshot.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { frameToSnapshot } from './frameToSnapshot';

describe('frameToSnapshot', () => {
  it('maps mock signaling fields when present on frame', () => {
    const snap = frameToSnapshot({
      t: 10,
      position: 500,
      speed: 60,
      acceleration: 0.5,
      mode: 'traction',
      mass: 254000,
      passenger_count: 900,
      pantograph_voltage: 1500,
      power_demand: 800,
      running_phase: 'traction',
      distance_to_station: 700,
      target_station_id: 'ST_B',
      traction_level: 0.6,
      brake_level: 0,
    });
    expect(snap.trains[0].distance_to_station).toBe(700);
    expect(snap.trains[0].target_station_id).toBe('ST_B');
    expect(snap.signaling.commands[0]?.running_phase).toBe('traction');
    expect(snap.signaling.commands[0]?.traction_level).toBe(0.6);
  });
});
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd frontend && npm run test -- src/utils/frameToSnapshot.test.ts
```

Expected: FAIL

- [ ] **Step 4: 更新 frameToSnapshot.ts**

```typescript
export function frameToSnapshot(
  frame: MockReplayFrame,
  speedMultiplier: SpeedMultiplier = 1,
): SimulationSnapshot {
  const runningPhase = frame.running_phase
    ?? (frame.mode === 'stopped' ? 'dwell'
      : frame.mode === 'braking' ? 'braking'
      : frame.mode === 'traction' ? 'traction'
      : 'coasting');

  return {
    // ... clock, power, track, events 不变 ...
    trains: [{
      id: 'TRAIN_01',
      position: frame.position,
      speed: frame.speed,
      acceleration: frame.acceleration,
      jerk: frame.jerk ?? 0,
      mode: frame.mode,
      mass: frame.mass,
      passenger_count: frame.passenger_count,
      door_status: 'closed',
      pantograph_voltage: frame.pantograph_voltage,
      power_demand: frame.power_demand,
      distance_to_station: frame.distance_to_station ?? 0,
      target_station_id: frame.target_station_id ?? '',
      fault_alarm: null,
    }],
    signaling: {
      commands: [{
        train_id: 'TRAIN_01',
        traction_level: frame.traction_level ?? 0,
        brake_level: frame.brake_level ?? 0,
        emergency_brake: false,
        running_phase: runningPhase,
      }],
      emergency_brake: [],
      train_intervals: [],
      ma_profiles: [],
      speed_limits: [],
      timetable_deviations: [],
    },
  };
}
```

在 `generateMockTrajectory.ts` 每帧输出时追加 `running_phase`（按 mode 映射）及简化的 `distance_to_station`（到下一站的剩余距离，可用现有站间逻辑估算）。

- [ ] **Step 5: 运行测试确认通过**

```bash
cd frontend && npm run test -- src/utils/frameToSnapshot.test.ts src/mock/generateMockTrajectory.test.ts
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/utils/frameToSnapshot.ts \
        frontend/src/utils/frameToSnapshot.test.ts frontend/src/mock/generateMockTrajectory.ts
git commit -m "feat(frontend): Mock 模式补齐 signaling 字段"
```

---

### Task 8: SignalParams Live 模式限制说明

**Files:**
- Modify: `frontend/src/components/param/SignalParams.tsx`
- Modify: `frontend/src/components/param/ParamPanel.tsx:9-11`（注释修正为迭代二）

**Interfaces:**
- Consumes: `connection` 或环境变量判断 Live/Mock
- 后端现状：`simulation_manager.py` 仅运行时接受 `targetSpeedRatio` 更新

- [ ] **Step 1: SignalParams 区分可写参数**

在 `SignalParams.tsx` 中为 `dwell_time` / `departure_interval` 在 Live 模式（`VITE_USE_MOCK !== 'true'` 且 WS 已连接）下设置 `disabled`，并在 fieldset 底部追加提示：

```tsx
import { useSimulationState } from '../../context/SimulationContext';

// 组件内：
  const { connection } = useSimulationState();
  const isLive = import.meta.env.VITE_USE_MOCK !== 'true';
  const liveLocked = isLive && connection === 'connected';

// ParamStepper disabled 逻辑：
            disabled={disabled || (liveLocked && key !== 'target_speed_ratio')}

// fieldset 末尾：
      {liveLocked && (
        <p style={{ fontSize: 11, color: 'var(--text-secondary)', margin: '6px 0 0' }}>
          Live 模式仅「目标速度比」可实时修改；站停时间与发车间隔需重启仿真后生效（待后端支持）。
        </p>
      )}
```

- [ ] **Step 2: 修正 ParamPanel 注释**

将 `UI-PARAM-03/04/06` 注释中的「迭代三」改为「迭代二（部分）」。

- [ ] **Step 3: 验证**

```bash
cd frontend && npx tsc -b && npm run lint
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/param/SignalParams.tsx frontend/src/components/param/ParamPanel.tsx
git commit -m "fix(frontend): SignalParams Live 模式可写范围"
```

---

### Task 9: 全量验收与分支收尾

**Files:**
- Verify: 全部 signal 相关文件

- [ ] **Step 1: 全量测试**

```bash
cd frontend && npm run test && npx tsc -b && npm run lint
```

Expected: 全部 PASS

- [ ] **Step 2: Live 后端联调**

```bash
# 终端 1
cd backend && uv run uvicorn sim_engine.app:app --reload --host 0.0.0.0 --port 8000

# 终端 2 — .env: VITE_USE_MOCK=false
cd frontend && npm run dev
```

验收清单（对照迭代二场景 4、7、8）：

| 检查项 | 预期 |
|--------|------|
| 切换五视图无卡顿，时钟同步 | 通过 |
| MA 图：列车移动，包络终点随 `maProfile` 变化 | 通过 |
| MA 图：footer 显示「后端 MA」或「固定包络」 | 通过 |
| 速度包络：四条线（限速/ATP/目标/实际） | 通过 |
| 运行图：轨迹平滑累积 | 通过 |
| SignalStatusBar：相位、牵引/制动级位更新 | 通过 |
| 到站后 ATS 偏差显示（若后端推送） | 通过 |
| Mock 模式：MA 图不再显示距目标站 `--` | 通过 |

- [ ] **Step 3: 更新设计文档验收勾选**

在 `docs/superpowers/specs/2026-07-10-frontend-signal-view-design.md` 的「验收标准」章节，将已通过项改为 `[x]`。

- [ ] **Step 4: Commit 文档**

```bash
git add docs/superpowers/specs/2026-07-10-frontend-signal-view-design.md
git commit -m "docs(frontend): 信号视图验收项更新"
```

- [ ] **Step 5: 调用 finishing-a-development-branch**

全部 Task 完成后，调用 `finishing-a-development-branch` skill 合并回 `dev`。

---

## Spec 覆盖自检

| Spec / 需求 | 对应 Task | 状态 |
|-------------|-----------|------|
| UI-SIG-01 MA 示意图 | Task 1 + Task 4 | Phase 1 完成 + maProfile 对接 |
| UI-SIG-02 速度包络线 | Task 1 + Task 5 | + ATP 限速线 |
| UI-SIG-03 运行图 | Task 1 + Task 6 | + ATS 偏差标注 |
| chartHistory.positionTime | Phase 1 已完成 | — |
| runningPhase 降级策略 | Phase 1 + Task 7 | Mock 补齐 |
| 后端 maProfile / speedLimits / timetableDeviation | Task 2 + Task 3 | 新增 |
| UI-PARAM-04 信号参数（Live 限制） | Task 8 | 部分（后端仅 targetSpeedRatio） |
| 验收场景 4 多视图联动 | Task 9 | 手动 |
| 验收场景 7 ATO 验证 | Task 5 + Task 9 | 速度包络展示 ATO 跟踪效果 |
| 验收场景 8 ATP 包络 | Task 4 + Task 9 | maProfile 对接 |

**不在本计划范围（留待其他负责人 / 后续迭代）：**
- UI-SIG-04~06（迭代三/四）
- ATP 紧急制动曲线完整绘制（迭代三）
- 多车追踪间隔 MA（迭代三）
- 后端 `GET/PUT /config/signal` API（后端负责）
- UI-PARAM-06 参数预设（控制面板负责人）

## 与后端协调项（记录，非本计划实现）

| 项 | 现状 | 建议 |
|----|------|------|
| `dwellTime` / `departureInterval` 运行时更新 | 后端只写 `targetSpeedRatio` | 后端迭代二补 PUT 支持，或前端保持 Task 8 限制说明 |
| `events` 数组 | 始终 `[]` | 事件日志后端完成后前端在 StatusBar 展示 |
| WebSocket schema 与需求附录 B 命名差异 | 实际用 `maProfile` 等 camelCase | 前端 adapter 已对齐实际推送格式 |

---

## 执行后合并

全部 Task 完成后，调用 `finishing-a-development-branch` skill 合并回 `dev`。
