# 参数-指标矩阵与方案对比增强设计

> **日期：** 2026-07-14
> **状态：** 设计确认
> **关联迭代：** 迭代三
> **关联需求：** UI-PARAM-06（参数预设方案保存/加载扩展）、多方案对比决策功能增强

---

## 一、概述

### 1.1 目标

在现有方案对比功能基础上，系统性地解决以下问题：

1. **公平对比** — 所有方案在固定评估窗口内比较，避免跑多跑少无法对比
2. **指标全面** — 从效率/能耗/舒适/安全/准点5个维度综合评价方案
3. **参数完整** — 补齐前端未暴露的参数，让用户能调所有影响仿真的参数
4. **参数可对比** — 方案之间改了哪些参数一目了然

### 1.2 设计原则

- **增量修改** — 不重构现有架构，只做扩展
- **方案即模板** — 不另做独立参数预设系统，加载方案参数即可作为基底
- **向后兼容** — 旧方案JSON文件仍可读取，缺少的字段用默认值填充

---

## 二、评估窗口机制

### 2.1 两个时长参数

| 参数 | 含义 | 默认值 | 配置位置 |
|------|------|--------|---------|
| `total_time` | 仿真运行硬上限 | 6000s | `simulation.yaml`（已有） |
| `evaluation_time` | 评估窗口时长 | 600s | `simulation.yaml`（新增） |

### 2.2 后端逻辑

**配置加载**（`core/config.py`）：

```python
@dataclass
class SimulationParams:
    total_time: float = 6000.0        # 已有
    evaluation_time: float = 600.0    # 新增
    # ...
```

**方案保存时的指标截取**（`api/scenarios.py` `save_scenario`）：

```
1. 确定评估时长 eval_duration = min(evaluation_time, 实际仿真时长)
2. 从 recorder.buffer 筛选 time <= eval_duration 的记录
3. 基于筛选后的数据计算：
   - totalTime = eval_duration
   - totalDistance = max_position（筛选后）
   - avgSpeed = 筛选后平均速度
   - maxSpeed = 筛选后最大速度
4. 能耗/网压/峰值功率：
   - 取 eval_duration 时刻 snapshot 的快照值
   - 或取筛选后窗口内的累计值
5. 冲击率/加速度：
   - 取筛选后窗口内的最大值/平均值
6. 紧急制动次数：
   - 统计筛选后窗口内触发次数
7. 晚点时间：
   - 统计筛选后窗口内累计晚点
8. result 中记录 evaluationDuration = eval_duration
```

### 2.3 评估完成通知

当 `clock.elapsed` 首次达到 `evaluation_time` 时，后端通过 WebSocket 广播 `evaluation_complete` 事件，仿真**继续运行不受影响**。

**WebSocket 消息格式：**

```json
{
  "type": "evaluation_complete",
  "data": {
    "evaluationTime": 600,
    "elapsed": 600.0,
    "message": "指标评估已完成（600s），您可以保存方案进行对比"
  }
}
```

**后端实现**（`SimulationManager._run_loop`）：

```python
# 在 _run_loop 的 snapshot 广播之后
if (self._evaluation_snapshot is None
    and orch.clock.elapsed >= orch.sim_params.evaluation_time):
    self._evaluation_snapshot = {
        "elapsed": orch.clock.elapsed,
        "summary": orch.recorder.summary(),
        "tracking": {
            "minVoltage": self._min_voltage,
            "peakPower": self._peak_power,
            "maxJerk": self._max_jerk,
            "avgJerk": self._jerk_sum / max(self._jerk_count, 1),
            "maxAccel": self._max_accel,
            "ebCount": self._eb_count,
            "totalDelay": self._total_delay,
        }
    }
    await self.ws_manager.broadcast({
        "type": "evaluation_complete",
        "data": {
            "evaluationTime": orch.sim_params.evaluation_time,
            "elapsed": orch.clock.elapsed,
        }
    })
    # 仿真继续跑，不停止
    # 同时缓存此刻的 snapshot 数据（能耗/网压等），供后续方案保存使用
    current_snapshot = snapshot
```

**前端处理：**

```
┌─ 收到 evaluation_complete ─────────────────────────────────┐
│                                                             │
│  🟢 指标评估已完成 (600s)                                    │
│  您可以保存方案进行对比  [💾 保存方案]  [✕ 继续跑]             │
│                                                             │
│  - 提示条淡入在顶部，不弹窗不阻塞                               │
│  - 点"保存方案" → 跳转到方案对比页面，自动打开保存面板           │
│  - 点 ✕ 或 30s 后自动消失                                     │
│  - 仿真继续跑，不受影响                                        │
└─────────────────────────────────────────────────────────────┘
```

**保存方案时的指标截取：**

如果存在 `_evaluation_snapshot`，方案保存时直接用缓存数据计算指标（避免从 recorder 中截取）：
- 效率指标 ← `_evaluation_snapshot.summary`
- 舒适度/安全/准点指标 ← `_evaluation_snapshot.tracking`
- 能耗指标 ← 从 `_evaluation_time` 时刻缓存的 snapshot 提取

如果不存在 `_evaluation_snapshot`（旧版本或手动提前停止），回退到从 recorder 截取。

### 2.4 边界情况

| 场景 | 处理 |
|------|------|
| 仿真跑满 6000s，`evaluation_time=600` | 截取前 600s 数据算指标 |
| 仿真跑了 200s 提前停，`evaluation_time=600` | 按 200s 算，标记 `actualDuration: 200` |
| `evaluation_time` > `total_time` | 以 `total_time` 为准 |
| `evaluation_time` = 0 或未配置 | 回退到实际仿真时长（保持向后兼容） |
| 仿真 pause 后 resume，`evaluation_time` 未到 | 累计时间继续，到点再次触发通知 |
| 仿真 stop 时 `evaluation_time` 未到 | 不触发通知，保存方案时按实际时长截取 |

---

## 三、指标体系

### 3.1 指标总览（15个）

#### 效率维度（4个）

| 指标 | 含义 | 单位 | 优劣 | 数据来源 |
|------|------|------|------|---------|
| `totalTime` | 总耗时(评估窗口) | s | ↓ | 已有 |
| `totalDistance` | 总里程 | m | ↑ | 已有 |
| `avgSpeed` | 平均速度 | km/h | ↑ | 已有 |
| `maxSpeed` | 最高速度 | km/h | ↑ | 已有 |

#### 能耗维度（4个）

| 指标 | 含义 | 单位 | 优劣 | 数据来源 |
|------|------|------|------|---------|
| `tractionEnergy` | 牵引能耗 | kWh | ↓ | 已有 |
| `regenEnergy` | 再生电量 | kWh | ↑ | 已有 |
| `netEnergy` | 净能耗 | kWh | ↓ | 已有 |
| `regenRate` | 再生利用率 | % | ↑ | 新增：`regenEnergy / tractionEnergy × 100`，tractionEnergy=0 时返回 0 |

#### 舒适度维度（3个）

| 指标 | 含义 | 单位 | 优劣 | 数据来源 |
|------|------|------|------|---------|
| `maxJerk` | 最大冲击率 | m/s³ | ↓ | 新增：`TrainState.jerk` 窗口内最大值 |
| `avgJerk` | 平均冲击率 | m/s³ | ↓ | 新增：窗口内 jerk 平均值 |
| `maxAccel` | 最大加速度 | m/s² | ↓ | 新增：`TrainState.acceleration` 窗口内最大值 |

#### 安全维度（3个）

| 指标 | 含义 | 单位 | 优劣 | 数据来源 |
|------|------|------|------|---------|
| `minVoltage` | 最低网压 | V | ↑ | 已有 |
| `peakPower` | 峰值功率 | kW | ↓ | 已有 |
| `ebCount` | 紧急制动次数 | 次 | ↓ | 新增：仿真过程中 `emergency_brake=True` 触发次数 |

#### 准点维度（1个）

| 指标 | 含义 | 单位 | 优劣 | 数据来源 |
|------|------|------|------|---------|
| `totalDelay` | 总晚点时间 | s | ↓ | 新增：`timetableDeviation` 中正偏差累计 |

### 3.2 方案JSON扩展

```json
{
  "result": {
    // 已有字段
    "totalTime": 185.2,
    "totalDistance": 3200.0,
    "avgSpeed": 45.2,
    "maxSpeed": 64.1,
    "tractionEnergy": 28.5,
    "regenEnergy": 4.2,
    "netEnergy": 24.3,
    "minVoltage": 1380,
    "peakPower": 3200,
    // 新增字段
    "maxJerk": 0.52,
    "avgJerk": 0.18,
    "maxAccel": 0.85,
    "regenRate": 14.7,
    "ebCount": 0,
    "totalDelay": 12.5,
    "evaluationDuration": 600
  }
}
```

### 3.3 向后兼容

旧方案 JSON 缺少新增字段，前端读取时：

```typescript
const maxJerk = result.maxJerk ?? 0;       // 缺省 = 0
const avgJerk = result.avgJerk ?? 0;
const maxAccel = result.maxAccel ?? 0;
const regenRate = result.regenRate ?? 0;
const ebCount = result.ebCount ?? 0;
const totalDelay = result.totalDelay ?? 0;
```

---

## 四、参数暴露补齐

### 4.1 前端新增控件（6个）

#### 车辆参数区新增（`VehicleParams.tsx`）

| 参数 | 字段名 | 默认值 | 步进 | 最小值 | 最大值 |
|------|--------|--------|------|--------|--------|
| 空气阻力系数 Cd | `davisCDragCoeff` | 0.5 | 0.05 | 0.01 | 2.0 |
| 弯道阻力系数 | `curveResistCoeff` | 600 | 50 | 100 | 2000 |
| 隧道阻力系数 | `tunnelResistFactor` | 1.2 | 0.1 | 1.0 | 3.0 |

#### 信号参数区新增（`SignalParams.tsx`）

| 参数 | 字段名 | 默认值 | 步进 | 最小值 | 最大值 |
|------|--------|--------|------|--------|--------|
| ATP安全距离 | `safetyDistance` | 300 | 30 | 50 | 1000 |
| 舒适减速度 | `comfortDecel` | 0.8 | 0.1 | 0.1 | 2.0 |
| 冲击率上限 | `maxJerk` | 0.75 | 0.05 | 0.1 | 2.0 |

### 4.2 后端补全

**`get_params()` 在 signal 部分新增（`simulation_manager.py`）：**

```python
"signal": {
    # 已有
    "dwellTime": ...,
    "departureInterval": ...,
    "targetSpeedRatio": ...,
    # 新增
    "safetyDistance": orch.sim_params.signal.atp.safety_distance,
    "comfortDecel": orch.sim_params.pid.comfort_decel,
    "maxJerk": orch.sim_params.pid.max_jerk,
}
```

**`update_params()` 新增 signal 更新逻辑：**

```python
signal_updates = updates.get("signal", {})
# 已有 3 个
if "targetSpeedRatio" in signal_updates: ...
if "departureInterval" in signal_updates: ...
if "dwellTime" in signal_updates: ...
# 新增 3 个
if "safetyDistance" in signal_updates:
    orch.sim_params.signal.atp.safety_distance = float(...)
if "comfortDecel" in signal_updates:
    orch.sim_params.pid.comfort_decel = float(...)
if "maxJerk" in signal_updates:
    orch.sim_params.pid.max_jerk = float(...)
```

**`update_params()` 新增 power 更新逻辑（需处理无变电所配置的情况）：**

```python
power_updates = updates.get("power", {})
subs = orch.sim_params.power.substations
if "pantographVoltage" in power_updates and subs:
    # 所有变电所的额定电压统一更新
    for sub in subs:
        sub.rated_voltage = float(power_updates["pantographVoltage"])
if "substationCapacity" in power_updates and subs:
    for sub in subs:
        sub.rated_power = float(power_updates["substationCapacity"])
```

### 4.3 方案参数的完整性

当前方案保存时 `params` 结构已包含 `vehicle` / `signal` / `power` / `simulation` 四部分。需要补充：

- `get_params()` 的 vehicle 部分已包含 `davisCDragCoeff` / `curveResistCoeff` / `tunnelResistFactor`（已有）
- `get_params()` 的 signal 部分补全 `safetyDistance` / `comfortDecel` / `maxJerk`
- `get_params()` 的 power 部分去掉硬编码，从 `orch.sim_params.power` 读取
- `params.simulation` 增加 `evaluationTime`、`coastingMinSpeed`、`stationStopTolerance`

### 4.4 `update_config` 同步支持

`evaluation_time` 属于配置级参数（写入 YAML 文件），需在 `update_config()` 的 `field_map` 中补充：

```python
# simulation_manager.py update_config() 中的 field_map 补充
field_map = {
    # 已有
    "timeStep": "time_step",
    "totalTime": "total_time",
    # ...
    # 新增
    "evaluationTime": "evaluation_time",
}
```

---

## 五、方案数据采集逻辑

### 5.1 保存方案时的数据流

```
用户点"保存"
  ↓
校验引擎状态（必须非运行中）
  ↓
确定评估时长 eval_duration = min(evaluation_time, 实际仿真时长)
  ↓
从 recorder.buffer 截取 time <= eval_duration 的记录
  ↓
计算指标：
  ├── 效率指标 ← 从截取后的记录计算
  ├── 能耗指标 ← 从截取后的 snapshot 提取
  ├── 舒适度指标 ← 从截取后的记录计算 jerk/accel 极值
  ├── 安全指标 ← 从追踪变量提取 minVoltage/peakPower/ebCount
  └── 准点指标 ← 从 timetableDeviation 累计
  ↓
从 get_params() 获取当前参数快照
  ↓
组装 JSON 写入 scenarios/ 目录
```

### 5.2 新增追踪变量

在 `SimulationManager` 中新增追踪变量：

```python
class SimulationManager:
    def __init__(self, ...):
        # 已有
        self._min_voltage = 1500.0
        self._peak_power = 0.0
        # 新增
        self._max_jerk = 0.0
        self._jerk_sum = 0.0
        self._jerk_count = 0
        self._max_accel = 0.0
        self._eb_count = 0
        self._eb_prev_states: dict[str, bool] = {}  # 各列车上一帧的紧急制动状态
        self._total_delay = 0.0
        self._prev_delays: dict[str, dict[str, float]] = {}  # (trainId, stationId) → 上次记录的偏差
```

在 `_update_tracking()` 中更新：

```python
def _update_tracking(self, snapshot: dict) -> None:
    self._last_snapshot = snapshot
    
    # 原有追踪
    power_data = snapshot.get("data", {}).get("power", {})
    # ... minVoltage / peakPower ...
    
    # 舒适度追踪（极值 + 平均值）
    trains = snapshot.get("data", {}).get("trains", [])
    for t in trains:
        jerk = t.get("jerk", 0)
        self._max_jerk = max(self._max_jerk, jerk)
        self._jerk_sum += jerk
        self._jerk_count += 1
        self._max_accel = max(self._max_accel, abs(t.get("acceleration", 0)))
    
    # 紧急制动计数：只统计 0→1 的上升沿，避免重复计数
    cmds = snapshot.get("data", {}).get("signaling", {}).get("controlCommands", [])
    for cmd in cmds:
        tid = cmd.get("trainId", "")
        eb = cmd.get("emergencyBrake", False)
        prev_eb = self._eb_prev_states.get(tid, False)
        if eb and not prev_eb:
            self._eb_count += 1
        self._eb_prev_states[tid] = eb
    
    # 晚点累计：记录最新偏差值，不重复累加
    devs = snapshot.get("data", {}).get("signaling", {}).get("timetableDeviation", [])
    for d in devs:
        tid = d.get("trainId", "")
        sid = d.get("stationId", "")
        delay = d.get("delayArrival", 0)
        if delay > 0:
            key = f"{tid}_{sid}"
            prev_delay = self._prev_delays.get(key, 0.0)
            if delay > prev_delay:
                # 只在偏差增大时累加增量（首次到达该站时 prev_delay=0）
                self._total_delay += delay - prev_delay
                self._prev_delays[key] = delay
```

---

## 六、前端对比增强

### 6.1 对比页面布局

```
┌─────────────────────────────────────────────────────────────┐
│  顶部栏 (现有)                                                │
├──────────────────┬──────────────────────────────────────────┤
│  📋 方案管理      │  [指标对比] [参数对比]  ← Tab 切换         │
│                  │                                          │
│  [保存方案]       │  Tab 1: 指标对比                          │
│                  │  ┌────────────────────────────────────┐   │
│  ☑ ATO经济       │  │  按维度分组的对比表格               │   │
│  ☑ 三段式重载     │  │  + 柱状图                          │   │
│  ☐ 高速方案       │  └────────────────────────────────────┘   │
│                  │                                          │
│  [加载] [删除]   │  Tab 2: 参数对比                          │
│                  │  ┌────────────────────────────────────┐   │
│                  │  │  只显示有差异的参数表格              │   │
│                  │  │  + 差异高亮/折叠相同参数             │   │
│                  │  └────────────────────────────────────┘   │
└──────────────────┴──────────────────────────────────────────┘
```

### 6.2 指标对比 Tab

**对比表格（`CompareTable.tsx` 增强）：**

- 指标按 5 个维度分组，每个维度有分组标题行
- 旧方案（缺少新指标）显示 `-` 或 `0`
- 颜色标识：绿色=最优，红色=最差（已有）
- 新增 `evaluationDuration` 辅助信息行

**对比柱状图（`CompareChartBar.tsx` 增强）：**

- 改为下拉选择要对比的维度（效率/能耗/舒适/安全/准点）
- 默认展示"效率"维度

### 6.3 参数对比 Tab（新增）

**`CompareParams.tsx`（新增组件）：**

- 读取各方案的 `params` 字段，按 `vehicle` / `signal` / `power` / `simulation` 分组展示
- **勾选 0 个方案**：提示"请勾选方案查看参数"
- **勾选 1 个方案**：显示该方案的完整参数列表（相当于"查看方案参数详情"）
- **勾选 2+ 个方案**：差异对比模式
  - 相同参数自动折叠，显示"所有方案相同"
  - 有差异的参数高亮显示，差异值用颜色标识（增大=红色，减小=绿色）
  - 同一参数在所有方案中值相同时，合并为一行显示

### 6.4 新增/修改文件清单

| 文件 | 操作 | 说明 |
|:----|:----|:-----|
| `frontend/src/types/simulation.ts` | 修改 | ScenarioResult 新增6个字段、争取参数对比类型 |
| `frontend/src/components/scenario/CompareTable.tsx` | 修改 | 按分组展示、新增指标行 |
| `frontend/src/components/scenario/CompareChartBar.tsx` | 修改 | 支持维度切换 |
| `frontend/src/components/scenario/CompareParams.tsx` | **新增** | 参数对比表格 |
| `frontend/src/pages/ScenarioComparePage.tsx` | 修改 | 右侧 Tab 切换 |
| `frontend/src/components/param/VehicleParams.tsx` | 修改 | 新增3个控件 |
| `frontend/src/components/param/SignalParams.tsx` | 修改 | 新增3个控件 |
| `frontend/src/utils/paramStep.ts` | 修改 | 新增参数步进定义 |
| `frontend/src/components/param/PowerParams.tsx` | 修改 | 补齐更新逻辑 |

---

## 七、后端修改文件清单

| 文件 | 操作 | 说明 |
|:----|:----|:-----|
| `sim_engine/core/config.py` | 修改 | `SimulationParams` 新增 `evaluation_time` |
| `sim_engine/config/simulation.yaml` | 修改 | 新增 `evaluation_time` 配置项 |
| `sim_engine/services/simulation_manager.py` | 修改 | `get_params` / `update_params` 补全 signal 和 power 参数；新增追踪变量 |
| `sim_engine/api/scenarios.py` | 修改 | `save_scenario` 按评估窗口截取指标、新增6个指标计算 |
| `sim_engine/orchestrator.py` | 修改 | 可选：暴露 `step_once` 中的 ebCount 追踪 |

---

## 八、不做的事项

1. **综合评分/加权评分** — 先展示各维度指标，加权评分后续迭代
2. **雷达图** — 后续迭代
3. **方案编辑** — 保存后不可编辑参数，只能删除重建
4. **方案分组/标签/搜索** — 简单列表即可
5. **方案导入/导出** — 后续迭代
6. **批量无头运行** — 手动跑一个保存一个
7. **独立参数预设系统** — 方案即模板，不另做预设

---

## 九、边界情况与错误处理

| 场景 | 处理方式 |
|:-----|:---------|
| 引擎从未运行过就点保存 | 提示"请先运行一次仿真" |
| 仿真正在运行时点保存 | 提示"请先暂停或停止仿真" |
| 仿真跑了不到 evaluation_time 就停了 | 按实际时长截取，标注 `actualDuration` |
| 旧方案 JSON 缺少新字段 | 前端读取时用 `??` 回退到默认值 |
| 勾选 < 2 个方案 | 对比表格提示"请勾选至少 2 个方案进行对比" |
| 勾选 < 2 个方案看参数对比 | 显示该方案的完整参数列表 |
| 方案文件损坏 | 跳过，不阻塞列表加载 |