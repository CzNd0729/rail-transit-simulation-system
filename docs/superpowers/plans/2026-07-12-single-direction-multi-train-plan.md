# 单方向多列车仿真 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有单列车 MVP 上实现同方向多列车仿真（配置驱动发车），并接入 SIG-07 固定追踪间隔 enforcement，为线路图多车展示与完整 SIG-07 验收打基础。

**Architecture:** 编排器维护 `list[TrainRun]`，每车独立 `ThreeStageController` + `ATSController` + `ManualDriveController`；`step_once` 按 position 顺序步进所有 active 列车；共享时钟/轨道/ATP；snapshot 输出多车 `trains[]` 与 `trainIntervals[]`。

**Tech Stack:** Python 3.10+, dataclass, PyYAML, pytest, 现有 `Orchestrator` / `build_simulation_snapshot` / `train_following.is_interval_safe`

**设计文档：** `docs/superpowers/specs/2026-07-12-single-direction-multi-train-design.md`

## Global Constraints

- 所有可调参数通过 YAML 注入，不得硬编码（NFR-07）
- 无额外非必要第三方依赖（NFR-06）
- 模块间通过 dataclass 契约交互；禁止跨模块 import 内部实现（`backend/CLAUDE.md`）
- 对外速度单位 km/h，位置 m，时间步长 dt 为秒
- 范围：**单方向**多车；反向由队友负责
- `train_count=1` 时必须与现有 MVP 行为一致（回归测试全绿）
- 提交格式：`feat(<scope>): <中文描述>`（≤50 字符，caveman-commit）；**一 Task 一提交**
- 文档冲突（SIG-07 迭代归属）不得自行修改 `docs/`，需提醒组长

## File Map

| 文件 | 职责 |
|------|------|
| `core/config.py` | `SimulationParams.train_count`, `departure_interval` |
| `config/simulation.yaml` | 多车默认配置 |
| `orchestrator.py` | `TrainRun`、多车 `step_once`、spawn、SIG-07 EB |
| `data/snapshot.py` | 多车 `trains[]`、`trainIntervals` |
| `signaling/atp.py` | MA 终点受前车 chainage 约束 |
| `signaling/train_following.py` | 已有 `is_interval_safe`（本计划只接入） |
| `services/simulation_manager.py` | `trainCount` / `departureInterval` API 对齐 |
| `tests/test_multi_train.py` | 多车专项集成测试 |

---

### Task 1: 多车仿真配置（train_count / departure_interval）

**Files:**
- Modify: `backend/sim_engine/core/config.py`
- Modify: `backend/sim_engine/config/simulation.yaml`
- Create: `backend/tests/test_simulation_multi_train_config.py`

**Interfaces:**
- Produces:
  - `SimulationParams.train_count: int = 1`
  - `SimulationParams.departure_interval: float = 120.0`
  - `load_simulation_params()` 从 `simulation.yaml` 读取上述字段

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_simulation_multi_train_config.py`:

```python
"""多车仿真配置加载测试。"""

from __future__ import annotations

from sim_engine.core.config import SimulationParams, load_simulation_params


def test_simulation_params_defaults():
    p = SimulationParams()
    assert p.train_count == 1
    assert p.departure_interval == 120.0


def test_load_train_count_from_yaml(tmp_path):
    yaml_text = """
simulation:
  train_count: 3
  departure_interval: 90.0
  time_step: 0.1
"""
    p = tmp_path / "simulation.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    params = load_simulation_params(p)
    assert params.train_count == 3
    assert params.departure_interval == 90.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_simulation_multi_train_config.py -v`

Expected: FAIL — `SimulationParams` 无 `train_count` 属性

- [ ] **Step 3: 实现配置字段**

在 `backend/sim_engine/core/config.py` 的 `SimulationParams` 增加：

```python
train_count: int = 1
departure_interval: float = 120.0
```

在 `load_simulation_params()` 增加：

```python
train_count=int(data.get("train_count", 1)),
departure_interval=float(data.get("departure_interval", 120.0)),
```

在 `backend/sim_engine/config/simulation.yaml` 增加（演示默认 3 车）：

```yaml
  train_count: 3
  departure_interval: 120.0
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_simulation_multi_train_config.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/core/config.py backend/sim_engine/config/simulation.yaml backend/tests/test_simulation_multi_train_config.py
git commit -m "feat(sim): 多车仿真配置项"
```

---

### Task 2: TrainRun 模型与编排器多车初始化

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Create: `backend/tests/test_train_run_init.py`

**Interfaces:**
- Produces:
  - `@dataclass TrainRun`（见设计文档 §3.1）
  - `Orchestrator.trains: list[TrainRun]`
  - `Orchestrator._init_trains(passenger_load: float) -> None`
  - 向后兼容属性：`train_state`, `train_id`, `signaling`, `manual_driver`, `ats`, `last_step`
  - `reset()` / `from_config_dir()` 创建 N 个 TrainRun；仅首车 `active=True`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_train_run_init.py`:

```python
"""TrainRun 初始化与向后兼容属性测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_orchestrator_creates_multiple_train_runs():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 3
    orch.reset()
    assert len(orch.trains) == 3
    assert orch.trains[0].train_id == "TRAIN_01"
    assert orch.trains[1].train_id == "TRAIN_02"
    assert orch.trains[0].active is True
    assert orch.trains[1].active is False
    assert orch.trains[1].spawn_time == orch.sim_params.departure_interval


def test_backward_compat_train_state_property():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    assert orch.train_state is orch.trains[0].state
    orch.train_state.speed = 42.0
    assert orch.trains[0].state.speed == 42.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_train_run_init.py -v`

Expected: FAIL — 无 `trains` 属性

- [ ] **Step 3: 实现 TrainRun 与 _init_trains**

在 `orchestrator.py` 顶部增加 `TrainRun` dataclass；`from_config_dir` 末尾调用 `_init_trains`；`reset()` 重建列车列表。每车：

- 复制 `timetable.yaml` 条目，`train_id=f"TRAIN_{i+1:02d}"`
- 独立 `ATSController` + `ThreeStageController`
- `spawn_time = i * sim_params.departure_interval`

**注意：** 此 Task **不改造** `step_once`，仍只步进首车（或保持现有单车逻辑），确保 Task 2 完成后现有集成测试仍绿。

- [ ] **Step 4: 运行测试**

Run: `cd backend && uv run pytest tests/test_train_run_init.py tests/test_orchestrator.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/orchestrator.py backend/tests/test_train_run_init.py
git commit -m "feat(orchestrator): TrainRun 多车初始化"
```

---

### Task 3: 多车 step_once 步进与 snapshot 多 trains[]

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Modify: `backend/sim_engine/data/snapshot.py`
- Create: `backend/tests/test_multi_train_step.py`

**Interfaces:**
- Consumes: Task 2 的 `TrainRun`, `Orchestrator.trains`
- Produces:
  - `step_once()` 循环所有 `active` TrainRun 并步进
  - spawn 检查：`elapsed >= spawn_time` → `active=True` + `signaling.reset()`
  - `build_simulation_snapshot(..., train_entries: list[TrainSnapshotEntry])` 或等价多车参数
  - `occupancy.update({id: pos for active trains})`
  - snapshot `data.trains` 长度 = active 列车数

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_multi_train_step.py`:

```python
"""多车步进与 snapshot 输出测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_delayed_spawn_adds_second_train_to_snapshot():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 2
    orch.sim_params.departure_interval = 5.0
    orch.reset()
    orch.start()
    for _ in range(30):
        snap = orch.step_once()
    assert snap is not None
    train_ids = [t["id"] for t in snap["data"]["trains"]]
    assert "TRAIN_01" in train_ids
    assert "TRAIN_02" in train_ids
    assert len(train_ids) == 2


def test_single_train_count_one_unchanged_snapshot_shape(orchestrator):
    orch = orchestrator
    orch.sim_params.train_count = 1
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert len(snap["data"]["trains"]) == 1
    assert len(snap["data"]["signaling"]["controlCommands"]) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_multi_train_step.py -v`

Expected: FAIL — snapshot 始终 1 列车 / 第二车未 spawn

- [ ] **Step 3: 重构 snapshot 支持多车**

扩展 `build_simulation_snapshot`：接受列车列表（每车含 `train_id`, `state`, `forces`, `pantograph_voltage`, `power_demand`），聚合 `power.totalConsumption` / `totalRegeneration`，`signaling.controlCommands` 每车一条。

- [ ] **Step 4: 重构 step_once 多车循环**

将现有单车步进逻辑提取为 `_step_train(run: TrainRun, dt, elapsed) -> StepResult`，`step_once` 内：

1. spawn 检查
2. `active_runs = [r for r in self.trains if r.active]`
3. 对每车调用 `_step_train`
4. 聚合 power / occupancy / signaling_extra
5. `build_simulation_snapshot(...)`

- [ ] **Step 5: 运行测试**

Run: `cd backend && uv run pytest tests/test_multi_train_step.py tests/test_orchestrator.py tests/test_orchestrator_signaling.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/orchestrator.py backend/sim_engine/data/snapshot.py backend/tests/test_multi_train_step.py
git commit -m "feat(orchestrator): 多车步进与 snapshot"
```

---

### Task 4: SIG-07 追踪间隔 enforcement + trainIntervals

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Modify: `backend/sim_engine/data/snapshot.py`
- Create: `backend/tests/test_sig07_following.py`

**Interfaces:**
- Consumes: `sim_engine.signaling.train_following.is_interval_safe(ahead_pos, rear_pos, min_interval)`
- Produces:
  - 步进中对后方列车：间隔不足 → `ControlCommands(emergency_brake=True)`
  - snapshot `signaling.trainIntervals[]` 字段

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_sig07_following.py`:

```python
"""SIG-07 追踪间隔 enforcement 测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_interval_violation_triggers_eb_on_following_train():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 2
    orch.sim_params.departure_interval = 0.0
    orch.sim_params.signal.following_min_interval = 500.0
    orch.reset()
    orch.trains[0].active = True
    orch.trains[1].active = True
    orch.trains[0].state.position = 2000.0
    orch.trains[0].state.speed = 40.0
    orch.trains[1].state.position = 1600.0  # 间隔 400m < 500m
    orch.trains[1].state.speed = 40.0
    orch.start()
    snap = orch.step_once()
    cmds = {c["trainId"]: c for c in snap["data"]["signaling"]["controlCommands"]}
    assert cmds["TRAIN_02"]["emergencyBrake"] is True
    intervals = snap["data"]["signaling"]["trainIntervals"]
    assert any(i["trainId"] == "TRAIN_02" and i["safe"] is False for i in intervals)


def test_single_train_no_train_intervals(orchestrator):
    orch = orchestrator
    orch.sim_params.train_count = 1
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert snap["data"]["signaling"].get("trainIntervals", []) == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_sig07_following.py -v`

Expected: FAIL

- [ ] **Step 3: 在 _step_train 前计算 leading_pos 并 enforcement**

对每辆 active 列车，找同向更高 position 的最近前车；调用 `is_interval_safe(leading_pos, run.state.position, min_interval)`；False 则 EB。构建 `trainIntervals` 列表写入 `signaling_extra`。

- [ ] **Step 4: 运行测试**

Run: `cd backend && uv run pytest tests/test_sig07_following.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/orchestrator.py backend/sim_engine/data/snapshot.py backend/tests/test_sig07_following.py
git commit -m "feat(signaling): SIG-07 追踪间隔 enforcement"
```

---

### Task 5: ATP MA 受前车位置约束

**Files:**
- Modify: `backend/sim_engine/signaling/atp.py`
- Modify: `backend/sim_engine/orchestrator.py`
- Create: `backend/tests/test_atp_leading_ma.py`

**Interfaces:**
- Produces:
  - `ATPController.ma_end_chainage(train_position, target_chainage, leading_chainage: float | None = None) -> float`
  - 若 `leading_chainage` 给定：`ma_end = min(target, leading_chainage - safety_distance)`，且 `>= train_position`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_atp_leading_ma.py`:

```python
"""ATP MA 前车约束测试。"""

from __future__ import annotations

from sim_engine.core.config import AtpConfig
from sim_engine.signaling.atp import ATPController


def test_ma_end_capped_by_leading_train():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    ma_end = atp.ma_end_chainage(
        train_position=1000.0,
        target_station_chainage=3000.0,
        leading_chainage=1500.0,
    )
    assert ma_end == 1200.0  # 1500 - 300


def test_ma_end_without_leading_uses_target():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    ma_end = atp.ma_end_chainage(1000.0, 3000.0, None)
    assert ma_end == 3000.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_atp_leading_ma.py -v`

Expected: FAIL — 未知参数 `leading_chainage`

- [ ] **Step 3: 扩展 atp.py 并在 orchestrator 传入 leading**

- [ ] **Step 4: 运行全量 signaling 相关测试**

Run: `cd backend && uv run pytest tests/test_atp_leading_ma.py tests/test_orchestrator_signaling.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/atp.py backend/sim_engine/orchestrator.py backend/tests/test_atp_leading_ma.py
git commit -m "feat(signaling): ATP MA 前车约束"
```

---

### Task 6: SimulationManager API 与生命周期对齐

**Files:**
- Modify: `backend/sim_engine/services/simulation_manager.py`
- Create: `backend/tests/test_simulation_manager_multi_train.py`

**Interfaces:**
- Produces:
  - `get_status()["trainCount"]` ← `sim_params.train_count`
  - `get_params()["signal"]["departureInterval"]` ← `sim_params.departure_interval`
  - `update_config` 支持 `simulation.trainCount` / `simulation.departureInterval`
  - `_run_loop` 结束：全部 spawn 且全部到终点停稳

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_simulation_manager_multi_train.py`:

```python
"""SimulationManager 多车 API 测试。"""

from __future__ import annotations

import pytest

from sim_engine.services.simulation_manager import SimulationManager
from sim_engine.ws.manager import WebSocketConnectionManager


@pytest.fixture
def manager():
    return SimulationManager(WebSocketConnectionManager())


def test_get_status_train_count(manager):
    manager.orchestrator.sim_params.train_count = 3
    status = manager.get_status()
    assert status["trainCount"] == 3


def test_get_params_departure_interval(manager):
    manager.orchestrator.sim_params.departure_interval = 90.0
    params = manager.get_params()
    assert params["signal"]["departureInterval"] == 90.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_simulation_manager_multi_train.py -v`

Expected: FAIL — `trainCount` 硬编码 1

- [ ] **Step 3: 实现 API 与 _run_loop 多车结束条件**

- [ ] **Step 4: 运行测试**

Run: `cd backend && uv run pytest tests/test_simulation_manager_multi_train.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/services/simulation_manager.py backend/tests/test_simulation_manager_multi_train.py
git commit -m "feat(api): 多车配置 API 对齐"
```

---

### Task 7: 全量回归与验收

**Files:**
- Modify: `backend/tests/test_orchestrator.py`（如需要：部分测试显式 `train_count=1`）
- 可选: `backend/tests/conftest.py` fixture 强制单车

- [ ] **Step 1: 确保 conftest orchestrator fixture 使用 train_count=1**

在 `conftest.py` 的 `orchestrator` fixture 中：

```python
orch = Orchestrator.from_config_dir()
orch.sim_params.train_count = 1
orch.reset()
return orch
```

避免默认 yaml `train_count=3` 破坏现有测试。

- [ ] **Step 2: 全量 pytest**

Run: `cd backend && uv run pytest -v`

Expected: 全绿（≥286 passed）

- [ ] **Step 3: 手动冒烟（可选）**

启动后端，WebSocket 观察 `train_count=3` 时 `simulation_snapshot.data.trains` 长度随发车递增。

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "test: 多车回归与 fixture 隔离"
```

---

## 计划自检

| 设计需求 | 对应 Task |
|----------|-----------|
| train_count / departure_interval 配置 | Task 1 |
| 多 TrainRun 独立信号链 | Task 2 |
| 延迟发车 + 多车步进 | Task 3 |
| SIG-07 EB + trainIntervals | Task 4 |
| ATP MA 前车约束 | Task 5 |
| REST/WS trainCount API | Task 6 |
| 回归 + conftest 隔离 | Task 7 |

## 执行顺序与依赖

```
Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7
                └─ Task 4 依赖 Task 3 的多车步进
                └─ Task 5 可与 Task 4 并行，但建议顺序 4→5
```

## 执行方式（待你确认）

**Plan 已保存至** `docs/superpowers/plans/2026-07-12-single-direction-multi-train-plan.md`  
**设计已保存至** `docs/superpowers/specs/2026-07-12-single-direction-multi-train-design.md`

两种执行方式：

1. **Subagent-Driven（推荐）** — 每 Task 派生子 agent，Task 间人工/AI 审查
2. **Inline Execution** — 本会话按 Task 1→7 逐步执行，每 Task 完成后暂停确认

**请确认：**
1. 设计文档是否有需修改之处？
2. 选择哪种执行方式？确认后从 **Task 1** 开始（不再一次性全做完）。
