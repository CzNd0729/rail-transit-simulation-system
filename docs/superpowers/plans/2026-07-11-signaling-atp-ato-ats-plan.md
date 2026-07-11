# 信号后端 SIG-04/05/06 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在单列车 MVP 上实现 ATP 安全包络（SIG-04）、ATO 模块化（SIG-05）、ATS 延长站停调整（SIG-06）；SIG-07 多车追踪本计划仅预留配置与接口占位。

**Architecture:** 保留 `ThreeStageController` 作为阶段机；制动微调逻辑抽离到 `ATOController`；每步在编排器中 `three_stage → atp.check → manual_drive` 串联；到站时 `ATSController` 按策略 B（extend）计算 `dwell_remaining`；snapshot 输出 `runningPhase`、`speedLimits`、`maProfile`、`timetableDeviation`。

**Tech Stack:** Python 3.10+, dataclass, PyYAML, pytest, 现有 `PIDController` / `Orchestrator` / `build_simulation_snapshot`

## Global Constraints

- 所有可调参数通过 YAML 注入，不得硬编码（NFR-07）
- 无额外非必要第三方依赖（NFR-06）
- 模块间通过 dataclass 契约交互；禁止跨模块 import 内部实现（`backend/CLAUDE.md`）
- 对外速度单位 km/h，位置 m，时间步长 dt 为秒
- 本计划范围：**单列车**；SIG-07 不做多车编排器改造
- ATS 策略 B：**晚点后延长站停**（`adjusted = nominal + max(0, delay)`），早点不压缩
- 提交格式：`feat(signaling): <中文描述>`（≤50 字符，caveman-commit）

## File Map

| 文件 | 职责 |
|------|------|
| `signaling/models.py` | `SafetyStatus`, `MaProfile`, `Timetable`, `TimetableDeviation` |
| `signaling/ato.py` | `ATOController`：制动 PID 微调 + 制动曲线目标速度 |
| `signaling/atp.py` | `ATPController`：超速检测 + 单列车 MA 终点（下一目标站） |
| `signaling/ats.py` | `ATSController`：策略 B 站停调整 + 偏离记录 |
| `signaling/train_following.py` | SIG-07 占位（常量 + TODO，本迭代不 enforcement） |
| `signaling/three_stage.py` | 阶段机；调用 ATO/ATS |
| `core/config.py` | `SignalConfig`, `AtpConfig`, `AtsConfig` 加载 |
| `config/simulation.yaml` | `signal_mode`, `atp`, `ats`, `following` |
| `config/timetable.yaml` | 单列车计划时刻（MVP） |
| `orchestrator.py` | ATP 叠加 + snapshot 扩展字段 |
| `data/snapshot.py` | signaling 段字段扩展 |

---

### Task 1: 信号配置与数据模型

**Files:**
- Create: `backend/sim_engine/signaling/models.py`
- Modify: `backend/sim_engine/core/config.py`
- Modify: `backend/sim_engine/config/simulation.yaml`
- Create: `backend/tests/test_signal_models.py`

**Interfaces:**
- Produces:
  - `SafetyStatus` enum: `NORMAL`, `EMERGENCY_BRAKE`
  - `@dataclass MaProfile: train_id, ma_end_chainage, safety_distance`
  - `@dataclass TimetableEntry: station_id, planned_arrival, planned_departure`
  - `@dataclass Timetable: train_id, entries: list[TimetableEntry]`
  - `@dataclass TimetableDeviation: train_id, station_id, delay_arrival, nominal_dwell, adjusted_dwell`
  - `@dataclass AtpConfig: safety_distance=300.0, overspeed_margin=0.05`
  - `@dataclass AtsConfig: dwell_adjust_mode="extend", min_dwell_time=15.0, max_dwell_time=300.0`
  - `@dataclass SignalConfig: mode="three_stage", atp, ats, following_min_interval=500.0`
  - `SimulationParams.signal: SignalConfig`

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_signal_models.py`:

```python
"""signaling.models 与 SignalConfig 加载测试。"""

from __future__ import annotations

from sim_engine.core.config import load_simulation_params
from sim_engine.signaling.models import (
    AtsConfig,
    AtpConfig,
    SafetyStatus,
    Timetable,
    TimetableEntry,
)


def test_safety_status_values():
    assert SafetyStatus.NORMAL.value == "normal"
    assert SafetyStatus.EMERGENCY_BRAKE.value == "emergency_brake"


def test_timetable_entry_fields():
    e = TimetableEntry(station_id="ST02", planned_arrival=120.0, planned_departure=150.0)
    assert e.station_id == "ST02"


def test_load_signal_config_from_yaml(tmp_path):
    yaml_text = """
simulation:
  signal_mode: atp_ato
  atp:
    safety_distance: 300
    overspeed_margin: 0.05
  ats:
    dwell_adjust_mode: extend
    min_dwell_time: 15
    max_dwell_time: 300
  following:
    min_interval: 500
"""
    p = tmp_path / "simulation.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    params = load_simulation_params(p)
    assert params.signal.mode == "atp_ato"
    assert params.signal.atp.safety_distance == 300.0
    assert params.signal.ats.dwell_adjust_mode == "extend"
    assert params.signal.following_min_interval == 500.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_signal_models.py -v`

Expected: FAIL — `ModuleNotFoundError: sim_engine.signaling.models`

- [ ] **Step 3: 实现 models.py**

Create `backend/sim_engine/signaling/models.py`:

```python
"""信号系统数据模型（ATP/ATS/时刻表）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SafetyStatus(str, Enum):
    NORMAL = "normal"
    EMERGENCY_BRAKE = "emergency_brake"


@dataclass(frozen=True)
class MaProfile:
    train_id: str
    ma_end_chainage: float
    safety_distance: float


@dataclass(frozen=True)
class TimetableEntry:
    station_id: str
    planned_arrival: float
    planned_departure: float


@dataclass
class Timetable:
    train_id: str
    entries: list[TimetableEntry] = field(default_factory=list)

    def planned_arrival(self, station_id: str) -> float | None:
        for e in self.entries:
            if e.station_id == station_id:
                return e.planned_arrival
        return None


@dataclass(frozen=True)
class TimetableDeviation:
    train_id: str
    station_id: str
    delay_arrival: float
    nominal_dwell: float
    adjusted_dwell: float


@dataclass
class AtpConfig:
    safety_distance: float = 300.0
    overspeed_margin: float = 0.05


@dataclass
class AtsConfig:
    dwell_adjust_mode: str = "extend"
    min_dwell_time: float = 15.0
    max_dwell_time: float = 300.0


@dataclass
class SignalConfig:
    mode: str = "three_stage"
    atp: AtpConfig = field(default_factory=AtpConfig)
    ats: AtsConfig = field(default_factory=AtsConfig)
    following_min_interval: float = 500.0
```

- [ ] **Step 4: 扩展 core/config.py**

在 `SimulationParams` 增加 `signal: SignalConfig = field(default_factory=SignalConfig)`，新增 `_load_signal_params(data)` 读取：

```yaml
signal_mode: three_stage   # 或 atp_ato
atp:
  safety_distance: 300
  overspeed_margin: 0.05
ats:
  dwell_adjust_mode: extend
  min_dwell_time: 15
  max_dwell_time: 300
following:
  min_interval: 500
```

在 `load_simulation_params()` 中调用 `_load_signal_params(data)`。

- [ ] **Step 5: 更新 simulation.yaml**

在 `backend/sim_engine/config/simulation.yaml` 的 `simulation:` 下追加上述块（值与 models 默认一致）。

- [ ] **Step 6: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_signal_models.py -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/sim_engine/signaling/models.py backend/sim_engine/core/config.py backend/sim_engine/config/simulation.yaml backend/tests/test_signal_models.py
git commit -m "feat(signaling): 信号配置与数据模型"
```

---

### Task 2: ATOController（SIG-05）

**Files:**
- Create: `backend/sim_engine/signaling/ato.py`
- Modify: `backend/sim_engine/signaling/__init__.py`
- Create: `backend/tests/test_ato.py`

**Interfaces:**
- Consumes: `PIDController` from `signaling/pid_controller.py`
- Produces:
  - `class ATOController:` with `__init__(self, kp_brake: float, comfort_decel: float)`
  - `def braking_trim(self, speed_kmh: float, remaining_m: float) -> float` → 返回 `[0,1]` 制动级位修正后的 ff+trim
  - `def target_speed_on_curve(self, remaining_m: float) -> float` → km/h

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_ato.py`:

```python
"""ATOController 单元测试。"""

from __future__ import annotations

from sim_engine.signaling.ato import ATOController


def test_target_speed_zero_at_station():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    assert ato.target_speed_on_curve(0.0) == 0.0


def test_target_speed_positive_before_station():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    v = ato.target_speed_on_curve(100.0)
    assert v > 0.0


def test_braking_trim_increases_when_overspeed():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    remaining = 200.0
    target = ato.target_speed_on_curve(remaining)
    low = ato.compute_brake_level(speed_kmh=target * 0.5, remaining_m=remaining)
    high = ato.compute_brake_level(speed_kmh=target * 1.5, remaining_m=remaining)
    assert high >= low
    assert 0.0 <= high <= 1.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_ato.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 ato.py**

Create `backend/sim_engine/signaling/ato.py`:

```python
"""ATO 自动驾驶控制器（SIG-05）：制动曲线 + P 微调。"""

from __future__ import annotations

from sim_engine.signaling.pid_controller import PIDController


class ATOController:
    """制动阶段 PID 微调，牵引/惰行仍由 ThreeStageController 阶段机负责。"""

    def __init__(self, kp_brake: float, comfort_decel: float):
        self._comfort_decel = comfort_decel
        self._pid = PIDController(kp=kp_brake)

    def target_speed_on_curve(self, remaining_m: float) -> float:
        return PIDController.braking_curve_speed(remaining_m, self._comfort_decel)

    def compute_brake_level(self, speed_kmh: float, remaining_m: float) -> float:
        """前馈 v²/2d + P 微调，输出 [0,1] 制动级位。"""
        v_target = self.target_speed_on_curve(remaining_m)
        if v_target <= 0.01:
            return 1.0
        # 前馈：按剩余距离比例估算
        ff = min(1.0, max(0.0, (speed_kmh - v_target) / max(v_target, 1.0)))
        error = (speed_kmh - v_target) / max(v_target, 1.0)
        trim = self._pid.compute(error)
        return min(1.0, max(0.0, ff + trim))
```

- [ ] **Step 4: 更新 signaling/__init__.py 导出 ATOController**

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_ato.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/signaling/ato.py backend/sim_engine/signaling/__init__.py backend/tests/test_ato.py
git commit -m "feat(signaling): 新增 ATO 制动控制器"
```

---

### Task 3: ThreeStageController 接入 ATO

**Files:**
- Modify: `backend/sim_engine/signaling/three_stage.py`
- Modify: `backend/tests/test_signaling.py`

**Interfaces:**
- Consumes: `ATOController.compute_brake_level(speed_kmh, remaining_m) -> float`
- Produces: 行为不变；制动阶段内部改调 `ATOController`（替换直接 `_brake_pid` 组合逻辑）

- [ ] **Step 1: 写回归测试（制动仍有效）**

在 `test_signaling.py` 追加：

```python
def test_braking_uses_ato_controller(make_ctrl, make_train):
    ctrl, _ = make_ctrl()
    ctrl._state.phase = Phase.BRAKING
    ctrl._state._brake_target_id = "ST02"
    train = make_train(position=950.0, speed=40.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.brake_level > 0.0
```

（若项目无 `make_ctrl` fixture，按现有 `_make_ctrl()` helper 写法内联。）

- [ ] **Step 2: 运行测试确认通过或失败**

Run: `cd backend && uv run pytest tests/test_signaling.py::test_braking_command -v`

- [ ] **Step 3: 修改 three_stage.py**

在 `ThreeStageController.__init__` 中：

```python
from sim_engine.signaling.ato import ATOController

self._ato = ATOController(
    kp_brake=sim_params.pid.kp_brake,
    comfort_decel=sim_params.pid.comfort_decel,
)
```

将 `_compute_braking_level(...)` 内对 `_brake_pid` 的直接调用改为：

```python
return self._ato.compute_brake_level(train.speed, remaining_m)
```

保留 `_brake_pid` 仅当仍有引用；若无则删除字段。

- [ ] **Step 4: 全量信号测试**

Run: `cd backend && uv run pytest tests/test_signaling.py -v`

Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/three_stage.py backend/tests/test_signaling.py
git commit -m "refactor(signaling): 三段式制动改接 ATO"
```

---

### Task 4: ATPController 单列车版（SIG-04）

**Files:**
- Create: `backend/sim_engine/signaling/atp.py`
- Create: `backend/tests/test_atp.py`

**Interfaces:**
- Produces:
  - `class ATPController:` with `__init__(self, config: AtpConfig)`
  - `def check_overspeed(self, speed_kmh: float, speed_limit_kmh: float) -> SafetyStatus`
  - `def ma_end_chainage(self, train_position: float, target_station_chainage: float | None) -> float`
  - `def build_ma_profile(self, train_id: str, train_position: float, target_station_chainage: float | None) -> MaProfile`
  - `def atp_speed_limit(self, speed_limit_kmh: float) -> float` → `speed_limit * (1 - overspeed_margin)` 用于 snapshot

- [ ] **Step 1: 写失败测试**

Create `backend/tests/test_atp.py`:

```python
"""ATPController 单元测试（单列车 SIG-04）。"""

from __future__ import annotations

from sim_engine.signaling.atp import ATPController
from sim_engine.signaling.models import AtpConfig, SafetyStatus


def test_overspeed_triggers_eb():
    atp = ATPController(AtpConfig(overspeed_margin=0.05))
    limit = 80.0
    assert atp.check_overspeed(84.0, limit) == SafetyStatus.NORMAL
    assert atp.check_overspeed(84.1, limit) == SafetyStatus.EMERGENCY_BRAKE


def test_ma_end_is_target_station():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    profile = atp.build_ma_profile("T1", train_position=500.0, target_station_chainage=1000.0)
    assert profile.ma_end_chainage == 1000.0
    assert profile.safety_distance == 300.0


def test_ma_end_without_target_is_train_position():
    atp = ATPController(AtpConfig())
    profile = atp.build_ma_profile("T1", train_position=500.0, target_station_chainage=None)
    assert profile.ma_end_chainage == 500.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_atp.py -v`

- [ ] **Step 3: 实现 atp.py**

Create `backend/sim_engine/signaling/atp.py`:

```python
"""ATP 安全防护（SIG-04 单列车简化版）。"""

from __future__ import annotations

from sim_engine.signaling.models import AtpConfig, MaProfile, SafetyStatus


class ATPController:
    """固定安全距离 MA + 超速防护；不计算动态 MA 速度曲线。"""

    def __init__(self, config: AtpConfig):
        self._config = config

    def atp_speed_limit(self, speed_limit_kmh: float) -> float:
        return speed_limit_kmh * (1.0 - self._config.overspeed_margin)

    def check_overspeed(self, speed_kmh: float, speed_limit_kmh: float) -> SafetyStatus:
        threshold = speed_limit_kmh * (1.0 + self._config.overspeed_margin)
        if speed_kmh > threshold:
            return SafetyStatus.EMERGENCY_BRAKE
        return SafetyStatus.NORMAL

    def ma_end_chainage(self, train_position: float, target_station_chainage: float | None) -> float:
        if target_station_chainage is None:
            return train_position
        return target_station_chainage

    def build_ma_profile(
        self,
        train_id: str,
        train_position: float,
        target_station_chainage: float | None,
    ) -> MaProfile:
        return MaProfile(
            train_id=train_id,
            ma_end_chainage=self.ma_end_chainage(train_position, target_station_chainage),
            safety_distance=self._config.safety_distance,
        )
```

- [ ] **Step 4: 更新 __init__.py 导出 ATPController**

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_atp.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/signaling/atp.py backend/sim_engine/signaling/__init__.py backend/tests/test_atp.py
git commit -m "feat(signaling): 单列车 ATP 超速与 MA"
```

---

### Task 5: 时刻表加载（SIG-06 前置）

**Files:**
- Create: `backend/sim_engine/signaling/timetable_loader.py`
- Create: `backend/sim_engine/config/timetable.yaml`
- Create: `backend/tests/test_timetable_loader.py`

**Interfaces:**
- Produces: `def load_timetable(path: Path) -> Timetable`

- [ ] **Step 1: 创建 timetable.yaml（MVP 3 站线）**

Create `backend/sim_engine/config/timetable.yaml`（与 `track.yaml` 中 ST01/ST02/ST03 对齐，计划时刻为相对仿真起点的秒数，可按实际线路调整）：

```yaml
timetable:
  train_id: TRAIN_01
  entries:
    - station_id: ST01
      planned_arrival: 0
      planned_departure: 30
    - station_id: ST02
      planned_arrival: 90
      planned_departure: 120
    - station_id: ST03
      planned_arrival: 180
      planned_departure: 210
```

- [ ] **Step 2: 写失败测试**

```python
from pathlib import Path
from sim_engine.signaling.timetable_loader import load_timetable

def test_load_timetable():
    path = Path(__file__).resolve().parents[1] / "sim_engine/config/timetable.yaml"
    tt = load_timetable(path)
    assert tt.train_id == "TRAIN_01"
    assert tt.planned_arrival("ST02") == 90.0
```

- [ ] **Step 3: 实现 timetable_loader.py**

```python
from pathlib import Path
import yaml
from sim_engine.signaling.models import Timetable, TimetableEntry

def load_timetable(path: str | Path) -> Timetable:
    with Path(path).open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    root = data.get("timetable", data)
    entries = [
        TimetableEntry(
            station_id=str(e["station_id"]),
            planned_arrival=float(e["planned_arrival"]),
            planned_departure=float(e["planned_departure"]),
        )
        for e in root.get("entries", [])
    ]
    return Timetable(train_id=str(root.get("train_id", "TRAIN_01")), entries=entries)
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && uv run pytest tests/test_timetable_loader.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/timetable_loader.py backend/sim_engine/config/timetable.yaml backend/tests/test_timetable_loader.py
git commit -m "feat(signaling): 时刻表 YAML 加载"
```

---

### Task 6: ATSController 策略 B（SIG-06）

**Files:**
- Create: `backend/sim_engine/signaling/ats.py`
- Create: `backend/tests/test_ats.py`

**Interfaces:**
- Produces:
  - `class ATSController:` with `__init__(self, config: AtsConfig, timetable: Timetable)`
  - `def adjust_dwell(self, station_id: str, nominal_dwell: float, actual_arrival: float) -> tuple[float, TimetableDeviation | None]`
  - 策略 B：`delay = actual - planned`；`adjusted = nominal + max(0, delay)`；clamp 到 `[min, max]`

- [ ] **Step 1: 写失败测试**

```python
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.models import AtsConfig, Timetable, TimetableEntry

def _tt():
    return Timetable("TRAIN_01", [
        TimetableEntry("ST02", planned_arrival=100.0, planned_departure=130.0),
    ])

def test_on_time_dwell_unchanged():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=100.0)
    assert adjusted == 30.0
    assert dev is not None
    assert dev.delay_arrival == 0.0

def test_late_extends_dwell():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, dev = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=130.0)
    assert adjusted == 60.0  # 30 + 30s late
    assert dev.delay_arrival == 30.0

def test_early_does_not_shorten():
    ats = ATSController(AtsConfig(), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=80.0)
    assert adjusted == 30.0

def test_clamped_by_max_dwell():
    ats = ATSController(AtsConfig(max_dwell_time=45.0), _tt())
    adjusted, _ = ats.adjust_dwell("ST02", nominal_dwell=30.0, actual_arrival=200.0)
    assert adjusted == 45.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_ats.py -v`

- [ ] **Step 3: 实现 ats.py**

```python
"""ATS 运行图调度（SIG-06 策略 B：延长站停）。"""

from __future__ import annotations

from sim_engine.signaling.models import AtsConfig, Timetable, TimetableDeviation


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
        if self._config.dwell_adjust_mode == "extend":
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

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_ats.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/ats.py backend/tests/test_ats.py backend/sim_engine/signaling/__init__.py
git commit -m "feat(signaling): ATS 延长站停策略"
```

---

### Task 7: ThreeStageController 集成 ATS

**Files:**
- Modify: `backend/sim_engine/signaling/three_stage.py`
- Modify: `backend/tests/test_signaling.py`

**Interfaces:**
- Consumes: `ATSController.adjust_dwell(station_id, nominal_dwell, actual_arrival)`
- Produces: `ThreeStageController` 构造签名增加 `ats: ATSController | None = None, clock_elapsed: Callable[[], float] | None = None` 或在 `compute_commands` 传入 `elapsed: float`

- [ ] **Step 1: 写失败测试**

```python
def test_late_arrival_extends_dwell(make_ctrl_with_ats):
    ctrl, _ = make_ctrl_with_ats()
    train = make_train(position=1000.0, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1, elapsed=130.0)  # 计划 100，晚点 30
    assert ctrl.signal_state.phase == Phase.DWELL
    assert ctrl.signal_state.dwell_remaining == 60.0  # 30 nominal + 30 delay
```

- [ ] **Step 2: 修改 three_stage.py 到站分支**

在两处设置 `st.dwell_remaining = target.dwell_time` 的位置改为：

```python
nominal = target.dwell_time
if self._ats is not None:
    adjusted, _ = self._ats.adjust_dwell(target.id, nominal, elapsed)
    st.dwell_remaining = adjusted
else:
    st.dwell_remaining = nominal
```

`compute_commands(self, train, dt, elapsed: float = 0.0)` 增加 `elapsed` 参数；跳站恢复 dwell 分支同样处理。

- [ ] **Step 3: 运行测试**

Run: `cd backend && uv run pytest tests/test_signaling.py tests/test_ats.py -v`

- [ ] **Step 4: Commit**

```bash
git add backend/sim_engine/signaling/three_stage.py backend/tests/test_signaling.py
git commit -m "feat(signaling): 到站集成 ATS 站停调整"
```

---

### Task 8: 编排器集成 ATP + 时刻表 + snapshot

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Modify: `backend/sim_engine/data/snapshot.py`
- Modify: `backend/tests/test_data.py`
- Create: `backend/tests/test_orchestrator_signaling.py`

**Interfaces:**
- Consumes: `ATPController`, `ATSController`, `load_timetable`
- Produces: 每步 pipeline：
  1. `cmd = signaling.compute_commands(state, dt, elapsed=clock.elapsed)`
  2. `if atp.check_overspeed(...) == EMERGENCY_BRAKE: cmd = EB`
  3. `cmd = manual_driver.get_commands(cmd)`
  4. snapshot 含 `runningPhase`, `speedLimits`, `maProfile`, `timetableDeviation`

- [ ] **Step 1: 写 snapshot 失败测试**

在 `test_data.py` 追加：

```python
def test_snapshot_signaling_extended_fields():
    snap = build_simulation_snapshot(
        clock, sim_params, "TRAIN_01", state, forces,
        signaling_extra={
            "runningPhase": "traction",
            "speedLimits": [{"trainId": "TRAIN_01", "permanentLimit": 80, "atpLimit": 76.0}],
            "maProfile": [{"trainId": "TRAIN_01", "maEndChainage": 1000.0, "safetyDistance": 300.0}],
            "timetableDeviation": [],
        },
    )
    sig = snap["data"]["signaling"]
    assert sig["controlCommands"][0]["runningPhase"] == "traction"
    assert sig["speedLimits"][0]["atpLimit"] == 76.0
```

- [ ] **Step 2: 扩展 build_simulation_snapshot**

增加可选参数 `signaling_extra: dict | None = None`，合并进 `signaling` 段；`controlCommands[0]` 支持 `runningPhase`。

- [ ] **Step 3: 修改 orchestrator.py**

在 `from_config_dir()` 中：

```python
from sim_engine.signaling.atp import ATPController
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.timetable_loader import load_timetable

timetable = load_timetable(CONFIG_DIR / "timetable.yaml")
ats = ATSController(sim_params.signal.ats, timetable)
atp = ATPController(sim_params.signal.atp)
signaling = ThreeStageController(track, vehicle.params, sim_params, ats=ats)
```

在 `Orchestrator` dataclass 增加 `atp: ATPController` 字段。

在 `step_once()` 中，`compute_commands` 传入 `elapsed=self.clock.elapsed`；ATP 检查后覆盖 EB；构建 `signaling_extra` 传给 snapshot builder。

`runningPhase` 取自 `cmd.phase` 或 `signaling.signal_state.phase.value`。

- [ ] **Step 4: 编排器集成测试**

Create `backend/tests/test_orchestrator_signaling.py`:

```python
def test_overspeed_triggers_eb_in_snapshot(orchestrator):
    orch = orchestrator
    orch.start()
    orch.train_state.speed = 200.0  # 极端超速
    snap = orch.step_once()
    cmd = snap["data"]["signaling"]["controlCommands"][0]
    assert cmd["emergencyBrake"] is True
```

- [ ] **Step 5: 全量后端测试**

Run: `cd backend && uv run pytest tests/test_signaling.py tests/test_atp.py tests/test_ats.py tests/test_orchestrator_signaling.py tests/test_data.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/orchestrator.py backend/sim_engine/data/snapshot.py backend/tests/test_data.py backend/tests/test_orchestrator_signaling.py
git commit -m "feat(signaling): 编排器集成 ATP/ATS 输出"
```

---

### Task 9: SIG-07 占位（本迭代不实现）

**Files:**
- Create: `backend/sim_engine/signaling/train_following.py`
- Create: `backend/tests/test_train_following.py`

**Interfaces:**
- Produces: `def check_following_interval(following_pos, leading_pos, min_interval) -> bool` 仅返回是否安全（供迭代三使用）

- [ ] **Step 1: 实现占位模块**

```python
"""多车追踪间隔（SIG-07 占位，迭代三实现）。"""

def is_interval_safe(following_pos: float, leading_pos: float, min_interval: float) -> bool:
    return (following_pos - leading_pos) >= min_interval
```

- [ ] **Step 2: 单测**

```python
def test_interval_safe():
    assert is_interval_safe(1500, 1000, 500) is True
    assert is_interval_safe(1400, 1000, 500) is False
```

- [ ] **Step 3: Commit**

```bash
git add backend/sim_engine/signaling/train_following.py backend/tests/test_train_following.py
git commit -m "chore(signaling): SIG-07 多车间隔占位"
```

---

### Task 10: 验收与覆盖率

**Files:**
- Modify: `backend/tests/test_signaling.py`（可选补充场景测试）

- [ ] **Step 1: 场景测试 — 晚点到站延长站停**

Run 全程仿真，断言第二站 `timetableDeviation[0].delayArrival > 0` 且 `adjustedDwell > nominalDwell`（可在 orchestrator 集成测试中 mock 晚点）。

- [ ] **Step 2: 覆盖率**

Run: `cd backend && uv run pytest --cov=sim_engine/signaling --cov-report=term-missing`

Expected: signaling 包覆盖率 ≥ 80%（NFR-03）

- [ ] **Step 3: 全量回归**

Run: `cd backend && uv run pytest -v`

Expected: PASS

- [ ] **Step 4: Commit（若有补充测试）**

```bash
git commit -m "test(signaling): SIG-04~06 验收场景"
```

---

## Spec Self-Review

| 需求 | 对应 Task |
|------|-----------|
| SIG-04 ATP 固定距离 MA + 不计算动态曲线 | Task 4, 8 |
| SIG-04 超速 EB | Task 4, 8 |
| SIG-05 ATO PID 控车 | Task 2, 3 |
| SIG-05 signal_mode 配置 | Task 1 |
| SIG-06 ATS 仅调整站停 | Task 6, 7 |
| SIG-06 策略 B 延长站停 | Task 6 |
| SIG-07 多车 500m | Task 9 占位 only |
| 单列车 | 全文约束 |
| NFR-07 YAML 配置 | Task 1 |
| snapshot API 字段 | Task 8 |

**已知不在本计划范围：** 多车编排器、前车距离 ATP、SIG-10 车门 EB、联锁 CI、前端 UI-SIG 图表（前端另计划）。

---

## 执行顺序依赖

```
Task 1 → Task 2 → Task 3 → Task 4
              ↘ Task 5 → Task 6 → Task 7 → Task 8 → Task 9 → Task 10
```

Task 4 与 Task 5~7 可并行（不同开发者），Task 8 需等待 4 和 7 完成。
