# ATS recover 赶点站停 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ATS 默认站停策略从 `extend`（晚点加站停）改为 `recover`（晚点缩短赶点），消除 continuous 多车超长站停与后车追踪制动。

**Architecture:** 在 `ATSController.adjust_dwell` 增加 `recover` 分支；`Timetable` 补充 `planned_departure` 查询；配置默认切到 `recover`；原 `extend` 保留作显式兼容。

**Tech Stack:** Python 3.10+, pytest, PyYAML

## Global Constraints

- 参数经 YAML/`AtsConfig` 注入，不硬编码魔法数到业务分支以外的配置默认值（NFR-07）
- 无新增第三方依赖（NFR-06）
- 提交：`feat(signaling): …` / `test(signaling): …` / `chore(config): …`，≤50 汉字，caveman-commit
- 不修改 `docs/需求文档.md` 争议正文（向组长报告）；本设计文档为准
- 从 `dev` 迁出 `feat/ats-recover-dwell`，合并用 rebase + `--ff-only`

---

### Task 1: Timetable.planned_departure + ATS recover 单测（先失败）

**Files:**
- Modify: `backend/sim_engine/signaling/models.py`
- Modify: `backend/tests/test_ats.py`
- Test: `backend/tests/test_ats.py`

**Interfaces:**
- Produces: `Timetable.planned_departure(station_id: str) -> float | None`
- Produces: `ATSController.adjust_dwell` 在 `dwell_adjust_mode=="recover"` 下的行为（本任务先写测试）

- [ ] **Step 1: 扩展 test_ats.py**

将 `test_ats.py` 替换/追加为完整覆盖（保留旧 extend 行为为显式配置）：

```python
"""ATSController 单元测试（recover 默认 + extend 兼容）。"""

from __future__ import annotations

from sim_engine.core.config import AtsConfig
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.models import Timetable, TimetableEntry


def _tt():
    return Timetable("TRAIN_01", [
        TimetableEntry("ST02", planned_arrival=100.0, planned_departure=130.0),
    ])


def test_planned_departure_lookup():
    tt = _tt()
    assert tt.planned_departure("ST02") == 130.0
    assert tt.planned_departure("ST99") is None


def test_on_time_dwell_unchanged():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover"), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=100.0)
    assert adjusted == 30.0
    assert dev is not None
    assert dev.delay_arrival == 0.0


def test_late_shortens_dwell_recover():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", min_dwell_time=15.0), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 15.0
    assert dev.delay_arrival == 30.0


def test_late_clamped_by_min_dwell():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", min_dwell_time=15.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=200.0)
    assert adjusted == 15.0


def test_early_holds_to_planned_departure():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover", max_dwell_time=300.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=80.0)
    # planned_departure - actual = 50
    assert adjusted == 50.0


def test_extend_mode_still_adds_delay():
    ats = ATSController(AtsConfig(dwell_adjust_mode="extend"), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 60.0


def test_unknown_station_returns_nominal():
    ats = ATSController(AtsConfig(dwell_adjust_mode="recover"), _tt())
    adjusted, dev = ats.adjust_dwell("ST99", nominal_dwell=25.0, actual_arrival=100.0)
    assert adjusted == 25.0
    assert dev is None
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && python -m pytest tests/test_ats.py -v --tb=short`

Expected: FAIL — `planned_departure` 缺失 和/或 recover 行为不符合

- [ ] **Step 3: 实现 Timetable.planned_departure**

在 `models.py` 的 `Timetable` 中、`planned_arrival` 旁增加：

```python
def planned_departure(self, station_id: str) -> float | None:
    for e in self.entries:
        if e.station_id == station_id:
            return e.planned_departure
    return None
```

- [ ] **Step 4: 实现 ats.py recover**

将 `ats.py` 改为：

```python
"""ATS 运行图调度（SIG-06：recover 赶点 / extend 兼容）。"""

from __future__ import annotations

from sim_engine.core.config import AtsConfig
from sim_engine.signaling.models import Timetable, TimetableDeviation


class ATSController:
    def __init__(self, config: AtsConfig, timetable: Timetable):
        self._config = config
        self._timetable = timetable
        self.last_deviation: TimetableDeviation | None = None

    def adjust_dwell(
        self,
        station_id: str,
        nominal_dwell: float,
        actual_arrival: float,
    ) -> tuple[float, TimetableDeviation | None]:
        planned = self._timetable.planned_arrival(station_id)
        if planned is None:
            return nominal_dwell, None

        delay = actual_arrival - planned
        mode = self._config.dwell_adjust_mode
        if mode == "recover":
            if delay > 0:
                adjusted = nominal_dwell - delay
            else:
                planned_dep = self._timetable.planned_departure(station_id)
                if planned_dep is not None:
                    adjusted = max(nominal_dwell, planned_dep - actual_arrival)
                else:
                    adjusted = nominal_dwell - delay
        elif mode == "extend":
            adjusted = nominal_dwell + max(0.0, delay)
        else:
            adjusted = nominal_dwell

        adjusted = max(self._config.min_dwell_time, min(self._config.max_dwell_time, adjusted))
        dev = TimetableDeviation(
            train_id=self._timetable.train_id,
            station_id=station_id,
            delay_arrival=delay,
            nominal_dwell=nominal_dwell,
            adjusted_dwell=adjusted,
        )
        self.last_deviation = dev
        return adjusted, dev
```

- [ ] **Step 5: 运行确认通过**

Run: `cd backend && python -m pytest tests/test_ats.py -v --tb=short`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/signaling/models.py backend/sim_engine/signaling/ats.py backend/tests/test_ats.py
git commit -m "feat(signaling): ATS recover 赶点站停"
```

---

### Task 2: 默认配置切到 recover + 适配依赖测试

**Files:**
- Modify: `backend/sim_engine/config/signal.yaml`
- Modify: `backend/sim_engine/core/config.py`
- Modify: `backend/tests/test_signal_models.py`
- Modify: `backend/tests/test_signaling.py`
- Modify: `backend/tests/test_orchestrator_signaling.py`

**Interfaces:**
- Consumes: Task 1 的 `recover` / `extend` 行为
- Produces: 默认 `dwell_adjust_mode="recover"`

- [ ] **Step 1: 改配置默认**

`signal.yaml`：

```yaml
  ats:
    dwell_adjust_mode: recover      # 赶点：晚点缩短 / 早点等到发车点
    min_dwell_time: 15
    max_dwell_time: 300
```

`config.py` 中 `AtsConfig.dwell_adjust_mode` 默认与 `load` 回退改为 `"recover"`。

- [ ] **Step 2: 适配测试**

1. `test_signal_models.py`：断言 `dwell_adjust_mode == "recover"`（配置样例同步改）。
2. `test_signaling.py`：
   - `test_late_arrival_extends_dwell` → 改名为 `test_late_arrival_shortens_dwell_recover`，期望 `dwell_remaining == 15.0`（或 `AtsConfig` 的 `min_dwell`）；`make_ctrl_with_ats` 使用默认 recover。
   - 若需保留 extend 行为，另加 `AtsConfig(dwell_adjust_mode="extend")` 的用例。
3. `test_orchestrator_signaling.py` 中 `test_late_arrival_timetable_deviation_in_snapshot`：
   - 晚点时改为断言 `adjustedDwell <= nominalDwell`（赶点），且 `delayArrival > 0`。
   - 删除 `adjustedDwell > nominalDwell` / `dwell_remaining > nominalDwell`。

- [ ] **Step 3: 运行相关测试**

Run:

```bash
cd backend
python -m pytest tests/test_ats.py tests/test_signal_models.py tests/test_signaling.py::test_late_arrival_shortens_dwell_recover tests/test_signaling.py::test_on_time_arrival_dwell_unchanged_with_ats tests/test_orchestrator_signaling.py -v --tb=short
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/sim_engine/config/signal.yaml backend/sim_engine/core/config.py backend/tests/test_signal_models.py backend/tests/test_signaling.py backend/tests/test_orchestrator_signaling.py
git commit -m "chore(config): ATS 默认 recover 并适配测试"
```

---

### Task 3: continuous 集成验收（防雪崩）

**Files:**
- Modify: `backend/tests/test_continuous_dispatch_integration.py`

**Interfaces:**
- Consumes: 默认 `recover` 的 Orchestrator

- [ ] **Step 1: 追加集成测试**

在 `test_continuous_dispatch_integration.py` 末尾追加：

```python
def test_continuous_dwell_not_capped_massively():
    """recover 下长时间运行不应大量出现顶满 max_dwell 的站停。"""
    orch = Orchestrator.from_config_dir()
    assert orch.sim_params.signal.ats.dwell_adjust_mode == "recover"
    orch.sim_params.total_time = 2500.0
    orch.reset()
    orch.start()
    capped = 0
    samples = 0
    max_dwell = orch.sim_params.signal.ats.max_dwell_time
    for _ in range(25000):
        orch.step_once()
        for run in orch.trains:
            if not run.active:
                continue
            d = run.ats.last_deviation
            if d is None:
                continue
            samples += 1
            if d.adjusted_dwell >= max_dwell - 1e-6 and d.delay_arrival > 0:
                capped += 1
    # 允许偶然几次贴顶，但不允许多数偏离记录顶满
    assert samples > 0
    assert capped / samples < 0.05, f"capped={capped} samples={samples}"
```

- [ ] **Step 2: 运行集成测试**

Run: `cd backend && python -m pytest tests/test_continuous_dispatch_integration.py::test_continuous_dwell_not_capped_massively -v --tb=short`

Expected: PASS（若偶发失败，可把阈值从 `0.05` 调到 `0.10` 并记录原因，但不得回到 extend 行为）

- [ ] **Step 3: 全量回归**

Run: `cd backend && python -m pytest -q --tb=line`

Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_continuous_dispatch_integration.py
git commit -m "test(signaling): continuous 站停防雪崩验收"
```

---

## 自审检查

- [x] 设计文档每条规则均有 Task（recover / 配置默认 / 测试 / 验收）
- [x] 无 TBD 占位
- [x] `planned_departure` 在 Task 1 定义，ats 中使用一致
- [x] 依赖 extend 的测试改为显式 mode 或改为 recover 断言
- [x] 非本轮范围（时刻表重标定、派车闸门）未写入实现步骤
