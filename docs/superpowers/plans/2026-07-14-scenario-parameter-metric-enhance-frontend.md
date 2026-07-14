# 方案参数-指标矩阵增强 — 前端实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有方案对比功能基础上，补齐前端未暴露的参数控件、扩展指标体系、新增参数对比 Tab、支持评估完成通知。

**Architecture:** 增量修改现有组件，不重构架构。核心改动链：类型定义 → 参数步进工具 → 参数表单控件 → 对比组件增强 → 页面 Tab 切换 → WebSocket 通知处理。

**Tech Stack:** React 19 + TypeScript 6.0 + ECharts 6.1 + echarts-for-react

## Global Constraints

- 向后兼容：旧方案 JSON 缺少的新字段用 `??` 回退默认值
- 参数命名：前端内部使用 snake_case，API 通信时由 apiAdapter 转 camelCase
- 迭代一范围约束：非本设计文档的功能标 `// TODO: 迭代N实现`
- 所有可调参数步进量为基准值的 10%

---

### Task 1: 类型定义扩展

**Files:**
- Modify: `frontend/src/types/simulation.ts`

**Interfaces:**
- Produces: `ScenarioResult` 新增 7 字段；`SimulationParams.signal` 新增 3 字段；`ServerMessage` 新增 `evaluation_complete` 类型；新增 `ScenarioParams` 导出类型

**说明:** 这是所有后续任务的基础，必须先完成。

- [ ] **Step 1: ScenarioResult 新增 6 个指标字段 + 1 个辅助字段**

在 `ScenarioResult` 接口中新增（约 L620-631）：

```typescript
export interface ScenarioResult {
  // 已有字段
  totalTime: number;
  totalDistance: number;
  avgSpeed: number;
  maxSpeed: number;
  tractionEnergy: number;
  regenEnergy: number;
  netEnergy: number;
  minVoltage: number;
  peakPower: number;
  // 新增字段
  maxJerk: number;            // 最大冲击率 (m/s³)
  avgJerk: number;            // 平均冲击率 (m/s³)
  maxAccel: number;           // 最大加速度 (m/s²)
  regenRate: number;          // 再生利用率 (%)
  ebCount: number;            // 紧急制动次数
  totalDelay: number;         // 总晚点时间 (s)
  evaluationDuration: number; // 评估窗口时长 (s)
}
```

- [ ] **Step 2: SimulationParams.signal 新增 3 个字段**

在 `SimulationParams` 的 `signal` 中新增（约 L284-289）：

```typescript
signal: {
    dwell_time?: number;
    departure_interval?: number;
    target_speed_ratio?: number;
    // 新增
    safety_distance?: number;  // ATP安全距离 (m)
    comfort_decel?: number;    // 舒适减速度 (m/s²)
    max_jerk?: number;         // 冲击率上限 (m/s³)
};
```

- [ ] **Step 3: ServerMessage 新增 evaluation_complete 类型**

在 `ServerMessage` 联合类型中新增（约 L557-562）：

```typescript
export type ServerMessage =
  | { type: 'simulation_snapshot'; timestamp: number; data: ApiSimulationSnapshot }
  | { type: 'init_state'; config: Record<string, unknown>; state?: { runState: RunState; simulationTime: number } }
  | { type: 'simulation_status'; data: { runState: RunState; simulationTime: number; reason?: string } }
  | { type: 'simulation_complete'; data: Record<string, unknown> }
  | { type: 'evaluation_complete'; data: { evaluationTime: number; elapsed: number; message?: string } }
  | { type: 'heartbeat'; serverTime?: string };
```

- [ ] **Step 4: 在 Scenario 的 params 类型附近新增 ScenarioParams 类型（可选导出，方便 CompareParams 使用）**

在 `Scenario` 接口之后，确认 `Scenario['params']` 类型已可直接引用。无需额外定义——`CompareParams` 直接使用 `Scenario['params']`。

- [ ] **Step 5: 运行 TypeScript 类型检查**

```bash
cd frontend && npx tsc -b --noEmit
```

预期：类型检查通过（可能有其他预存错误，但不应该有本次修改引入的新错误）。

---

### Task 2: 参数步进工具扩展

**Files:**
- Modify: `frontend/src/utils/paramStep.ts`

**Interfaces:**
- Consumes: 新增的参数字段名
- Produces: `VEHICLE_PARAM_STEP_KEYS` 新增 3 项、`SIGNAL_PARAM_STEP_KEYS` 新增 3 项、对应默认值

- [ ] **Step 1: VEHICLE_PARAM_STEP_KEYS 新增 3 个车辆参数键**

在数组末尾追加（约 L8）：

```typescript
export const VEHICLE_PARAM_STEP_KEYS = [
  'empty_mass',
  'passenger_capacity',
  'max_speed',
  'max_traction_force',
  'max_brake_force',
  'davis_A',
  'davis_B',
  'davis_C_front_area',
  // 新增
  'davis_C_drag_coeff',
  'curve_resist_coeff',
  'tunnel_resist_factor',
] as const;
```

- [ ] **Step 2: SIGNAL_PARAM_STEP_KEYS 新增 3 个信号参数键**

在数组末尾追加（约 L31）：

```typescript
export const SIGNAL_PARAM_STEP_KEYS = [
  'dwell_time',
  'departure_interval',
  'target_speed_ratio',
  // 新增
  'safety_distance',
  'comfort_decel',
  'max_jerk',
] as const;
```

- [ ] **Step 3: DEFAULT_SIGNAL_PARAMS 新增 3 个默认值**

```typescript
export const DEFAULT_SIGNAL_PARAMS = {
  dwell_time: 30,
  departure_interval: 120,
  target_speed_ratio: 0.8,
  // 新增
  safety_distance: 300,
  comfort_decel: 0.8,
  max_jerk: 0.75,
} as const;
```

- [ ] **Step 4: 运行现有测试确保不破坏**

```bash
cd frontend && npx vitest run src/utils/paramStep.test.ts
```

---

### Task 3: VehicleParams 新增 3 个控件

**Files:**
- Modify: `frontend/src/components/param/VehicleParams.tsx`

**Interfaces:**
- Consumes: `VEHICLE_PARAM_STEP_KEYS`（含新增 3 项）、`VehicleParamStepKey`（自动扩展）

- [ ] **Step 1: PARAM_LABELS 新增 3 个标签**

在 `PARAM_LABELS` 对象中追加（约 L23-32）：

```typescript
const PARAM_LABELS: Record<VehicleParamStepKey, string> = {
  empty_mass: '空车质量 (kg)',
  passenger_capacity: '载客量',
  max_speed: '最大速度 (km/h)',
  max_traction_force: '最大牵引力 (N)',
  max_brake_force: '最大制动力 (N)',
  davis_A: 'Davis A',
  davis_B: 'Davis B',
  davis_C_front_area: '迎风面积 (m²)',
  // 新增
  davis_C_drag_coeff: '空气阻力系数 Cd',
  curve_resist_coeff: '弯道阻力系数',
  tunnel_resist_factor: '隧道阻力系数',
};
```

由于 `VEHICLE_PARAM_STEP_KEYS` 已自动包含新增键，且 `ParamStepper` 通过 `.map()` 遍历渲染，无需修改 JSX 部分。

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 4: SignalParams 新增 3 个控件

**Files:**
- Modify: `frontend/src/components/param/SignalParams.tsx`

**Interfaces:**
- Consumes: `SIGNAL_PARAM_STEP_KEYS`（含新增 3 项）、`SignalParamStepKey`（自动扩展）

- [ ] **Step 1: PARAM_LABELS 新增 3 个标签**

在 `PARAM_LABELS` 对象中追加（约 L18-22）：

```typescript
const PARAM_LABELS: Record<SignalParamStepKey, string> = {
  dwell_time: '站停时间 (s)',
  departure_interval: '发车间隔 (s)',
  target_speed_ratio: '目标速度比',
  // 新增
  safety_distance: 'ATP安全距离 (m)',
  comfort_decel: '舒适减速度 (m/s²)',
  max_jerk: '冲击率上限 (m/s³)',
};
```

由于 `SIGNAL_PARAM_STEP_KEYS` 已自动包含新增键，JSX 无需修改。

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 5: apiAdapter 补齐 signal/power 参数映射

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts`

**Interfaces:**
- Consumes: 新增的 signal 参数字段
- Produces: `toApiParamUpdate` 正确发送新增字段、新增 power 参数发送逻辑

- [ ] **Step 1: toApiParamUpdate 中 signal 映射新增 3 个字段**

修改 `toApiParamUpdate` 函数中 signal 部分（约 L185-194），追加：

```typescript
if (params.signal) {
    result.signal = {
      ...(params.signal.dwell_time !== undefined && { dwellTime: params.signal.dwell_time }),
      ...(params.signal.target_speed_ratio !== undefined && {
        targetSpeedRatio: params.signal.target_speed_ratio,
      }),
      ...(params.signal.departure_interval !== undefined && {
        departureInterval: params.signal.departure_interval,
      }),
      // 新增
      ...(params.signal.safety_distance !== undefined && {
        safetyDistance: params.signal.safety_distance,
      }),
      ...(params.signal.comfort_decel !== undefined && {
        comfortDecel: params.signal.comfort_decel,
      }),
      ...(params.signal.max_jerk !== undefined && {
        maxJerk: params.signal.max_jerk,
      }),
    };
  }
```

- [ ] **Step 2: toApiParamUpdate 新增 power 参数映射**

在 signal 块之后、track 块之前，新增 power 块（当前代码缺少 power 映射）：

```typescript
if (params.power) {
    result.power = {
      ...(params.power.pantograph_voltage !== undefined && {
        pantographVoltage: params.power.pantograph_voltage,
      }),
      ...(params.power.substation_capacity !== undefined && {
        substationCapacity: params.power.substation_capacity,
      }),
    };
  }
```

- [ ] **Step 3: parseApiParams 中 signal 反向映射新增 3 个字段**

在 `parseApiParams` 的 signal 部分（约 L254-265），追加：

```typescript
const signalRaw = raw.signal as Record<string, unknown> | undefined;
  if (signalRaw) {
    result.signal = {
      ...(signalRaw.dwellTime !== undefined && { dwell_time: signalRaw.dwellTime as number }),
      ...(signalRaw.departureInterval !== undefined && {
        departure_interval: signalRaw.departureInterval as number,
      }),
      ...(signalRaw.targetSpeedRatio !== undefined && {
        target_speed_ratio: signalRaw.targetSpeedRatio as number,
      }),
      // 新增
      ...(signalRaw.safetyDistance !== undefined && {
        safety_distance: signalRaw.safetyDistance as number,
      }),
      ...(signalRaw.comfortDecel !== undefined && {
        comfort_decel: signalRaw.comfortDecel as number,
      }),
      ...(signalRaw.maxJerk !== undefined && {
        max_jerk: signalRaw.maxJerk as number,
      }),
    };
  }
```

- [ ] **Step 4: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 6: PowerParams 补齐更新逻辑

**Files:**
- Modify: `frontend/src/components/param/PowerParams.tsx`

**说明:** 当前 PowerParams 组件的 `updateParams` 已能通过 `toApiParamUpdate` 正确发送（Task 5 补齐了 power 映射），组件本身无需修改。但需确认 `DEFAULT_POWER_PARAMS` 包含在初始状态中（已在 `SimulationContext.tsx` 中确认）。

`PowerParams.tsx` 逻辑已完整——`handleChange` 调用 `updateParams({ power: { ...params.power, [key]: value } })`，参数会通过 `toApiParamUpdate` 正确映射为 `pantographVoltage` / `substationCapacity` 发送给后端。

**此任务无需代码修改，仅需验证。**

- [ ] **Step 1: 验证 power 参数更新链路**

确认 `SimulationContext.tsx` `initialState.params.power` 不为空对象（当前为空 `{}`），需要改为：

```typescript
power: { ...DEFAULT_POWER_PARAMS },
```

检查 `SimulationContext.tsx` L55，当前为 `power: {}`，需修改为 `power: { ...DEFAULT_POWER_PARAMS }`。

---

### Task 7: CompareTable 增强 — 维度分组 + 新指标行

**Files:**
- Modify: `frontend/src/components/scenario/CompareTable.tsx`

**Interfaces:**
- Consumes: `ScenarioResult`（含新增字段）

- [ ] **Step 1: 重构 METRICS 为按维度分组的二维数组**

替换现有的 `METRICS` 数组（约 L20-29）：

```typescript
interface DimensionGroup {
  name: string;
  icon: string;
  metrics: MetricDef[];
}

const DIMENSION_GROUPS: DimensionGroup[] = [
  {
    name: '效率', icon: '⚡',
    metrics: [
      { key: 'totalTime', label: '总耗时', unit: 's', lowerIsBetter: true, decimals: 1 },
      { key: 'totalDistance', label: '总里程', unit: 'm', lowerIsBetter: false, decimals: 1 },
      { key: 'avgSpeed', label: '平均速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
      { key: 'maxSpeed', label: '最高速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    name: '能耗', icon: '🔋',
    metrics: [
      { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenEnergy', label: '再生电量', unit: 'kWh', lowerIsBetter: false, decimals: 1 },
      { key: 'netEnergy', label: '净能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenRate', label: '再生利用率', unit: '%', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    name: '舒适度', icon: '🛋️',
    metrics: [
      { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 2 },
      { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 2 },
      { key: 'maxAccel', label: '最大加速度', unit: 'm/s²', lowerIsBetter: true, decimals: 2 },
    ],
  },
  {
    name: '安全', icon: '🛡️',
    metrics: [
      { key: 'minVoltage', label: '最低网压', unit: 'V', lowerIsBetter: false, decimals: 0 },
      { key: 'peakPower', label: '峰值功率', unit: 'kW', lowerIsBetter: true, decimals: 1 },
      { key: 'ebCount', label: '紧急制动', unit: '次', lowerIsBetter: true, decimals: 0 },
    ],
  },
  {
    name: '准点', icon: '⏱️',
    metrics: [
      { key: 'totalDelay', label: '总晚点', unit: 's', lowerIsBetter: true, decimals: 1 },
    ],
  },
];
```

- [ ] **Step 2: 渲染改为按维度分组**

修改 tbody 渲染逻辑，每个维度先渲染分组标题行，再渲染该维度的指标行：

```tsx
<tbody>
  {DIMENSION_GROUPS.map((group) => (
    <React.Fragment key={group.name}>
      {/* 维度分组标题行 */}
      <tr>
        <td colSpan={scenarios.length + 1} style={styles.dimHeader}>
          {group.icon} {group.name}
        </td>
      </tr>
      {/* 该维度的指标行 */}
      {group.metrics.map((metric) => (
        <tr key={metric.key}>
          <td style={styles.tdLabel}>{metric.label}</td>
          {scenarios.map((s) => {
            const raw = (s.result as unknown as Record<string, number>)[metric.key];
            const value = typeof raw === 'number' ? raw : 0;
            const cellStyle = getCellStyle(metric, value);
            return (
              <td key={s.id} style={{ ...styles.td, ...cellStyle }}>
                {value.toFixed(metric.decimals)} {metric.unit}
              </td>
            );
          })}
        </tr>
      ))}
    </React.Fragment>
  ))}
  {/* 评估窗口辅助信息行 */}
  {scenarios.length > 0 && (
    <tr>
      <td style={styles.tdLabel}>评估窗口</td>
      {scenarios.map((s) => {
        const duration = (s.result as unknown as Record<string, number>).evaluationDuration;
        return (
          <td key={s.id} style={{ ...styles.td, color: 'var(--text-secondary)', fontWeight: 400 }}>
            {typeof duration === 'number' && duration > 0 ? `${duration}s` : '-'}
          </td>
        );
      })}
    </tr>
  )}
</tbody>
```

- [ ] **Step 3: 新增 dimHeader 样式**

在 styles 对象中追加：

```typescript
dimHeader: {
  textAlign: 'left' as const,
  padding: '8px 10px',
  borderBottom: '2px solid var(--border-color)',
  color: 'var(--text-highlight)',
  fontWeight: 700,
  fontSize: '12px',
  backgroundColor: 'rgba(42, 42, 74, 0.2)',
},
```

- [ ] **Step 4: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 8: CompareChartBar 增强 — 维度切换

**Files:**
- Modify: `frontend/src/components/scenario/CompareChartBar.tsx`

**Interfaces:**
- Consumes: `ScenarioResult`（含新增字段）

- [ ] **Step 1: 重构为维度选择 + 动态图表**

完整替换组件内容：

```typescript
import { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareChartBarProps {
  scenarios: ScenarioDetailResponse[];
}

interface BarMetric {
  key: string;
  label: string;
  unit: string;
}

const DIMENSION_METRICS: Record<string, BarMetric[]> = {
  '效率': [
    { key: 'totalTime', label: '总耗时', unit: 's' },
    { key: 'totalDistance', label: '总里程', unit: 'm' },
    { key: 'avgSpeed', label: '平均速度', unit: 'km/h' },
    { key: 'maxSpeed', label: '最高速度', unit: 'km/h' },
  ],
  '能耗': [
    { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh' },
    { key: 'regenEnergy', label: '再生电量', unit: 'kWh' },
    { key: 'netEnergy', label: '净能耗', unit: 'kWh' },
    { key: 'regenRate', label: '再生利用率', unit: '%' },
  ],
  '舒适度': [
    { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³' },
    { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³' },
    { key: 'maxAccel', label: '最大加速度', unit: 'm/s²' },
  ],
  '安全': [
    { key: 'minVoltage', label: '最低网压', unit: 'V' },
    { key: 'peakPower', label: '峰值功率', unit: 'kW' },
    { key: 'ebCount', label: '紧急制动', unit: '次' },
  ],
  '准点': [
    { key: 'totalDelay', label: '总晚点', unit: 's' },
  ],
};

const DIMENSION_NAMES = Object.keys(DIMENSION_METRICS);

export default function CompareChartBar({ scenarios }: CompareChartBarProps) {
  const [selectedDim, setSelectedDim] = useState('效率');

  if (scenarios.length < 2) {
    return (
      <div className="panel" style={{ height: '100%' }}>
        <div className="panel-title">📈 指标对比柱状图</div>
        <div style={{ textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' }}>
          请勾选至少 2 个方案进行对比
        </div>
      </div>
    );
  }

  const metrics = DIMENSION_METRICS[selectedDim];
  const names = scenarios.map((s) => s.name);
  const colors = ['#1890ff', '#ff4d4f', '#52c41a', '#fadb14', '#722ed1', '#eb2f96'];

  // 动态确定是否需要双 Y 轴（不同量纲的指标用不同轴）
  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    legend: {
      data: metrics.map((m) => m.label),
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 60, right: 60, top: 30, bottom: 50 },
    xAxis: {
      type: 'category' as const,
      data: names,
      axisLabel: {
        color: '#a0a0a0', fontSize: 11,
        rotate: names.length > 3 ? 15 : 0,
      },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: metrics.map((m) => `${m.label}(${m.unit})`).join(' / '),
        nameTextStyle: { color: '#a0a0a0', fontSize: 10 },
        axisLabel: { color: '#a0a0a0', fontSize: 10 },
        axisLine: { lineStyle: { color: '#2a2a4a' } },
        splitLine: { lineStyle: { color: 'rgba(42, 42, 74, 0.4)' } },
      },
    ],
    series: metrics.map((m, i) => ({
      name: m.label,
      type: 'bar' as const,
      data: scenarios.map((s) => {
        const v = (s.result as unknown as Record<string, number>)[m.key];
        return typeof v === 'number' ? Number(v.toFixed(1)) : 0;
      }),
      itemStyle: { color: colors[i % colors.length] },
      barMaxWidth: 40,
    })),
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <div className="panel-title" style={{ margin: 0 }}>📈 指标对比柱状图</div>
        <select
          value={selectedDim}
          onChange={(e) => setSelectedDim(e.target.value)}
          style={{
            fontSize: '12px',
            padding: '2px 8px',
            backgroundColor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
          }}
        >
          {DIMENSION_NAMES.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
```

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 9: CompareParams 新增 — 参数对比组件

**Files:**
- Create: `frontend/src/components/scenario/CompareParams.tsx`

**Interfaces:**
- Consumes: `ScenarioDetailResponse`（含 params 字段）
- Produces: `CompareParams` 组件

- [ ] **Step 1: 创建组件文件**

创建 `frontend/src/components/scenario/CompareParams.tsx`：

```typescript
/**
 * CompareParams — 方案参数对比
 * - 0 个方案：提示勾选
 * - 1 个方案：展示完整参数列表
 * - 2+ 个方案：差异对比模式（相同折叠、不同高亮）
 */
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareParamsProps {
  scenarios: ScenarioDetailResponse[];
}

/** 参数分组定义 */
interface ParamGroup {
  name: string;
  icon: string;
  keys: string[];
  labels: Record<string, string>;
  units: Record<string, string>;
  decimals: Record<string, number>;
}

const PARAM_GROUPS: ParamGroup[] = [
  {
    name: '车辆参数', icon: '🚇',
    keys: [
      'empty_mass', 'passenger_capacity', 'max_speed',
      'max_traction_force', 'max_brake_force',
      'davis_A', 'davis_B', 'davis_C_front_area',
      'davis_C_drag_coeff', 'curve_resist_coeff', 'tunnel_resist_factor',
    ],
    labels: {
      empty_mass: '空车质量', passenger_capacity: '载客量', max_speed: '最大速度',
      max_traction_force: '最大牵引力', max_brake_force: '最大制动力',
      davis_A: 'Davis A', davis_B: 'Davis B', davis_C_front_area: '迎风面积',
      davis_C_drag_coeff: '空气阻力系数 Cd', curve_resist_coeff: '弯道阻力系数',
      tunnel_resist_factor: '隧道阻力系数',
    },
    units: {
      empty_mass: 'kg', passenger_capacity: '人', max_speed: 'km/h',
      max_traction_force: 'N', max_brake_force: 'N',
      davis_A: '', davis_B: '', davis_C_front_area: 'm²',
      davis_C_drag_coeff: '', curve_resist_coeff: '', tunnel_resist_factor: '',
    },
    decimals: {},
  },
  {
    name: '信号参数', icon: '🚦',
    keys: ['dwell_time', 'departure_interval', 'target_speed_ratio', 'safety_distance', 'comfort_decel', 'max_jerk'],
    labels: {
      dwell_time: '站停时间', departure_interval: '发车间隔', target_speed_ratio: '目标速度比',
      safety_distance: 'ATP安全距离', comfort_decel: '舒适减速度', max_jerk: '冲击率上限',
    },
    units: {
      dwell_time: 's', departure_interval: 's', target_speed_ratio: '',
      safety_distance: 'm', comfort_decel: 'm/s²', max_jerk: 'm/s³',
    },
    decimals: { target_speed_ratio: 2, comfort_decel: 1, max_jerk: 2 },
  },
  {
    name: '供电参数', icon: '⚡',
    keys: ['pantograph_voltage', 'substation_capacity'],
    labels: { pantograph_voltage: '网压', substation_capacity: '变电所容量' },
    units: { pantograph_voltage: 'V', substation_capacity: 'kW' },
    decimals: {},
  },
];

/** simulation 参数展示 */
const SIM_PARAM_KEYS = ['totalTime', 'evaluationTime', 'coastingMinSpeed', 'stationStopTolerance'] as const;
const SIM_PARAM_LABELS: Record<string, string> = {
  totalTime: '仿真总时长', evaluationTime: '评估窗口',
  coastingMinSpeed: '惰行最低速度', stationStopTolerance: '站台停车容忍度',
};
const SIM_PARAM_UNITS: Record<string, string> = {
  totalTime: 's', evaluationTime: 's', coastingMinSpeed: 'km/h', stationStopTolerance: 'm',
};

function formatParamValue(value: unknown, unit: string, decimals?: number): string {
  if (typeof value === 'number') {
    const d = decimals ?? (Number.isInteger(value) ? 0 : 1);
    const formatted = value.toFixed(d);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  return String(value ?? '-');
}

/** 判断一个参数在所有方案中是否有差异 */
function hasDiff(scenarios: ScenarioDetailResponse[], group: string, key: string): boolean {
  const values = scenarios.map((s) => {
    const v = (s.params as Record<string, Record<string, unknown>>)[group]?.[key];
    return JSON.stringify(v);
  });
  return new Set(values).size > 1;
}

export default function CompareParams({ scenarios }: CompareParamsProps) {
  if (scenarios.length === 0) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">🔧 参数对比</div>
        <div style={styles.empty}>请勾选方案查看参数</div>
      </div>
    );
  }

  const isDiffMode = scenarios.length >= 2;

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">
        🔧 参数对比
        {isDiffMode && <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginLeft: '8px' }}>（差异模式）</span>}
      </div>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>参数</th>
              {scenarios.map((s) => (
                <th key={s.id} style={styles.th}>{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* 车辆参数组 */}
            {PARAM_GROUPS.map((group) => (
              <React.Fragment key={group.name}>
                <tr>
                  <td colSpan={scenarios.length + 1} style={styles.groupHeader}>
                    {group.icon} {group.name}
                  </td>
                </tr>
                {group.keys.map((key) => {
                  const diff = isDiffMode && hasDiff(scenarios, mapGroupToParamKey(group.name), key);
                  if (isDiffMode && !diff) return null; // 差异模式下隐藏相同参数
                  return (
                    <tr key={key} style={diff ? { backgroundColor: 'rgba(250, 173, 20, 0.08)' } : undefined}>
                      <td style={styles.tdLabel}>
                        {group.labels[key] ?? key}
                        {diff && <span style={{ marginLeft: '4px', fontSize: '10px' }}>🔶</span>}
                      </td>
                      {scenarios.map((s) => {
                        const val = (s.params as Record<string, Record<string, unknown>>)[mapGroupToParamKey(group.name)]?.[key];
                        return (
                          <td key={s.id} style={diff ? { ...styles.td, color: 'var(--color-warning)' } : styles.td}>
                            {formatParamValue(val, group.units[key] ?? '', group.decimals[key])}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </React.Fragment>
            ))}
            {/* simulation 参数 */}
            <tr>
              <td colSpan={scenarios.length + 1} style={styles.groupHeader}>
                ⚙️ 仿真参数
              </td>
            </tr>
            {SIM_PARAM_KEYS.map((key) => {
              const diff = isDiffMode && hasDiff(scenarios, 'simulation', key);
              if (isDiffMode && !diff) return null;
              return (
                <tr key={key} style={diff ? { backgroundColor: 'rgba(250, 173, 20, 0.08)' } : undefined}>
                  <td style={styles.tdLabel}>
                    {SIM_PARAM_LABELS[key] ?? key}
                    {diff && <span style={{ marginLeft: '4px', fontSize: '10px' }}>🔶</span>}
                  </td>
                  {scenarios.map((s) => {
                    const val = (s.params as Record<string, Record<string, unknown>>).simulation?.[key];
                    return (
                      <td key={s.id} style={diff ? { ...styles.td, color: 'var(--color-warning)' } : styles.td}>
                        {formatParamValue(val, SIM_PARAM_UNITS[key] ?? '', 0)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {/* 相同参数折叠提示 */}
            {isDiffMode && (
              <tr>
                <td colSpan={scenarios.length + 1} style={styles.foldedHint}>
                  📎 相同参数已自动折叠
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** 将分组名映射到 params 对象的键 */
function mapGroupToParamKey(groupName: string): string {
  const map: Record<string, string> = {
    '车辆参数': 'vehicle',
    '信号参数': 'signal',
    '供电参数': 'power',
  };
  return map[groupName] ?? groupName;
}

const styles: Record<string, React.CSSProperties> = {
  panel: { marginBottom: '12px' },
  tableWrapper: { overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: {
    textAlign: 'center', padding: '8px 10px',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-highlight)', fontWeight: 600, whiteSpace: 'nowrap',
  },
  td: {
    textAlign: 'center', padding: '6px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: '12px',
  },
  tdLabel: {
    textAlign: 'left', padding: '6px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-secondary)', fontWeight: 500,
  },
  groupHeader: {
    textAlign: 'left', padding: '8px 10px',
    borderBottom: '2px solid var(--border-color)',
    color: 'var(--text-highlight)', fontWeight: 700, fontSize: '12px',
    backgroundColor: 'rgba(42, 42, 74, 0.2)',
  },
  empty: { textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' },
  foldedHint: {
    textAlign: 'center', padding: '8px',
    color: 'var(--text-secondary)', fontSize: '11px', fontStyle: 'italic',
  },
};
```

- [ ] **Step 2: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 10: ScenarioComparePage Tab 切换

**Files:**
- Modify: `frontend/src/pages/ScenarioComparePage.tsx`

**Interfaces:**
- Consumes: `CompareParams`（new）、`CompareTable`、`CompareChartBar`

- [ ] **Step 1: 添加 Tab 状态与导入**

在文件顶部新增导入（L11-12 附近）：

```typescript
import { useState, useEffect, useCallback } from 'react';
import { getScenarios, getScenario } from '../services/api';
import ScenarioSavePanel from '../components/scenario/ScenarioSavePanel';
import ScenarioListPanel from '../components/scenario/ScenarioListPanel';
import CompareTable from '../components/scenario/CompareTable';
import CompareChartBar from '../components/scenario/CompareChartBar';
import CompareParams from '../components/scenario/CompareParams';  // 新增
import type { ScenarioSummary, ScenarioDetailResponse } from '../types/simulation';
```

在组件内部新增 Tab 状态（约 L15 之后）：

```typescript
const [activeTab, setActiveTab] = useState<'metrics' | 'params'>('metrics');
```

- [ ] **Step 2: 修改详情加载逻辑 — 支持 1 个方案**

修改 `checkedIds` effect（约 L40-65），将 `>= 2` 改为 `>= 1`：

```typescript
useEffect(() => {
    if (checkedIds.size < 1) {  // 原为 < 2
      setDetails([]);
      return;
    }
    // ... 其余不变
}, [checkedIds]);
```

- [ ] **Step 3: 右侧面板改为 Tab 结构**

替换右侧面板 JSX（约 L99-113）：

```tsx
<div style={styles.rightPanel}>
  {/* Tab 切换 */}
  <div style={styles.tabBar}>
    <button
      className={`btn ${activeTab === 'metrics' ? 'btn-primary' : ''}`}
      onClick={() => setActiveTab('metrics')}
      style={styles.tabBtn}
    >
      📊 指标对比
    </button>
    <button
      className={`btn ${activeTab === 'params' ? 'btn-primary' : ''}`}
      onClick={() => setActiveTab('params')}
      style={styles.tabBtn}
    >
      🔧 参数对比
    </button>
  </div>

  {detailsLoading ? (
    <div className="panel" style={styles.loadingPanel}>
      <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px 0' }}>
        加载方案详情中...
      </div>
    </div>
  ) : activeTab === 'metrics' ? (
    <>
      <CompareTable scenarios={details} />
      <div style={styles.chartArea}>
        <CompareChartBar scenarios={details} />
      </div>
    </>
  ) : (
    <CompareParams scenarios={details} />
  )}
</div>
```

- [ ] **Step 4: 添加 Tab 相关样式**

在 styles 对象中追加：

```typescript
tabBar: {
  display: 'flex',
  gap: '8px',
  marginBottom: '12px',
},
tabBtn: {
  fontSize: '13px',
  padding: '6px 16px',
},
```

- [ ] **Step 5: 添加 React 导入（Fragment 需要）**

确认文件顶部已有 `import { useState, useEffect, useCallback } from 'react';`（已有）。

- [ ] **Step 6: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 11: WebSocket evaluation_complete 通知处理

**Files:**
- Modify: `frontend/src/hooks/useWebSocket.ts`
- Modify: `frontend/src/context/SimulationContext.tsx`

**说明:** 当后端 WebSocket 推送 `evaluation_complete` 时，前端需要在全局显示通知条。

- [ ] **Step 1: AppState 新增 evaluationComplete 状态字段**

在 `frontend/src/types/simulation.ts` 的 `AppState` 接口中新增（L414-459）：

```typescript
/** 评估完成通知（null = 未触发或已关闭） */
evaluationComplete: { evaluationTime: number; elapsed: number } | null;
```

- [ ] **Step 2: initialState 新增初始值**

在 `SimulationContext.tsx` 的 `initialState` 对象中新增（约 L77 之后）：

```typescript
evaluationComplete: null,
```

- [ ] **Step 3: 新增 SET_EVALUATION_COMPLETE action**

在 `SimulationAction` 类型中新增（约 L99）：

```typescript
| { type: 'SET_EVALUATION_COMPLETE'; payload: { evaluationTime: number; elapsed: number } | null }
```

- [ ] **Step 4: Reducer 新增处理分支**

在 `simulationReducer` 的 switch 中新增（约 L196 之后）：

```typescript
case 'SET_EVALUATION_COMPLETE':
  return { ...state, evaluationComplete: action.payload };
```

同时，在 `RESET_STATE` 中确保自动清除（`return { ...initialState }` 已覆盖）。

- [ ] **Step 5: useWebSocket 处理 evaluation_complete 消息**

在 `useWebSocket.ts` 的 `ws.onmessage` switch 中，在 `default` 之前新增（约 L60）：

```typescript
case 'evaluation_complete':
  dispatch({
    type: 'SET_EVALUATION_COMPLETE',
    payload: {
      evaluationTime: message.data.evaluationTime,
      elapsed: message.data.elapsed,
    },
  });
  break;
```

- [ ] **Step 6: ScenarioComparePage 显示通知条**

在 `ScenarioComparePage.tsx` 组件中，从 context 读取 `evaluationComplete` 状态，在页面顶部渲染通知条：

```typescript
// 在组件内新增
const { evaluationComplete } = useSimulationState();  // 新增导入
const dispatch = useSimulationDispatch();  // 新增导入

// 在 return 的 container 顶部添加通知条
{evaluationComplete && (
  <div style={styles.evalNotice}>
    <span>🟢 指标评估已完成 ({evaluationComplete.evaluationTime}s)</span>
    <span style={{ marginLeft: '12px' }}>您可以保存方案进行对比</span>
    <button
      className="btn btn-primary"
      style={{ marginLeft: '12px', fontSize: '12px', padding: '2px 12px' }}
      onClick={() => {
        // 跳转到方案对比页面的保存面板（通过滚动或焦点）
        const savePanel = document.querySelector('.panel-title');
        savePanel?.scrollIntoView({ behavior: 'smooth' });
      }}
    >
      💾 保存方案
    </button>
    <button
      className="btn"
      style={{ marginLeft: '8px', fontSize: '12px', padding: '2px 8px' }}
      onClick={() => dispatch({ type: 'SET_EVALUATION_COMPLETE', payload: null })}
    >
      ✕
    </button>
  </div>
)}
```

- [ ] **Step 7: 添加 evalNotice 样式**

在 `ScenarioComparePage.tsx` 的 styles 对象中追加：

```typescript
evalNotice: {
  display: 'flex',
  alignItems: 'center',
  padding: '8px 16px',
  marginBottom: '12px',
  backgroundColor: 'rgba(82, 196, 26, 0.12)',
  border: '1px solid var(--color-success)',
  borderRadius: 'var(--border-radius)',
  fontSize: '13px',
  color: 'var(--color-success)',
},
```

- [ ] **Step 8: 添加 auto-dismiss 逻辑（30s 自动消失）**

在组件内新增 useEffect：

```typescript
useEffect(() => {
  if (!evaluationComplete) return;
  const timer = setTimeout(() => {
    dispatch({ type: 'SET_EVALUATION_COMPLETE', payload: null });
  }, 30000);
  return () => clearTimeout(timer);
}, [evaluationComplete, dispatch]);
```

- [ ] **Step 9: 验证编译**

```bash
cd frontend && npx tsc -b --noEmit
```

---

### Task 12: 集成验证与收尾

**Files:**
- 无新修改，仅验证

- [ ] **Step 1: 完整 TypeScript 编译检查**

```bash
cd frontend && npx tsc -b --noEmit
```

- [ ] **Step 2: 运行 lint 检查**

```bash
cd frontend && npm run lint
```

- [ ] **Step 3: 运行现有测试**

```bash
cd frontend && npx vitest run
```

- [ ] **Step 4: 启动开发服务器进行手动验证**

```bash
cd frontend && npm run dev
```

手动验证清单：
1. 参数面板：VehicleParams 显示 3 个新控件、SignalParams 显示 3 个新控件
2. 参数面板：修改新参数值，确认步进正常（10% 基准值）
3. 方案对比页：勾选 0/1/2+ 方案，确认三种状态正确
4. 方案对比页：指标对比 Tab 显示 5 个维度分组 + 评估窗口行
5. 方案对比页：柱状图维度下拉切换正常
6. 方案对比页：参数对比 Tab 中差异模式正确高亮/折叠
7. Mock 模式下 evaluation_complete 通知（需要后端支持，可手动 console 测试）

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat(frontend): 方案参数-指标矩阵增强 — 新增参数控件、指标体系、参数对比Tab、评估通知"
```

---

## 修改文件总览

| 文件 | 操作 | 任务 |
|:-----|:-----|:-----|
| `frontend/src/types/simulation.ts` | 修改 | Task 1 + Task 11.1 |
| `frontend/src/utils/paramStep.ts` | 修改 | Task 2 |
| `frontend/src/components/param/VehicleParams.tsx` | 修改 | Task 3 |
| `frontend/src/components/param/SignalParams.tsx` | 修改 | Task 4 |
| `frontend/src/utils/apiAdapter.ts` | 修改 | Task 5 |
| `frontend/src/context/SimulationContext.tsx` | 修改 | Task 6 + Task 11.2-11.4 |
| `frontend/src/components/scenario/CompareTable.tsx` | 修改 | Task 7 |
| `frontend/src/components/scenario/CompareChartBar.tsx` | 修改 | Task 8 |
| `frontend/src/components/scenario/CompareParams.tsx` | **新增** | Task 9 |
| `frontend/src/pages/ScenarioComparePage.tsx` | 修改 | Task 10 + Task 11.6-11.8 |
| `frontend/src/hooks/useWebSocket.ts` | 修改 | Task 11.5 |
