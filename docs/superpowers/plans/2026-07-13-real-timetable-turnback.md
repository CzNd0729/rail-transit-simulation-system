# 真实时刻表 + 持续派车 + 折返交路 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用北京地铁 4 号线手工 YAML 运行图驱动持续派车（高峰 150s / 平峰 270s），线路因 SIG-07 追踪间隔饱和时阻塞补发；列车终到后经道岔折返并执行上行 leg。

**Architecture:** 扩展 `Timetable` v2 加载 leg 模板；新建 `FleetScheduler`（headway 时钟 + 始发站容量闸门 + 动态 `TrainRun`）；新建 `TurnbackController`（折返状态机 + `SwitchManager`）；`Orchestrator` 在 continuous 模式下空车队启动、每步先调度再步进；`SimulationManager` 仅以 `total_time` 结束仿真。

**Tech Stack:** Python 3.10+, dataclass, PyYAML, pytest, 现有 `Orchestrator` / `SwitchManager` / `ATSController` / `train_following`

**设计文档：** `docs/superpowers/specs/2026-07-13-real-timetable-turnback-design.md`

## Global Constraints

- 所有可调参数通过 YAML 注入，不得硬编码（NFR-07）
- 无额外非必要第三方依赖（NFR-06）
- 模块间通过 dataclass 契约交互；禁止跨模块 import 内部实现（`backend/CLAUDE.md`）
- 对外速度 km/h，位置 m，时间步长 dt 为秒
- 高峰 `headway_s: 150`、折返 `turnback_time_s: 150`、平峰 `headway_s: 270`
- 派车阻塞时**保留班次、空隙满足后立即补发**（不跳班）
- `dispatch.mode: fixed` + `train_count=1` 回归行为必须与现有 MVP 一致
- 文档冲突（SIG-16 迭代三归属）不得自行修改 `docs/需求文档.md`，需提醒组长
- 提交格式：`feat(<scope>): <中文描述>`（≤50 字符）；**一 Task 一提交**

---

## File Map

| 文件 | 职责 |
|------|------|
| `signaling/models.py` | `TimetableLegTemplate`、`DispatchConfig`、`ServiceTimetable` |
| `signaling/timetable_loader.py` | v2 YAML 加载、旧格式兼容、`build_legs_for_train()` |
| `signaling/fleet_scheduler.py` | **新建** — 持续派车、始发站 clearance、`origin_clearance_ok()` |
| `signaling/turnback.py` | **新建** — 折返状态机、道岔联动、换向 |
| `config/timetable.yaml` | 高峰 v2 全线 leg 模板 + `dispatch.continuous` |
| `config/timetable_offpeak.yaml` | 平峰副本（`headway_s: 270`） |
| `config/simulation.yaml` | `bidirectional: false`；注明 continuous 忽略 `train_count` |
| `orchestrator.py` | 接入 scheduler/turnback；扩展 `TrainRun` |
| `services/simulation_manager.py` | 结束条件改为仅 `total_time`（continuous 模式） |
| `data/snapshot.py` | 可选 `dispatchStatus` / `legIndex` 字段 |
| `tests/test_timetable_v2_loader.py` | loader 单测 |
| `tests/test_fleet_scheduler.py` | 派车 / 阻塞 / 补发单测 |
| `tests/test_turnback.py` | 折返状态机单测 |
| `tests/test_continuous_dispatch_integration.py` | 端到端集成 |

---

### Task 1: Timetable v2 数据模型

**Files:**
- Modify: `backend/sim_engine/signaling/models.py`
- Create: `backend/tests/test_timetable_v2_loader.py`（仅模型/类型测试前半）

**Interfaces:**
- Produces:
  - `TimetableLegTemplate(direction, terminal_station, entries)`
  - `DispatchConfig(mode, origin_station, initial_direction, first_departure_s, headway_s, headway_pattern_s, max_active_trains, min_origin_clearance_m)`
  - `ServiceTimetable(meta, dispatch, leg_templates, trip_leg_names)`
  - `Timetable.with_absolute_times(base_elapsed: float) -> Timetable`（相对 leg → 绝对时刻）

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_timetable_v2_loader.py`:

```python
"""Timetable v2 数据模型与加载测试。"""

from __future__ import annotations

from sim_engine.signaling.models import DispatchConfig, TimetableEntry


def test_dispatch_config_defaults():
    cfg = DispatchConfig()
    assert cfg.mode == "continuous"
    assert cfg.headway_s == 150.0
    assert cfg.min_origin_clearance_m == 500.0


def test_timetable_absolute_offset():
    from sim_engine.signaling.models import Timetable

    tt = Timetable(
        train_id="TRAIN_01",
        entries=[
            TimetableEntry("ST01", planned_arrival=0.0, planned_departure=35.0),
            TimetableEntry("ST02", planned_arrival=114.0, planned_departure=139.0),
        ],
    )
    abs_tt = tt.with_absolute_times(300.0)
    assert abs_tt.planned_arrival("ST01") == 300.0
    assert abs_tt.planned_arrival("ST02") == 414.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_timetable_v2_loader.py::test_dispatch_config_defaults -v`

Expected: FAIL — `DispatchConfig` 未定义

- [ ] **Step 3: 实现模型**

在 `backend/sim_engine/signaling/models.py` 追加：

```python
@dataclass(frozen=True)
class TimetableLegTemplate:
    name: str
    direction: str
    terminal_station: str
    entries: list[TimetableEntry]


@dataclass(frozen=True)
class DispatchConfig:
    mode: str = "continuous"  # continuous | fixed
    origin_station: str = "ST01"
    initial_direction: str = "down"
    first_departure_s: float = 0.0
    headway_s: float = 150.0
    headway_pattern_s: tuple[float, ...] = ()
    max_active_trains: int = 40
    min_origin_clearance_m: float = 500.0


@dataclass(frozen=True)
class ServiceTimetable:
    line_name: str
    turnback_time_s: float
    turnback_switch_down: str
    turnback_switch_up: str
    dispatch: DispatchConfig
    leg_templates: dict[str, TimetableLegTemplate]
    trip_leg_names: tuple[str, ...] = ("down", "up")
```

在 `Timetable` 上增加：

```python
def with_absolute_times(self, base_elapsed: float) -> Timetable:
    return Timetable(
        train_id=self.train_id,
        entries=[
            TimetableEntry(
                e.station_id,
                planned_arrival=e.planned_arrival + base_elapsed,
                planned_departure=e.planned_departure + base_elapsed,
            )
            for e in self.entries
        ],
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_timetable_v2_loader.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/models.py backend/tests/test_timetable_v2_loader.py
git commit -m "feat(signaling): 添加时刻表 v2 数据模型"
```

---

### Task 2: Timetable v2 YAML 加载 + 配置文件

**Files:**
- Modify: `backend/sim_engine/signaling/timetable_loader.py`
- Rewrite: `backend/sim_engine/config/timetable.yaml`
- Create: `backend/sim_engine/config/timetable_offpeak.yaml`
- Modify: `backend/tests/test_timetable_v2_loader.py`

**Interfaces:**
- Consumes: `DispatchConfig`, `ServiceTimetable`, `TimetableLegTemplate` from Task 1
- Produces:
  - `load_service_timetable(path) -> ServiceTimetable`
  - `materialize_trip_timetables(service, train_id) -> list[Timetable]`（down/up 相对时刻表，未加绝对偏移）

- [ ] **Step 1: 写失败测试**

在 `test_timetable_v2_loader.py` 追加：

```python
from pathlib import Path

from sim_engine.signaling.timetable_loader import load_service_timetable, materialize_trip_timetables

CONFIG = Path(__file__).resolve().parents[1] / "sim_engine" / "config"


def test_load_peak_service_timetable():
    svc = load_service_timetable(CONFIG / "timetable.yaml")
    assert svc.dispatch.mode == "continuous"
    assert svc.dispatch.headway_s == 150.0
    assert "down" in svc.leg_templates
    assert len(svc.leg_templates["down"].entries) == 24


def test_materialize_trip_legs():
    svc = load_service_timetable(CONFIG / "timetable.yaml")
    legs = materialize_trip_timetables(svc, "TRAIN_01")
    assert len(legs) == 2
    assert legs[0].planned_arrival("ST24") == 1995.0
    assert legs[1].entries[0].station_id == "ST24"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_timetable_v2_loader.py::test_load_peak_service_timetable -v`

Expected: FAIL — `load_service_timetable` 未定义或 YAML 格式不匹配

- [ ] **Step 3: 实现 loader + 写入 YAML**

在 `timetable_loader.py` 实现 `load_service_timetable()` 与 `materialize_trip_timetables()`；检测旧格式（仅有 `train_id` + `entries`）时包装为 `mode: fixed` 单车。

将 `backend/sim_engine/config/timetable.yaml` 重写为设计文档 §3.1–§3.3 全文（`dispatch.headway_s: 150`，24 站 down/up entries）。

复制为 `timetable_offpeak.yaml`，仅改 `profile: offpeak_reference` 与 `dispatch.headway_s: 270`。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_timetable_v2_loader.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/timetable_loader.py \
        backend/sim_engine/config/timetable.yaml \
        backend/sim_engine/config/timetable_offpeak.yaml \
        backend/tests/test_timetable_v2_loader.py
git commit -m "feat(signaling): 实现 v2 时刻表加载与配置"
```

---

### Task 3: 始发站容量闸门 + FleetScheduler

**Files:**
- Create: `backend/sim_engine/signaling/fleet_scheduler.py`
- Modify: `backend/sim_engine/signaling/__init__.py`
- Create: `backend/tests/test_fleet_scheduler.py`

**Interfaces:**
- Consumes: `ServiceTimetable`, `TrainRun`（Task 4 定义字段）, `train_following.tracking_gap`
- Produces:
  - `origin_clearance_ok(active_runs, origin_chainage, direction, min_clearance_m) -> bool`
  - `FleetScheduler.tick(elapsed, trains, create_run) -> DispatchTickResult`
  - `DispatchTickResult(dispatched: list[TrainRun], blocked: bool, next_departure_time: float)`

**始发站 clearance 规则（下行 ST01）：**

```python
def origin_clearance_ok(
    active_runs: list[TrainRun],
    origin_chainage: float,
    direction: str,
    min_clearance_m: float,
) -> bool:
    """同向列车中，距始发点最近一列的净距须 >= min_clearance_m。"""
    same_dir = [r for r in active_runs if r.active and r.state.direction == direction]
    if not same_dir:
        return True
    if direction == "down":
        nearest_ahead = min(r.state.position for r in same_dir)
        return nearest_ahead >= origin_chainage + min_clearance_m
    nearest_ahead = max(r.state.position for r in same_dir)
    return origin_chainage - nearest_ahead >= min_clearance_m
```

**派车阻塞逻辑（已确认：不跳班）：**

```python
while elapsed >= self._next_departure_time and len(active) < max_active:
    if origin_clearance_ok(...):
        run = create_run(train_id, spawn_time=self._next_departure_time)
        dispatched.append(run)
        self._advance_headway_clock()  # next += headway_s 或 pattern 下一项
    else:
        blocked = True
        break  # 不推进 next_departure_time
```

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_fleet_scheduler.py`：

```python
"""FleetScheduler 持续派车测试。"""

from __future__ import annotations

from dataclasses import dataclass

from sim_engine.signaling.fleet_scheduler import FleetScheduler, origin_clearance_ok


@dataclass
class _FakeRun:
    active: bool
    direction: str
    position: float


def test_origin_clearance_empty_line():
    assert origin_clearance_ok([], 0.0, "down", 500.0) is True


def test_origin_clearance_blocked_down():
    runs = [_FakeRun(True, "down", 300.0)]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is False


def test_origin_clearance_ok_down():
    runs = [_FakeRun(True, "down", 600.0)]
    assert origin_clearance_ok(runs, 0.0, "down", 500.0) is True


def test_scheduler_dispatches_on_headway():
    # 使用最小 ServiceTimetable stub；验证 t=0 与 t=150 派两班
    ...


def test_scheduler_holds_when_blocked_then_catches_up():
    # 模拟前方 300m 有车阻塞；推进到 600m 后补发，且 next_departure 未跳过
    ...
```

（`test_scheduler_*` 在 Step 3 用完整 stub 实现。）

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_fleet_scheduler.py -v`

Expected: FAIL — 模块不存在

- [ ] **Step 3: 实现 FleetScheduler**

创建 `fleet_scheduler.py`，导出 `origin_clearance_ok`、`FleetScheduler`、`DispatchTickResult`。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_fleet_scheduler.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/fleet_scheduler.py \
        backend/sim_engine/signaling/__init__.py \
        backend/tests/test_fleet_scheduler.py
git commit -m "feat(signaling): 添加持续派车调度器"
```

---

### Task 4: TrainRun 扩展 + Orchestrator 接入 FleetScheduler

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Modify: `backend/sim_engine/config/simulation.yaml`
- Modify: `backend/tests/test_multi_train_step.py`
- Create: `backend/tests/test_continuous_dispatch_integration.py`

**Interfaces:**
- Consumes: `FleetScheduler`, `load_service_timetable`, `materialize_trip_timetables` from Task 2–3
- Produces:
  - `TrainRun.leg_index`, `TrainRun.legs`, `TrainRun.turnback_state`
  - `Orchestrator._service_timetable: ServiceTimetable`
  - continuous 模式 `reset()` 后 `trains == []`；`step_once()` 开头调用 `FleetScheduler.tick`

- [ ] **Step 1: 写失败集成测试**

Create `backend/tests/test_continuous_dispatch_integration.py`:

```python
"""持续派车集成测试。"""

from __future__ import annotations

from sim_engine.orchestrator import Orchestrator


def test_continuous_first_train_at_zero():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert snap is not None
    assert snap["data"]["trains"][0]["id"] == "TRAIN_01"
    assert snap["data"]["trains"][0]["direction"] == "down"


def test_continuous_second_train_at_150s():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    snap = None
    for _ in range(1500):  # 150s / 0.1s
        snap = orch.step_once()
    ids = [t["id"] for t in snap["data"]["trains"]]
    assert "TRAIN_01" in ids
    assert "TRAIN_02" in ids


def test_continuous_dispatch_count_grows():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 600.0
    orch.reset()
    orch.start()
    for _ in range(6000):
        orch.step_once()
    assert len(orch.trains) >= 4
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_continuous_dispatch_integration.py -v`

Expected: FAIL

- [ ] **Step 3: 改造 Orchestrator**

要点：

1. `from_config_dir` 加载 `load_service_timetable(timetable.yaml)` 存入 `_service_timetable`。
2. `dispatch.mode == "continuous"` 时 `_init_trains()` 设 `self.trains = []`，并 `self._fleet_scheduler.reset()`。
3. `dispatch.mode == "fixed"` 时保留现有 `train_count` × `departure_interval` 逻辑。
4. 新增 `_create_train_run(train_id, spawn_time) -> TrainRun`：`materialize_trip_timetables` → 首 leg 绑定 ATS → `active=True`。
5. `step_once()` 开头：

```python
if self._service_timetable.dispatch.mode == "continuous":
    active = [r for r in self.trains if r.active]
    result = self._fleet_scheduler.tick(
        self.clock.elapsed,
        active_runs=active,
        create_run=self._create_train_run,
    )
    self.trains.extend(result.dispatched)
```

6. `simulation.yaml` 设 `bidirectional: false`。

- [ ] **Step 4: 更新旧多车测试**

`test_multi_train_step.py` 中依赖 `train_count=3` 的用例：在 `reset()` 前设 `orch._service_timetable` 为 fixed 模式 stub，或 `dispatch.mode: fixed` 临时配置。

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_continuous_dispatch_integration.py tests/test_multi_train_step.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/orchestrator.py \
        backend/sim_engine/config/simulation.yaml \
        backend/tests/test_continuous_dispatch_integration.py \
        backend/tests/test_multi_train_step.py
git commit -m "feat(orchestrator): 接入持续派车模式"
```

---

### Task 5: TurnbackController + 道岔联动

**Files:**
- Create: `backend/sim_engine/signaling/turnback.py`
- Modify: `backend/sim_engine/orchestrator.py`
- Create: `backend/tests/test_turnback.py`

**Interfaces:**
- Consumes: `SwitchManager`, `ServiceTimetable.turnback_time_s`, `TrainRun.legs`
- Produces:
  - `TurnbackController.step(run, elapsed, switch_manager) -> bool`（本步是否占用折返）
  - 状态：`None | "switching" | "dwelling" | "reversing"`
  - 完成后：`run.leg_index += 1`，`run.state.direction` 翻转，`run.ats` 绑定 `legs[leg_index].with_absolute_times(elapsed)`

- [ ] **Step 1: 写失败测试**

```python
"""折返状态机测试。"""

from sim_engine.signaling.turnback import TurnbackController
from sim_engine.track.switch import SwitchManager
from sim_engine.track.models import Switch


def test_turnback_triggers_switch_at_terminal():
    switches = [Switch(id="SW04", chainage=18550, switch_type="crossover",
                       normal_direction="main", reverse_direction="siding",
                       lateral_speed_limit=30)]
    mgr = SwitchManager(switches)
    ctrl = TurnbackController(turnback_time_s=150.0, switch_id="SW04")
    # 用 Fake TrainRun 在 ST24 停稳触发
    ...
    assert mgr.query("SW04").state in ("transitioning", "reverse")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && python -m pytest tests/test_turnback.py -v`

Expected: FAIL

- [ ] **Step 3: 实现 TurnbackController**

折返触发条件：

- `run.active` 且 `run.turnback_state is None`
- `run.state.speed < 0.1`
- 当前 leg `terminal_station` 已到达（`three_stage` phase == dwell 且 `_dwell_station_id == terminal`）
- `run.leg_index + 1 < len(run.legs)`

状态推进在 `Orchestrator.step_once` 每车步进后调用。

- [ ] **Step 4: 集成到 orchestrator**

在 `_step_train` 之后或之内调用 `TurnbackController`；换向时：

```python
run.state.direction = "up" if run.state.direction == "down" else "down"
run.signaling.reset(direction=run.state.direction)
run.ats = ATSController(self.sim_params.signal.ats, run.legs[run.leg_index].with_absolute_times(elapsed))
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_turnback.py tests/test_continuous_dispatch_integration.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/signaling/turnback.py \
        backend/sim_engine/orchestrator.py \
        backend/tests/test_turnback.py
git commit -m "feat(signaling): 实现折返状态机与道岔联动"
```

---

### Task 6: SimulationManager 结束条件 + API 对齐

**Files:**
- Modify: `backend/sim_engine/services/simulation_manager.py`
- Modify: `backend/tests/test_continuous_dispatch_integration.py`

**Interfaces:**
- continuous 模式：`_run_loop` 仅在 `elapsed >= total_time` 或手动 stop 时结束；**不**调用 `_all_trains_finished` 作为终止条件
- `get_status().trainCount` → 当前 `len(orch.trains)`（动态）或 `len(active)`
- `get_params()` 暴露 `timetableProfile`、`headwayS`（从 `ServiceTimetable`）

- [ ] **Step 1: 写失败测试**

```python
def test_simulation_runs_until_total_time_not_all_trains_finished():
  orch = Orchestrator.from_config_dir()
  orch.sim_params.total_time = 30.0
  orch.reset()
  orch.start()
  for _ in range(400):
      orch.step_once()
  assert orch.clock.elapsed >= 30.0
  # 不要求所有车到达终点
```

- [ ] **Step 2–5: 实现、测试、Commit**

```bash
git commit -m "fix(sim): continuous 模式按 total_time 结束"
```

---

### Task 7: 回归测试 + 饱和场景验收

**Files:**
- Modify: `backend/tests/test_continuous_dispatch_integration.py`
- Modify: `backend/tests/test_signaling.py`（如有 timetable 相关回归）

- [ ] **Step 1: 饱和阻塞补发测试**

```python
def test_dispatch_blocks_when_origin_occupied_then_resumes():
    """前车距始发 <500m 时阻塞；前车驶离后补发，且不跳过班次。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    # 推进到应发第 2 班但前方不足 500m：TRAIN_02 延迟出现
    # 记录 _fleet_scheduler.next_departure_time 未跳过 150
    ...
```

- [ ] **Step 2: 折返端到端**

长仿真（`total_time=5000`）断言某车 `direction` 曾变为 `up`，且 `SW04` 曾 `reverse`。

- [ ] **Step 3: fixed 模式回归**

```python
def test_fixed_mode_train_count_fallback():
    # 临时改 dispatch.mode=fixed, train_count=1
    # 行为与 MVP 一致
```

- [ ] **Step 4: 全量 pytest**

Run: `cd backend && python -m pytest -v --tb=short`

Expected: PASS，覆盖率 ≥ 80%

- [ ] **Step 5: Commit**

```bash
git commit -m "test(signaling): 持续派车与折返验收用例"
```

---

### Task 8（可选 P2）: Snapshot / 前端参数展示

**Files:**
- Modify: `backend/sim_engine/data/snapshot.py`
- Modify: `frontend/src/utils/apiAdapter.ts`
- Modify: `frontend/src/components/param/SignalParams.tsx`

- [ ] 在 snapshot `signaling` 增加 `dispatchStatus: { blocked, nextDepartureTime, dispatchedCount }`
- [ ] 参数面板显示 `headway_s` / `profile`（只读），注明 continuous 模式

```bash
git commit -m "feat(frontend): 展示派车调度状态"
```

---

## Plan Self-Review

| Spec 需求 | 对应 Task |
|-----------|-----------|
| TT-01~06 时刻表 v2 + 全线 YAML | Task 1–2 |
| 持续派车 / 饱和阻塞 | Task 3–4, 7 |
| 阻塞不跳班 | Task 3 `FleetScheduler` |
| TB-01~06 折返 + 道岔 | Task 5 |
| OR-01~03 结束条件 / bidirectional | Task 4, 6 |
| AC-01~08 验收 | Task 7 |
| 平峰 timetable_offpeak.yaml | Task 2 |

无 TBD 占位；类型名 `ServiceTimetable` / `FleetScheduler` / `TurnbackController` 全文一致。

---

## 建议分支

```bash
git checkout dev
git pull --rebase origin dev
git checkout -b feat/real-timetable-turnback
```
