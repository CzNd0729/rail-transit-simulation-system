# 方案参数-指标矩阵增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有方案对比功能基础上，新增评估窗口机制、6个对比指标、6个参数控件、参数对比 Tab、评估完成通知

**Architecture:** 后端增量修改（SimulationParams 新增字段、SimulationManager 新增追踪变量、scenarios.py 扩展指标计算），前端增量修改（ParamPanel 新增控件、CompareTable 分组展示、新增 CompareParams 组件）

**Tech Stack:** Python 3.10+ / FastAPI / React 19 + TypeScript + ECharts

---

## 文件结构

### 后端修改

| 文件 | 操作 | 职责 |
|------|------|------|
| `sim_engine/core/config.py` | 修改 | `SimulationParams` 新增 `evaluation_time` 字段 |
| `sim_engine/config/simulation.yaml` | 修改 | 新增 `evaluation_time: 600` 配置项 |
| `sim_engine/services/simulation_manager.py` | 修改 | 新增追踪变量、`_update_tracking` 扩展、`get_params`/`update_params` 补全 signal/power 参数、`update_config` 补全 evaluationTime |
| `sim_engine/api/scenarios.py` | 修改 | `save_scenario` 按评估窗口截取指标、计算6个新指标 |

### 前端修改

| 文件 | 操作 | 职责 |
|------|------|------|
| `frontend/src/types/simulation.ts` | 修改 | `ScenarioResult` 新增6个字段、`SimulationParams` 补全参数类型 |
| `frontend/src/utils/paramStep.ts` | 修改 | 新增3个车辆参数和3个信号参数的步进定义 |
| `frontend/src/components/param/VehicleParams.tsx` | 修改 | 新增 Cd/弯道阻力/隧道阻力 3个控件 |
| `frontend/src/components/param/SignalParams.tsx` | 修改 | 新增 ATP安全距离/舒适减速度/冲击率 3个控件 |
| `frontend/src/components/param/PowerParams.tsx` | 修改 | 补齐 `davisCDragCoeff`/`curveResistCoeff`/`tunnelResistFactor` 的提取 |
| `frontend/src/components/scenario/CompareTable.tsx` | 修改 | 按5个维度分组展示、新增6个指标行、评估窗口信息行 |
| `frontend/src/components/scenario/CompareChartBar.tsx` | 修改 | 支持维度下拉切换 |
| `frontend/src/components/scenario/CompareParams.tsx` | **新增** | 参数对比表格组件 |
| `frontend/src/pages/ScenarioComparePage.tsx` | 修改 | 右侧 Tab 切换（指标对比/参数对比） |

---

## 任务分解

### 任务 1: 后端 — evaluation_time 配置字段

**文件：**
- 修改：`sim_engine/core/config.py`
- 修改：`sim_engine/config/simulation.yaml`

**接口：**
- 消费：`SimulationParams` 数据类已有 `total_time` 等字段
- 产出：`SimulationParams.evaluation_time: float` 字段

- [ ] **Step 1: 修改数据类**

在 `sim_engine/core/config.py` 的 `SimulationParams` 中新增字段：

```python
@dataclass
class SimulationParams:
    time_step: float = 0.1
    total_time: float = 600.0
    evaluation_time: float = 600.0  # 新增：评估窗口时长 (s)
    # ... 其余字段不变
```

- [ ] **Step 2: 修改 YAML 配置**

在 `sim_engine/config/simulation.yaml` 中新增：

```yaml
simulation:
  time_step: 0.1
  total_time: 6000
  evaluation_time: 600      # 新增
  # ... 其余不变
```

- [ ] **Step 3: 加载逻辑无需修改**

`load_simulation_params` 中已有 `float(data.get("evaluation_time", 600.0))` 的通用模式，新字段会自动被 YAML 中的值覆盖。确认 `evaluation_time` 在 `data.get()` 中会被正确读取，无需额外修改。

- [ ] **Step 4: 提交**

```bash
git add sim_engine/core/config.py sim_engine/config/simulation.yaml
git commit -m "feat(core): 新增 evaluation_time 评估窗口配置"
```

---

### 任务 2: 后端 — SimulationManager 新增追踪变量

**文件：**
- 修改：`sim_engine/services/simulation_manager.py`

**接口：**
- 消费：`SimulationManager._update_tracking` 方法
- 产出：`_max_jerk`、`_avg_jerk`、`_max_accel`、`_eb_count`、`_total_delay` 追踪变量、`_evaluation_snapshot` 缓存

- [ ] **Step 1: 新增追踪变量和 evaluation_snapshot 缓存**

在 `SimulationManager.__init__` 中新增：

```python
class SimulationManager:
    def __init__(self, ws_manager: WebSocketConnectionManager, external_mode: bool = False) -> None:
        # ... 已有代码 ...
        self._last_snapshot: dict | None = None
        self._last_summary: dict | None = None
        self._min_voltage: float = 1500.0
        self._peak_power: float = 0.0  # kW

        # 新增：舒适度追踪
        self._max_jerk: float = 0.0
        self._jerk_sum: float = 0.0
        self._jerk_count: int = 0
        self._max_accel: float = 0.0

        # 新增：紧急制动追踪（上升沿检测）
        self._eb_count: int = 0
        self._eb_prev_states: dict[str, bool] = {}

        # 新增：晚点追踪（增量累计）
        self._total_delay: float = 0.0
        self._prev_delays: dict[str, float] = {}

        # 新增：评估窗口缓存
        self._evaluation_snapshot: dict | None = None
```

- [ ] **Step 2: 重置追踪变量**

在 `_reset_tracking` 方法中补充：

```python
def _reset_tracking(self) -> None:
    self._last_snapshot = None
    self._last_summary = None
    self._min_voltage = 1500.0
    self._peak_power = 0.0
    # 新增重置
    self._max_jerk = 0.0
    self._jerk_sum = 0.0
    self._jerk_count = 0
    self._max_accel = 0.0
    self._eb_count = 0
    self._eb_prev_states.clear()
    self._total_delay = 0.0
    self._prev_delays.clear()
    self._evaluation_snapshot = None
```

- [ ] **Step 3: 扩展 `_update_tracking` 方法**

```python
def _update_tracking(self, snapshot: dict) -> None:
    """从单步 snapshot 更新追踪变量。"""
    self._last_snapshot = snapshot
    data = snapshot.get("data", {})
    power_data = data.get("power", {})

    # 原有：网压最低值
    vp = power_data.get("voltageProfile", [])
    for item in vp:
        v = item.get("voltage", 1500.0)
        if v < self._min_voltage:
            self._min_voltage = v

    # 原有：变电所峰值功率 (W → kW)
    subs = power_data.get("substations", [])
    for s in subs:
        p_kw = s.get("outputPower", 0) / 1000.0
        if p_kw > self._peak_power:
            self._peak_power = p_kw

    # 新增：舒适度追踪（极值 + 平均值分母）
    trains = data.get("trains", [])
    for t in trains:
        jerk = t.get("jerk", 0)
        if jerk > self._max_jerk:
            self._max_jerk = jerk
        self._jerk_sum += jerk
        self._jerk_count += 1
        accel = abs(t.get("acceleration", 0))
        if accel > self._max_accel:
            self._max_accel = accel

    # 新增：紧急制动上升沿计数
    cmds = data.get("signaling", {}).get("controlCommands", [])
    for cmd in cmds:
        tid = cmd.get("trainId", "")
        eb = cmd.get("emergencyBrake", False)
        prev_eb = self._eb_prev_states.get(tid, False)
        if eb and not prev_eb:
            self._eb_count += 1
        self._eb_prev_states[tid] = eb

    # 新增：晚点增量累计
    devs = data.get("signaling", {}).get("timetableDeviation", [])
    for d in devs:
        tid = d.get("trainId", "")
        sid = d.get("stationId", "")
        delay = d.get("delayArrival", 0)
        if delay > 0:
            key = f"{tid}_{sid}"
            prev_delay = self._prev_delays.get(key, 0.0)
            if delay > prev_delay:
                self._total_delay += delay - prev_delay
                self._prev_delays[key] = delay
```

- [ ] **Step 4: 在 `_run_loop` 中注入 evaluation_complete 广播**

在 `_run_loop` 中，snapshot 广播之后、终点判断之前，插入评估完成通知逻辑：

```python
async def _run_loop(self) -> None:
    orch = self.orchestrator
    while orch.run_state == RunState.RUNNING:
        snapshot = orch.step_once()
        if snapshot:
            self._update_tracking(snapshot)
            await self.ws_manager.broadcast(snapshot)
            await self.ws_manager.broadcast({
                "type": "simulation_status",
                "data": {
                    "runState": "running",
                    "simulationTime": orch.clock.elapsed,
                    "reason": "running",
                },
            })

            # 新增：评估完成通知（首次到达 evaluation_time 时触发一次）
            if (self._evaluation_snapshot is None
                and orch.clock.elapsed >= orch.sim_params.evaluation_time):
                self._evaluation_snapshot = {
                    "elapsed": orch.clock.elapsed,
                    "summary": orch.recorder.summary(),
                    "tracking": {
                        "minVoltage": self._min_voltage,
                        "peakPower": self._peak_power,
                        "maxJerk": self._max_jerk,
                        "avgJerk": round(
                            self._jerk_sum / max(self._jerk_count, 1), 4
                        ),
                        "maxAccel": self._max_accel,
                        "ebCount": self._eb_count,
                        "totalDelay": round(self._total_delay, 2),
                    },
                }
                await self.ws_manager.broadcast({
                    "type": "evaluation_complete",
                    "data": {
                        "evaluationTime": orch.sim_params.evaluation_time,
                        "elapsed": orch.clock.elapsed,
                    },
                })

        # ... 原有终点判断和 sleep 逻辑不变 ...
```

- [ ] **Step 5: 新增 `get_run_stats` 扩展（供方案保存使用）**

`get_run_stats` 方法已存在，扩展为包含新指标：

```python
def get_run_stats(self) -> dict:
    """返回本次仿真运行的聚合统计数据。"""
    return {
        "minVoltage": self._min_voltage,
        "peakPower": self._peak_power,
        "maxJerk": self._max_jerk,
        "avgJerk": round(
            self._jerk_sum / max(self._jerk_count, 1), 4
        ),
        "maxAccel": self._max_accel,
        "ebCount": self._eb_count,
        "totalDelay": round(self._total_delay, 2),
    }
```

- [ ] **Step 6: 提交**

```bash
git add sim_engine/services/simulation_manager.py
git commit -m "feat(sim): 新增舒适度/安全/准点追踪变量与评估完成通知"
```

---

### 任务 3: 后端 — 补全 get_params / update_params

**文件：**
- 修改：`sim_engine/services/simulation_manager.py`

**接口：**
- 消费：`SimulationParams` 的 `signal.atp.safety_distance`、`pid.comfort_decel`、`pid.max_jerk`、`power.substations`
- 产出：`get_params()` 返回值中 signal 部分新增3个字段、power 部分去掉硬编码

- [ ] **Step 1: 扩展 `get_params()` 的 signal 部分**

```python
def get_params(self) -> dict:
    orch = self.orchestrator
    vp = orch.vehicle.params
    chainage = self._current_chainage()
    seg = orch.track.segment_at(chainage)
    tp = orch.track.query_at(chainage)
    return {
        "vehicle": {
            # ... 已有不变 ...
        },
        "track": {
            # ... 已有不变 ...
        },
        "power": {
            # 去掉硬编码，从 orch.sim_params.power 读取
            "pantographVoltage": (
                orch.sim_params.power.substations[0].rated_voltage
                if orch.sim_params.power.substations
                else 1500
            ),
            "substationCapacity": (
                orch.sim_params.power.substations[0].rated_power
                if orch.sim_params.power.substations
                else 5000
            ),
        },
        "signal": {
            # 已有
            "dwellTime": (
                orch.sim_params.dwell_time_override
                if orch.sim_params.dwell_time_override is not None
                else 30
            ),
            "departureInterval": orch.sim_params.departure_interval,
            "targetSpeedRatio": orch.sim_params.target_speed_ratio,
            # 新增
            "safetyDistance": orch.sim_params.signal.atp.safety_distance,
            "comfortDecel": orch.sim_params.pid.comfort_decel,
            "maxJerk": orch.sim_params.pid.max_jerk,
        },
    }
```

- [ ] **Step 2: 扩展 `update_params()` 的 signal 更新逻辑**

在 `signal_updates` 处理块中新增：

```python
signal_updates = updates.get("signal", {})
# 已有 3 个
if "targetSpeedRatio" in signal_updates:
    orch.sim_params.target_speed_ratio = float(signal_updates["targetSpeedRatio"])
    updated.append("signal.targetSpeedRatio")
if "departureInterval" in signal_updates:
    orch.sim_params.departure_interval = float(signal_updates["departureInterval"])
    updated.append("signal.departureInterval")
if "dwellTime" in signal_updates:
    orch.sim_params.dwell_time_override = float(signal_updates["dwellTime"])
    updated.append("signal.dwellTime")
# 新增 3 个
if "safetyDistance" in signal_updates:
    orch.sim_params.signal.atp.safety_distance = float(signal_updates["safetyDistance"])
    updated.append("signal.safetyDistance")
if "comfortDecel" in signal_updates:
    orch.sim_params.pid.comfort_decel = float(signal_updates["comfortDecel"])
    updated.append("signal.comfortDecel")
if "maxJerk" in signal_updates:
    orch.sim_params.pid.max_jerk = float(signal_updates["maxJerk"])
    updated.append("signal.maxJerk")
```

- [ ] **Step 3: 扩展 `update_params()` 的 power 更新逻辑**

在 `track_updates` 处理块之后、`signal_updates` 之前，或单独新增：

```python
power_updates = updates.get("power", {})
subs = orch.sim_params.power.substations
if "pantographVoltage" in power_updates and subs:
    for sub in subs:
        sub.rated_voltage = float(power_updates["pantographVoltage"])
    updated.append("power.pantographVoltage")
if "substationCapacity" in power_updates and subs:
    for sub in subs:
        sub.rated_power = float(power_updates["substationCapacity"])
    updated.append("power.substationCapacity")
```

- [ ] **Step 4: 扩展 `update_config()` 的 field_map**

在 `update_config` 方法的 `field_map` 中补充：

```python
field_map = {
    "timeStep": "time_step",
    "totalTime": "total_time",
    "speedMultiplier": "speed_multiplier",
    "targetSpeedRatio": "target_speed_ratio",
    "stationStopTolerance": "station_stop_tolerance",
    "trainCount": "train_count",
    "bidirectional": "bidirectional",
    "departureInterval": "departure_interval",
    "evaluationTime": "evaluation_time",  # 新增
}
```

- [ ] **Step 5: 提交**

```bash
git add sim_engine/services/simulation_manager.py
git commit -m "feat(sim): 补全 get_params/update_params 的 signal/power 参数"
```

---

### 任务 4: 后端 — 扩展方案保存指标计算

**文件：**
- 修改：`sim_engine/api/scenarios.py`

**接口：**
- 消费：`SimulationManager._evaluation_snapshot`、`SimulationManager.get_run_stats()`、`DataRecorder.buffer`
- 产出：方案 JSON 的 `result` 字段新增6个指标 + `evaluationDuration`

- [ ] **Step 1: 确定评估时长和指标数据源**

在 `save_scenario` 函数中，收集完 `summary` 和 `snapshot` 后，确定评估时长：

```python
@router.post("/scenarios")
async def save_scenario(body: dict) -> dict:
    sim = _get_sim_manager()
    orch = sim.orchestrator

    # ... 已有校验逻辑 ...

    summary = sim._last_summary
    sn = sim.get_last_snapshot()
    stats = sim.get_run_stats()

    # 确定评估时长
    if sim._evaluation_snapshot is not None:
        # 有评估缓存：用缓存数据算指标
        eval_duration = sim._evaluation_snapshot["elapsed"]
        eval_summary = sim._evaluation_snapshot["summary"]
        eval_tracking = sim._evaluation_snapshot["tracking"]
    else:
        # 无缓存：用实际仿真数据
        eval_duration = summary.get("total_time", 0.0) if summary else 0.0
        eval_summary = summary
        eval_tracking = stats
```

- [ ] **Step 2: 计算新指标并组装 result**

```python
    # 提取已有的能耗数据
    power_data = sn.get("data", {}).get("power", {}) if sn else {}
    traction_energy = power_data.get("totalConsumption", 0.0)
    regen_energy = power_data.get("totalRegeneration", 0.0)
    net_energy = round(traction_energy - regen_energy, 4)

    # 计算再生利用率（除零保护）
    regen_rate = 0.0
    if traction_energy > 0:
        regen_rate = round((regen_energy / traction_energy) * 100, 2)

    # 提取舒适度/安全/准点指标
    max_jerk = eval_tracking.get("maxJerk", 0.0)
    avg_jerk = eval_tracking.get("avgJerk", 0.0)
    max_accel = eval_tracking.get("maxAccel", 0.0)
    eb_count = eval_tracking.get("ebCount", 0)
    total_delay = eval_tracking.get("totalDelay", 0.0)

    result = {
        # 已有
        "totalTime": round(eval_duration, 2),
        "totalDistance": round(eval_summary.get("max_position", 0.0), 2) if eval_summary else 0.0,
        "avgSpeed": round(eval_summary.get("avg_speed", 0.0), 2) if eval_summary else 0.0,
        "maxSpeed": round(eval_summary.get("max_speed", 0.0), 2) if eval_summary else 0.0,
        "tractionEnergy": round(traction_energy, 4),
        "regenEnergy": round(regen_energy, 4),
        "netEnergy": net_energy,
        "minVoltage": round(stats.get("minVoltage", 1500.0), 2),
        "peakPower": round(stats.get("peakPower", 0.0), 2),
        # 新增
        "maxJerk": round(max_jerk, 4),
        "avgJerk": round(avg_jerk, 4),
        "maxAccel": round(max_accel, 4),
        "regenRate": regen_rate,
        "ebCount": eb_count,
        "totalDelay": round(total_delay, 2),
        "evaluationDuration": round(eval_duration, 2),
    }
```

- [ ] **Step 3: 确保方案 params 包含新暴露的参数**

检查方案组装逻辑，确保 `params.signal` 包含新增的 `safetyDistance` / `comfortDecel` / `maxJerk`（`get_params()` 已返回）。当前 `params` 组装代码：

```python
scenario = {
    "id": scenario_id,
    "name": ...,
    "description": ...,
    "createdAt": ...,
    "params": {
        "vehicle": params.get("vehicle", {}),
        "signal": params.get("signal", {}),   # 现在会包含新增字段 ✅
        "power": params.get("power", {}),      # 现在会从配置读取 ✅
        "simulation": config_section,
    },
    "result": result,
}
```

无需修改，`get_params()` 已经在任务 3 中补全了。

- [ ] **Step 4: 提交**

```bash
git add sim_engine/api/scenarios.py
git commit -m "feat(api): 方案保存新增6个指标和评估窗口截取"
```

---

### 任务 5: 前端 — 类型定义扩展

**文件：**
- 修改：`frontend/src/types/simulation.ts`

- [ ] **Step 1: ScenarioResult 新增字段**

```typescript
/** 方案仿真结果指标 */
export interface ScenarioResult {
  // 已有
  totalTime: number;
  totalDistance: number;
  avgSpeed: number;
  maxSpeed: number;
  tractionEnergy: number;
  regenEnergy: number;
  netEnergy: number;
  minVoltage: number;
  peakPower: number;
  // 新增
  maxJerk: number;
  avgJerk: number;
  maxAccel: number;
  regenRate: number;
  ebCount: number;
  totalDelay: number;
  evaluationDuration: number;
}
```

- [ ] **Step 2: SimulationParams 的 signal 部分补全**

```typescript
/** 仿真参数（供参数面板编辑使用） */
export interface SimulationParams {
  vehicle: Partial<VehicleParams>;
  track: {
    segment_id?: string;
    gradient?: number;
    curvature?: number;
    speed_limit?: number;
  };
  power: {
    pantograph_voltage?: number;
    substation_capacity?: number;
  };
  signal: {
    dwell_time?: number;
    departure_interval?: number;
    target_speed_ratio?: number;
    // 新增
    safety_distance?: number;
    comfort_decel?: number;
    max_jerk?: number;
  };
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/types/simulation.ts
git commit -m "feat(types): ScenarioResult 和 SimulationParams 新增字段"
```

---

### 任务 6: 前端 — 参数步进定义扩展

**文件：**
- 修改：`frontend/src/utils/paramStep.ts`

- [ ] **Step 1: 新增车辆参数步进键**

```typescript
/** 支持步进调节的车辆数值参数字段 */
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

- [ ] **Step 2: 新增信号参数步进键**

```typescript
/** 信号参数步进字段 */
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

- [ ] **Step 3: 新增默认信号参数**

```typescript
export const DEFAULT_SIGNAL_PARAMS = {
  dwell_time: 30,
  departure_interval: 120,
  target_speed_ratio: 0.8,
  safety_distance: 300,         // 新增
  comfort_decel: 0.8,           // 新增
  max_jerk: 0.75,               // 新增
} as const;
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/utils/paramStep.ts
git commit -m "feat(utils): 参数步进定义新增车辆3项和信号3项"
```

---

### 任务 7: 前端 — 车辆参数新增3个控件

**文件：**
- 修改：`frontend/src/components/param/VehicleParams.tsx`

- [ ] **Step 1: 新增标签映射**

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

`VEHICLE_PARAM_STEP_KEYS` 已包含新增字段，`handleChange` 使用通用逻辑，因此表单会自动渲染新增的3个控件。无需修改 `handleChange` 逻辑。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/param/VehicleParams.tsx
git commit -m "feat(ui): 车辆参数表单新增Cd/弯道阻力/隧道阻力"
```

---

### 任务 8: 前端 — 信号参数新增3个控件

**文件：**
- 修改：`frontend/src/components/param/SignalParams.tsx`

- [ ] **Step 1: 新增标签映射**

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

与车辆参数一样，`SIGNAL_PARAM_STEP_KEYS` 已包含新增字段，表单会自动渲染。

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/param/SignalParams.tsx
git commit -m "feat(ui): 信号参数表单新增ATP安全距离/舒适减速度/冲击率"
```

---

### 任务 9: 前端 — 对比表格按分组展示

**文件：**
- 修改：`frontend/src/components/scenario/CompareTable.tsx`

- [ ] **Step 1: 重构指标定义为分组结构**

```typescript
interface MetricGroup {
  label: string;        // 分组标题，如 "⚡ 效率指标"
  metrics: MetricDef[];
}

interface MetricDef {
  key: string;
  label: string;
  unit: string;
  lowerIsBetter: boolean;
  decimals: number;
}

const METRIC_GROUPS: MetricGroup[] = [
  {
    label: '⚡ 效率指标',
    metrics: [
      { key: 'totalTime', label: '总耗时', unit: 's', lowerIsBetter: true, decimals: 1 },
      { key: 'totalDistance', label: '总里程', unit: 'm', lowerIsBetter: false, decimals: 1 },
      { key: 'avgSpeed', label: '平均速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
      { key: 'maxSpeed', label: '最高速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    label: '⚡ 能耗指标',
    metrics: [
      { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenEnergy', label: '再生电量', unit: 'kWh', lowerIsBetter: false, decimals: 1 },
      { key: 'netEnergy', label: '净能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenRate', label: '再生利用率', unit: '%', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    label: '😊 舒适度指标',
    metrics: [
      { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 3 },
      { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 3 },
      { key: 'maxAccel', label: '最大加速度', unit: 'm/s²', lowerIsBetter: true, decimals: 2 },
    ],
  },
  {
    label: '🛡️ 安全指标',
    metrics: [
      { key: 'minVoltage', label: '最低网压', unit: 'V', lowerIsBetter: false, decimals: 0 },
      { key: 'peakPower', label: '峰值功率', unit: 'kW', lowerIsBetter: true, decimals: 1 },
      { key: 'ebCount', label: '紧急制动次数', unit: '次', lowerIsBetter: true, decimals: 0 },
    ],
  },
  {
    label: '⏱️ 准点指标',
    metrics: [
      { key: 'totalDelay', label: '总晚点时间', unit: 's', lowerIsBetter: true, decimals: 1 },
    ],
  },
];
```

- [ ] **Step 2: 渲染逻辑改为分组遍历**

```tsx
// 替换原来的 METRICS 遍历
export default function CompareTable({ scenarios }: CompareTableProps) {
  // ... 校验逻辑不变 ...

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">📊 指标对比</div>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>指标</th>
              {scenarios.map((s) => (
                <th key={s.id} style={styles.th}>{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRIC_GROUPS.map((group) => (
              // 分组标题行
              <tr key={group.label}>
                <td
                  colSpan={scenarios.length + 1}
                  style={styles.groupHeader}
                >
                  {group.label}
                </td>
              </tr>
              // 指标行
              {group.metrics.map((metric) => {
                const raw = (s.result as unknown as Record<string, number>)[metric.key];
                const value = typeof raw === 'number' ? raw : 0;
                const cellStyle = getCellStyle(metric, value);
                return (
                  <tr key={metric.key}>
                    <td style={styles.tdLabel}>{metric.label}</td>
                    {scenarios.map((s) => (
                      <td key={s.id} style={{ ...styles.td, ...cellStyle }}>
                        {value.toFixed(metric.decimals)} {metric.unit}
                      </td>
                    ))}
                  </tr>
                );
              })}
            ))}
            {/* 评估窗口信息行 */}
            <tr>
              <td style={styles.tdLabel}>评估窗口</td>
              {scenarios.map((s) => {
                const dur = (s.result as unknown as Record<string, number>).evaluationDuration;
                const actual = (s.result as unknown as Record<string, number>).totalTime;
                const text = dur ? `${dur.toFixed(0)}s` : '-';
                return (
                  <td key={s.id} style={styles.td}>
                    {text}
                    {dur && actual && actual < dur ? ` (实际:${actual.toFixed(0)}s)` : ''}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
      {/* ... 图例不变 ... */}
    </div>
  );
}
```

注意：`getCellStyle` 函数的参数需要从 `MetricDef` 改为使用 `MetricDef` 类型，需确保 `getCellStyle` 的 `metric` 参数签名兼容。

- [ ] **Step 3: 新增 groupHeader 样式**

```typescript
const styles: Record<string, React.CSSProperties> = {
  // ... 已有样式 ...
  groupHeader: {
    textAlign: 'left',
    padding: '10px 10px 4px',
    color: 'var(--text-highlight)',
    fontWeight: 700,
    fontSize: '13px',
    borderBottom: '1px solid var(--border-color)',
    backgroundColor: 'rgba(42, 42, 74, 0.2)',
  },
};
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/scenario/CompareTable.tsx
git commit -m "feat(ui): 对比表格按5个维度分组展示指标"
```

---

### 任务 10: 前端 — 柱状图支持维度切换

**文件：**
- 修改：`frontend/src/components/scenario/CompareChartBar.tsx`

- [ ] **Step 1: 定义维度分组和指标选择**

```typescript
interface DimensionOption {
  label: string;
  metrics: BarMetric[];
}

const DIMENSION_OPTIONS: DimensionOption[] = [
  {
    label: '效率指标',
    metrics: [
      { key: 'totalTime', label: '总耗时', unit: 's' },
      { key: 'avgSpeed', label: '平均速度', unit: 'km/h' },
      { key: 'totalDistance', label: '总里程', unit: 'm' },
    ],
  },
  {
    label: '能耗指标',
    metrics: [
      { key: 'netEnergy', label: '净能耗', unit: 'kWh' },
      { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh' },
      { key: 'regenEnergy', label: '再生电量', unit: 'kWh' },
    ],
  },
  {
    label: '舒适度指标',
    metrics: [
      { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³' },
      { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³' },
      { key: 'maxAccel', label: '最大加速度', unit: 'm/s²' },
    ],
  },
  {
    label: '安全指标',
    metrics: [
      { key: 'ebCount', label: '紧急制动次数', unit: '次' },
      { key: 'minVoltage', label: '最低网压', unit: 'V' },
      { key: 'peakPower', label: '峰值功率', unit: 'kW' },
    ],
  },
  {
    label: '准点指标',
    metrics: [
      { key: 'totalDelay', label: '总晚点时间', unit: 's' },
    ],
  },
];
```

- [ ] **Step 2: 新增维度选择下拉框**

```tsx
export default function CompareChartBar({ scenarios }: CompareChartBarProps) {
  const [selectedDimension, setSelectedDimension] = useState(0);
  const dimension = DIMENSION_OPTIONS[selectedDimension];

  // ... 渲染逻辑使用 dimension.metrics 替代原来的 BAR_METRICS ...

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">
        📈 对比图表
        <select
          value={selectedDimension}
          onChange={(e) => setSelectedDimension(Number(e.target.value))}
          style={styles.select}
        >
          {DIMENSION_OPTIONS.map((d, i) => (
            <option key={i} value={i}>{d.label}</option>
          ))}
        </select>
      </div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 40px)' }} notMerge />
    </div>
  );
}
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/scenario/CompareChartBar.tsx
git commit -m "feat(ui): 柱状图支持维度下拉切换"
```

---

### 任务 11: 前端 — 新增参数对比组件

**文件：**
- 创建：`frontend/src/components/scenario/CompareParams.tsx`

- [ ] **Step 1: 创建参数对比组件**

```tsx
/**
 * CompareParams — 方案参数对比表格
 * 勾选1个方案时显示完整参数列表
 * 勾选2+个方案时显示差异对比（相同参数折叠）
 */
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareParamsProps {
  scenarios: ScenarioDetailResponse[];
}

interface ParamDef {
  group: string;
  key: string;
  label: string;
  unit: string;
  decimals: number;
}

const PARAM_DEFS: ParamDef[] = [
  // 车辆参数
  { group: '🚇 车辆参数', key: 'emptyMass', label: '空车质量', unit: 'kg', decimals: 0 },
  { group: '🚇 车辆参数', key: 'passengerCapacity', label: '载客量', unit: '人', decimals: 0 },
  { group: '🚇 车辆参数', key: 'maxSpeed', label: '最大速度', unit: 'km/h', decimals: 0 },
  { group: '🚇 车辆参数', key: 'maxTractionForce', label: '最大牵引力', unit: 'N', decimals: 0 },
  { group: '🚇 车辆参数', key: 'maxBrakeForce', label: '最大制动力', unit: 'N', decimals: 0 },
  { group: '🚇 车辆参数', key: 'davisA', label: 'Davis A', unit: '', decimals: 4 },
  { group: '🚇 车辆参数', key: 'davisB', label: 'Davis B', unit: '', decimals: 4 },
  { group: '🚇 车辆参数', key: 'davisCFrontArea', label: '迎风面积', unit: 'm²', decimals: 1 },
  { group: '🚇 车辆参数', key: 'davisCDragCoeff', label: '空气阻力系数 Cd', unit: '', decimals: 2 },
  { group: '🚇 车辆参数', key: 'curveResistCoeff', label: '弯道阻力系数', unit: '', decimals: 0 },
  { group: '🚇 车辆参数', key: 'tunnelResistFactor', label: '隧道阻力系数', unit: '', decimals: 1 },
  // 信号参数
  { group: '🚦 信号参数', key: 'dwellTime', label: '站停时间', unit: 's', decimals: 0 },
  { group: '🚦 信号参数', key: 'departureInterval', label: '发车间隔', unit: 's', decimals: 0 },
  { group: '🚦 信号参数', key: 'targetSpeedRatio', label: '目标速度比', unit: '', decimals: 2 },
  { group: '🚦 信号参数', key: 'safetyDistance', label: 'ATP安全距离', unit: 'm', decimals: 0 },
  { group: '🚦 信号参数', key: 'comfortDecel', label: '舒适减速度', unit: 'm/s²', decimals: 1 },
  { group: '🚦 信号参数', key: 'maxJerk', label: '冲击率上限', unit: 'm/s³', decimals: 2 },
  // 供电参数
  { group: '⚡ 供电参数', key: 'pantographVoltage', label: '网压', unit: 'V', decimals: 0 },
  { group: '⚡ 供电参数', key: 'substationCapacity', label: '变电所容量', unit: 'kW', decimals: 0 },
  // 仿真配置
  { group: '⚙️ 仿真配置', key: 'trainCount', label: '列车数', unit: '', decimals: 0 },
  { group: '⚙️ 仿真配置', key: 'bidirectional', label: '双向模式', unit: '', decimals: 0 },
];

/** 从 params 中按路径取值 */
function getParamValue(
  params: ScenarioDetailResponse['params'],
  key: string,
): number | string | null {
  // 先在 vehicle 中找
  const v = params.vehicle as unknown as Record<string, unknown>;
  if (v && key in v) return v[key] as number;
  // 在 signal 中找
  const s = params.signal as unknown as Record<string, unknown>;
  if (s && key in s) return s[key] as number;
  // 在 power 中找
  const p = params.power as unknown as Record<string, unknown>;
  if (p && key in p) return p[key] as number;
  // 在 simulation 中找
  const sim = params.simulation as unknown as Record<string, unknown>;
  if (sim && key in sim) return sim[key] as number;
  return null;
}

export default function CompareParams({ scenarios }: CompareParamsProps) {
  if (scenarios.length === 0) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">📐 参数对比</div>
        <div style={styles.empty}>请勾选方案查看参数</div>
      </div>
    );
  }

  // 只有一个方案：显示完整参数列表
  if (scenarios.length === 1) {
    const scenario = scenarios[0];
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">📐 {scenario.name} 参数详情</div>
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <tbody>
              {PARAM_DEFS.map((def) => {
                const val = getParamValue(scenario.params, def.key);
                return (
                  <tr key={def.key}>
                    <td style={styles.tdLabel}>{def.label}</td>
                    <td style={styles.td}>
                      {val !== null ? `${Number(val).toFixed(def.decimals)} ${def.unit}` : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // 2+ 个方案：差异对比模式
  // 计算每个参数在所有方案中的值，判断是否有差异
  const paramValues = new Map<string, (number | string | null)[]>();
  for (const def of PARAM_DEFS) {
    const values = scenarios.map((s) => getParamValue(s.params, def.key));
    paramValues.set(def.key, values);
  }

  const hasDiff = (key: string) => {
    const vals = paramValues.get(key);
    if (!vals || vals.length < 2) return false;
    const first = vals[0];
    return vals.some((v) => v !== first);
  };

  // 按分组渲染
  const groups = [...new Set(PARAM_DEFS.map((d) => d.group))];

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">📐 参数对比</div>
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
            {groups.map((group) => (
              <tr key={group}>
                <td colSpan={scenarios.length + 1} style={styles.groupHeader}>
                  {group}
                </td>
              </tr>
              {PARAM_DEFS
                .filter((d) => d.group === group)
                .map((def) => {
                  const diff = hasDiff(def.key);
                  // 无差异且方案数>1时折叠
                  if (!diff) return null;
                  const vals = paramValues.get(def.key)!;
                  return (
                    <tr key={def.key}>
                      <td style={styles.tdLabel}>{def.label}</td>
                      {vals.map((val, i) => (
                        <td key={i} style={styles.td}>
                          {val !== null
                            ? `${Number(val).toFixed(def.decimals)} ${def.unit}`
                            : '-'}
                        </td>
                      ))}
                    </tr>
                  );
                })}
            </tr>
          ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 添加样式**

```typescript
const styles: Record<string, React.CSSProperties> = {
  panel: { marginBottom: '12px' },
  tableWrapper: { overflowX: 'auto' },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '12px',
  },
  th: {
    textAlign: 'center',
    padding: '8px 10px',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-highlight)',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  td: {
    textAlign: 'center',
    padding: '7px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-primary)',
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  tdLabel: {
    textAlign: 'left',
    padding: '7px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  groupHeader: {
    textAlign: 'left',
    padding: '10px 10px 4px',
    color: 'var(--text-highlight)',
    fontWeight: 700,
    fontSize: '13px',
    borderBottom: '1px solid var(--border-color)',
    backgroundColor: 'rgba(42, 42, 74, 0.2)',
  },
  empty: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    padding: '24px 0',
  },
};
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/scenario/CompareParams.tsx
git commit -m "feat(ui): 新增方案参数对比组件"
```

---

### 任务 12: 前端 — 方案对比页面 Tab 切换

**文件：**
- 修改：`frontend/src/pages/ScenarioComparePage.tsx`

- [ ] **Step 1: 新增 Tab 状态和切换逻辑**

```tsx
import ScenarioSavePanel from '../components/scenario/ScenarioSavePanel';
import ScenarioListPanel from '../components/scenario/ScenarioListPanel';
import CompareTable from '../components/scenario/CompareTable';
import CompareChartBar from '../components/scenario/CompareChartBar';
import CompareParams from '../components/scenario/CompareParams';  // 新增
import type { ScenarioSummary, ScenarioDetailResponse } from '../types/simulation';

export default function ScenarioComparePage() {
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());
  const [details, setDetails] = useState<ScenarioDetailResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'metrics' | 'params'>('metrics');  // 新增

  // ... 已有逻辑不变 ...

  return (
    <div style={styles.container}>
      {/* 左侧：方案管理 */}
      <div style={styles.leftPanel}>
        <ScenarioSavePanel onSaved={loadScenarios} />
        <ScenarioListPanel
          scenarios={scenarios}
          checkedIds={checkedIds}
          onToggle={handleToggle}
          onDeleted={loadScenarios}
          onApplied={() => {
            window.dispatchEvent(new CustomEvent('scenario-applied'));
          }}
          loading={loading}
        />
      </div>

      {/* 右侧：对比视图 */}
      <div style={styles.rightPanel}>
        {/* Tab 切换 */}
        <div style={styles.tabBar}>
          <button
            style={{
              ...styles.tab,
              ...(activeTab === 'metrics' ? styles.tabActive : {}),
            }}
            onClick={() => setActiveTab('metrics')}
          >
            📊 指标对比
          </button>
          <button
            style={{
              ...styles.tab,
              ...(activeTab === 'params' ? styles.tabActive : {}),
            }}
            onClick={() => setActiveTab('params')}
          >
            📐 参数对比
          </button>
        </div>

        {detailsLoading ? (
          <div className="panel" style={styles.loadingPanel}>
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '24px 0' }}>
              加载方案详情中...
            </div>
          </div>
        ) : (
          <>
            {activeTab === 'metrics' && (
              <>
                <CompareTable scenarios={details} />
                <div style={styles.chartArea}>
                  <CompareChartBar scenarios={details} />
                </div>
              </>
            )}
            {activeTab === 'params' && (
              <CompareParams scenarios={details} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  // ... 已有样式 ...
  tabBar: {
    display: 'flex',
    gap: '0',
    marginBottom: '12px',
    borderBottom: '1px solid var(--border-color)',
  },
  tab: {
    padding: '8px 16px',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    background: 'transparent',
    border: 'none',
    borderBottom: '2px solid transparent',
    cursor: 'pointer',
    transition: 'color 0.2s, border-color 0.2s',
  },
  tabActive: {
    color: 'var(--color-primary)',
    borderBottomColor: 'var(--color-primary)',
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/pages/ScenarioComparePage.tsx
git commit -m "feat(ui): 方案对比页面新增 Tab 切换"
```

---

### 任务 13: 前端 — 处理 WebSocket evaluation_complete 事件

**文件：**
- 修改：`frontend/src/context/SimulationContext.tsx` 或对应的 WebSocket 处理逻辑

- [ ] **Step 1: 在 WebSocket 消息处理中新增事件类型**

在 `ServerMessage` 类型中新增：

```typescript
export type ServerMessage =
  | { type: 'simulation_snapshot'; timestamp: number; data: ApiSimulationSnapshot }
  | { type: 'init_state'; config: Record<string, unknown>; state?: { runState: RunState; simulationTime: number } }
  | { type: 'simulation_status'; data: { runState: RunState; simulationTime: number; reason?: string } }
  | { type: 'simulation_complete'; data: Record<string, unknown> }
  | { type: 'evaluation_complete'; data: { evaluationTime: number; elapsed: number } }  // 新增
  | { type: 'heartbeat'; serverTime?: string };
```

- [ ] **Step 2: 在消息处理中添加 evaluation_complete 处理**

在 WebSocket 消息分发逻辑中（`useSimulation.ts` 或 `SimulationContext.tsx`），新增：

```typescript
if (msg.type === 'evaluation_complete') {
  // 触发全局事件，供提示条组件使用
  window.dispatchEvent(new CustomEvent('evaluation-complete', {
    detail: {
      evaluationTime: msg.data.evaluationTime,
      elapsed: msg.data.elapsed,
    },
  }));
}
```

- [ ] **Step 3: 创建评估完成提示条组件（可选）**

如果需要提示条 UI，新增一个简单组件：

```tsx
// frontend/src/components/scenario/EvaluationBanner.tsx
import { useEffect, useState } from 'react';

export default function EvaluationBanner() {
  const [visible, setVisible] = useState(false);
  const [evaluationTime, setEvaluationTime] = useState(0);

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      setEvaluationTime(detail.evaluationTime);
      setVisible(true);
    };
    window.addEventListener('evaluation-complete', handler);
    return () => window.removeEventListener('evaluation-complete', handler);
  }, []);

  if (!visible) return null;

  return (
    <div style={styles.banner}>
      <span>🟢 指标评估已完成（{evaluationTime}s）</span>
      <span style={styles.text}>您可以保存方案进行对比</span>
      <button
        style={styles.btn}
        onClick={() => {
          // 跳转到方案对比页面
          window.dispatchEvent(new CustomEvent('navigate', { detail: { view: 'scenario' } }));
        }}
      >
        💾 保存方案
      </button>
      <button
        style={styles.closeBtn}
        onClick={() => setVisible(false)}
      >
        ✕
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  banner: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '8px 16px',
    backgroundColor: 'rgba(82, 196, 26, 0.1)',
    border: '1px solid var(--color-success)',
    borderRadius: '4px',
    fontSize: '13px',
    color: 'var(--text-primary)',
    marginBottom: '8px',
  },
  text: { color: 'var(--text-secondary)', fontSize: '12px' },
  btn: {
    marginLeft: 'auto',
    padding: '4px 12px',
    fontSize: '12px',
    cursor: 'pointer',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '4px',
  },
};
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types/simulation.ts frontend/src/hooks/useSimulation.ts frontend/src/components/scenario/EvaluationBanner.tsx
git commit -m "feat(ui): 评估完成事件处理与提示条"
```

---

## 自检清单

1. **Spec覆盖检查：**
   - ✅ 评估窗口机制 → 任务 1、2、4
   - ✅ 评估完成通知 → 任务 2 Step 4、任务 13
   - ✅ 6个新增指标 → 任务 2、4、5、9
   - ✅ 6个参数控件 → 任务 3、6、7、8
   - ✅ 参数对比 Tab → 任务 11、12
   - ✅ 柱状图维度切换 → 任务 10
   - ✅ 供电参数补齐 → 任务 3 Step 3
   - ✅ eveluation_time 配置级更新 → 任务 3 Step 4

2. **Placeholder检查：** 无 TBD/TODO 占位

3. **类型一致性检查：** 后端字段与前端字段的 camelCase/snake_case 映射一致，参数按键名在 `getParamValue` 中统一查找