# 单方向多列车仿真设计

**日期：** 2026-07-12  
**范围：** 迭代二 — 同向多车仿真 + SIG-07 基础 enforcement（另一方向由队友负责）  
**前置：** 信号 Task 1~10 已完成（ATP/ATO/ATS、`train_following` 占位）

---

## 1. 背景与目标

当前编排器为**单列车、单方向** MVP：`Orchestrator.step_once()` 只推进一列车，`build_simulation_snapshot()` 固定输出 `trains: [1]`。前端线路图已支持 `trains.map()` 多 marker，但后端始终只发 1 辆车。

**目标：**

1. 支持**同方向**多列车并行仿真（`train_count` + `departure_interval` 配置驱动）
2. 每车独立三段式 / ATS / 手动 EB，共享轨道与仿真时钟
3. 接入 SIG-07 占位逻辑：固定追踪间隔不足时后车 EB；MA 终点受前车约束
4. snapshot / REST / WebSocket 输出多车数据，供线路图与后续 SIG-07 验收

**不在范围：**

- 下行 / 反向列车（队友负责）
- 动态间隔、联锁 CI、车门 EB（SIG-10）
- 多车再生能量就近吸收
- 前端详情视图多车切换（可继续默认 `trains[0]`）

---

## 2. 方案对比

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| **A（推荐）** | 编排器内 `list[TrainRun]`，单 `step_once` 循环 | 改动集中、复用现有信号链、与 snapshot 一致 | `orchestrator.py` 变长 |
| B | 多 Orchestrator 实例 + 协调器 | 边界清晰 | 时钟/轨道/供电重复，重构量大 |
| C | 进程级多实例 | 隔离好 | 过度设计，违背 MVP |

**推荐方案 A：** 在现有 `Orchestrator` 上扩展，保留 `train_state` / `signaling` 等属性指向首车，保证现有单车测试无需大改。

---

## 3. 架构

### 3.1 TrainRun 单元

每列车一个 `TrainRun` dataclass：

```python
@dataclass
class TrainRun:
    train_id: str                    # TRAIN_01, TRAIN_02, ...
    state: TrainState
    signaling: ThreeStageController  # 独立阶段机
    ats: ATSController               # 独立 ATS（时刻表 train_id 不同）
    manual_driver: ManualDriveController
    spawn_time: float                # i * departure_interval
    active: bool                     # 是否已发车
    last_step: StepResult | None = None
```

共享组件：`VehicleSystem`、`TrackPathService`、`SimulationClock`、`ATPController`（无状态）、`PowerNetwork`、`OccupancyDetector`。

### 3.2 发车逻辑

- `reset()`：创建 `train_count` 个 `TrainRun`；仅 `TRAIN_01` 初始 `active=True`
- 每步开头：若 `clock.elapsed >= spawn_time` 且未 active，则激活并 `signaling.reset()`
- 未 active 的列车：不参与步进、不占 snapshot `trains[]`、不占 occupancy

### 3.3 步进顺序（每仿真步）

```
for each active TrainRun (按 position 升序):
  1. 确定前车位置 leading_pos（同向更高 chainage 的最近前车）
  2. signaling.compute_commands(state, dt, elapsed)
  3. ATP 超速检查 → EB
  4. SIG-07: 若 leading_pos 存在且间隔不足 → EB
  5. manual_driver 叠加
  6. vehicle.step → 更新 state
  7. ATP.build_ma_profile(..., leading_chainage=leading_pos - safety_distance)
occupancy.update({train_id: position for all active})
power: 聚合各车 power_demand；电压采样用最高位置列车
build_simulation_snapshot(trains=[...], signaling_extra={...})
clock.tick()
```

### 3.4 SIG-07 间隔判定

沿用 `train_following.is_interval_safe(ahead_pos, rear_pos, min_interval)`（与现有测试一致：第一参数为前方列车 chainage，第二参数为后方列车 chainage）。  
当 `not is_interval_safe(leading_pos, rear_pos, following_min_interval)` 时，对**后方**列车施加 EB。

`following_min_interval` 来自 `signal.yaml` → `SignalConfig.following_min_interval`（默认 500m）。

### 3.5 Snapshot 扩展

- `data.trains[]`：所有 active 列车
- `signaling.controlCommands[]` / `speedLimits[]` / `maProfile[]`：每车一条
- `signaling.timetableDeviation[]`：合并各车 ATS 偏离
- 新增 `signaling.trainIntervals[]`（SIG-07 基础）：

```json
{
  "trainId": "TRAIN_02",
  "leadingTrainId": "TRAIN_01",
  "intervalM": 520.0,
  "minIntervalM": 500.0,
  "safe": true
}
```

### 3.6 向后兼容

Orchestrator 保留属性（指向首车或 `trains[0]`）：

- `train_state`（含 setter）
- `train_id`, `signaling`, `manual_driver`, `ats`, `last_step`

`set_emergency_brake(active)`：对所有 `TrainRun.manual_driver` 生效。

Recorder：每步仍写 1 条记录（取 position 最大的列车），保持现有 `test_recorder_buffer_grows` 行为。

### 3.7 SimulationManager

- `get_status().trainCount` ← `sim_params.train_count`
- `get_params().signal.departureInterval` ← `sim_params.departure_interval`
- `update_config` 支持 `trainCount` / `departureInterval` 写入 `simulation.yaml`
- `_run_loop` 结束条件：超时 **或** 全部列车已 spawn 且均到终点停稳

---

## 4. 配置

`simulation.yaml` 新增：

```yaml
simulation:
  train_count: 3
  departure_interval: 120.0
```

`SimulationParams` 新增字段，默认值 `train_count=1`、`departure_interval=120.0`（单车行为不变）。

---

## 5. 测试策略

| 层级 | 内容 |
|------|------|
| 单元 | 配置加载、`is_interval_safe`（已有）、ATP leading 约束 |
| 集成 | 多车 spawn、snapshot `len(trains)==N`、间隔 EB、MA 截断 |
| 回归 | 现有 `test_orchestrator*.py` 在 `train_count=1` 下仍通过 |

---

## 6. 文档冲突（需组长确认）

- `docs/需求文档.md` / `迭代二_单列车增强需求文档.md`：SIG-07 标为**迭代二**
- `docs/详细设计文档.md` §4.3：多车追踪流程标为**迭代三**

本设计按**迭代二多车基础 + SIG-07 enforcement** 实施；若组长认定多车属迭代三，需调整需求文档后再合并。

---

## 7. 验收标准

1. `train_count=3`、`departure_interval=120` 时，线路图/WebSocket 可见 3 辆同向列车，按间隔依次发车
2. 人工缩小间隔或加速后车，后车 snapshot 出现 `emergencyBrake: true`
3. `signaling.trainIntervals` 输出每对追踪关系及是否 safe
4. `train_count=1` 时行为与当前 MVP 一致，全量 pytest 通过
