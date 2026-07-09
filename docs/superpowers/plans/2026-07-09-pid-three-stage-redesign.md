# 三段式 PID 控车系统重新设计 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重写三段式控车系统的制动和牵引逻辑，制动改为前馈（运动学公式）+ P 微调，牵引改为开环满牵引，消除 PID 增益过低、阶段切换频繁 reset 导致的制动不准问题。

**Architecture:**
- 制动：前馈根据 v²/2d 算出所需减速度，减去阻力贡献后反推制动级位，P 微调修正风阻/坡度扰动
- 牵引：开环满牵引，接近巡航速度时切惰行，全程无 PID
- PIDController 简化为 P-only，只在制动阶段使用
- 阶段切换不再频繁 reset PID（仅到站 DWELL 时 reset）

**Tech Stack:** Python 3.10+, pytest

## 全局约束

- 保持 `PidParams` 数据类存在（`SimulationParams` 依赖它），但只保留 `comfort_decel`, `kp_brake`, `creep_gain`, `deadband_d`, `brake_safety_factor` 五个字段
- `braking_curve_speed` 静态方法保留在简化后的 `PIDController` 中
- 惰行补偿逻辑不变
- 跳站检测逻辑不变
- 所有现有测试用例通过或按新设计更新

---

### Task 1: 精简配置参数 — PidParams 和 simulation.yaml

**Files:**
- Modify: `backend/sim_engine/core/config.py` (PidParams 数据类)
- Modify: `backend/sim_engine/config/simulation.yaml` (pid 配置段)

**Interfaces:**
- Consumes: 无
- Produces: `PidParams` 数据类（精简后），`_load_pid_params()` 更新

- [ ] **Step 1: 更新 PidParams**

`backend/sim_engine/core/config.py`:
```python
@dataclass
class PidParams:
    """前馈制动参数（原 PID 参数已精简）。"""
    comfort_decel: float = 0.8
    """制动曲线舒适减速度 (m/s²)，前馈核心参数。"""

    kp_brake: float = 0.02
    """制动 P 微调增益（归一化误差 → 制动级位修正量）。"""

    creep_gain: float = 0.25
    """蠕行模式制动力随距离衰减系数。"""

    deadband_d: float = 1.0
    """蠕行触发距离 (m)，距站台该距离内且低速时切换蠕行。"""

    brake_safety_factor: float = 1.02
    """刹车触发距离安全系数。前馈响应快，不再需要大的安全余量。"""
```

- [ ] **Step 2: 更新 `_load_pid_params`**

```python
def _load_pid_params(data: dict) -> PidParams:
    pid_data = data.get("pid", {}) or {}
    return PidParams(
        comfort_decel=float(pid_data.get("comfort_decel", 0.8)),
        kp_brake=float(pid_data.get("kp_brake", 0.02)),
        creep_gain=float(pid_data.get("creep_gain", 0.25)),
        deadband_d=float(pid_data.get("deadband_d", 1.0)),
        brake_safety_factor=float(pid_data.get("brake_safety_factor", 1.02)),
    )
```

- [ ] **Step 3: 更新 `simulation.yaml`**

`backend/sim_engine/config/simulation.yaml`:
```yaml
simulation:
  pid:
    comfort_decel: 0.8
    kp_brake: 0.02
    creep_gain: 0.25
    deadband_d: 1.0
    brake_safety_factor: 1.02
  coasting_min_speed: 30.0
  speed_multiplier: 1
  station_stop_tolerance: 1.0
  target_speed_ratio: 0.8
  time_step: 0.1
  total_time: 6000
```

- [ ] **Step 4: 运行测试验证**

```bash
cd backend
pytest tests/test_pid_controller.py -v --tb=short 2>&1 | head -50
```
预期：部分测试会因 PidParams 字段变更而失败（后续任务修复）

- [ ] **Step 5: 提交**

```bash
git add backend/sim_engine/core/config.py backend/sim_engine/config/simulation.yaml
git commit -m "refactor(config): 精简 PidParams 为前馈制动参数"
```

---

### Task 2: 简化 PIDController 为 P-only

**Files:**
- Modify: `backend/sim_engine/signaling/pid_controller.py`

**Interfaces:**
- Consumes: `PidParams`（精简后）
- Produces: `PIDController(kp: float)` — `compute(error: float) -> float`，`reset()`，`braking_curve_speed(remaining_m, comfort_decel) -> float`（静态方法）

- [ ] **Step 1: 重写 pid_controller.py**

```python
"""P-only 微调控制器。

前馈制动方案中，PID 只做微调修正，不再作为主控。
去除 I/D/deadband/anti-windup，只用 P 项。
"""

from __future__ import annotations

import math


class PIDController:
    """P-only 控制器，用于制动阶段的微调修正。

    用法::

        pid = PIDController(kp=0.02)
        trim = pid.compute(error)   # error = v_actual - v_target
        brake_level = clamp(ff + trim, 0, 1)
    """

    def __init__(self, kp: float):
        self.kp = kp

    def compute(self, error: float) -> float:
        """计算 P 修正量。

        Args:
            error: 归一化误差（无量纲），如 (v_actual - v_target) / v_target。

        Returns:
            P 修正量，范围 [-kp, kp]。
        """
        return self.kp * error

    def reset(self) -> None:
        """P-only 控制器无状态，无需 reset。"""

    @staticmethod
    def braking_curve_speed(remaining_m: float, comfort_decel: float) -> float:
        """计算制动曲线上当前点的目标速度 (km/h)。

        ``v = sqrt(2 * a * d)``
        """
        if remaining_m <= 0.0:
            return 0.0
        v_ms = math.sqrt(2 * comfort_decel * remaining_m)
        return v_ms * 3.6
```

- [ ] **Step 2: 运行测试验证**

```bash
cd backend
pytest tests/test_pid_controller.py -v --tb=short 2>&1 | head -50
```
预期：大量测试失败（因为 PIDController 构造函数和 compute 签名变了）

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/signaling/pid_controller.py
git commit -m "refactor(signaling): 简化 PIDController 为 P-only"
```

---

### Task 3: 重写 ThreeStageController — 前馈制动 + 开环牵引

**Files:**
- Modify: `backend/sim_engine/signaling/three_stage.py`

**Interfaces:**
- Consumes: `PidParams`（精简后），`PIDController`（P-only），`SimulationParams`
- Produces: `ThreeStageController.compute_commands(train, dt) -> ControlCommands`，`ThreeStageController.pid_params -> PidParams`

- [ ] **Step 1: 重写 three_stage.py**

核心变更：
1. 删除 `_traction_pid`，只保留 `_brake_pid`（P-only）
2. 重写 `_braking_step`：前馈 + P 微调
3. 简化牵引阶段为开环满牵引
4. 阶段切换不再 reset（仅 DWELL 时 reset）
5. 保留惰行补偿、跳站检测、蠕行模式

```python
"""三段式运行模式控制器（前馈制动版）。

牵引 → 惰行 → 制动：
- 牵引：开环满牵引，接近巡航速度时切惰行
- 制动：前馈（运动学公式）+ P 微调，精确停靠站台
- 接近站台时切换为蠕行模式，确保柔和停车

到站停车后等待站停时间再发车。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sim_engine.core.config import PidParams, SimulationParams
from sim_engine.signaling.pid_controller import PIDController
from sim_engine.track.models import Station
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.dynamics import effective_speed_limit_kmh
from sim_engine.vehicle.models import GRAVITY, ControlCommands, TrainState, VehicleParams
from sim_engine.vehicle.traction import interpolate_force_percent


class Phase(str, Enum):
    TRACTION = "traction"
    COASTING = "coasting"
    BRAKING = "braking"
    DWELL = "dwell"


@dataclass
class TrainSignalState:
    phase: Phase = Phase.TRACTION
    dwell_remaining: float = 0.0
    _dwell_station_id: str = ""
    _last_target_station_id: str = ""


class ThreeStageController:
    """为单列车生成控车指令。

    牵引阶段：开环满牵引，无 PID。
    制动阶段：前馈（运动学公式）+ P 微调。
    """

    def __init__(
        self,
        track: TrackPathService,
        vehicle_params: VehicleParams,
        sim_params: SimulationParams,
    ):
        self.track = track
        self.vehicle_params = vehicle_params
        self.sim_params = sim_params
        self._state = TrainSignalState()

        # P-only 制动微调控制器
        self._brake_pid = PIDController(kp=sim_params.pid.kp_brake)

        # 标记首站为已停靠，防止兜底检测误判刚离站的列车
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    @property
    def signal_state(self) -> TrainSignalState:
        return self._state

    @property
    def pid_params(self) -> PidParams:
        """制动 PID 参数（测试可通过此属性验证配置）。"""
        return self.sim_params.pid

    def reset(self) -> None:
        self._state = TrainSignalState()
        self._brake_pid.reset()
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    def compute_commands(self, train: TrainState, dt: float) -> ControlCommands:
        st = self._state
        tol = self.sim_params.station_stop_tolerance

        # ── DWELL 站停倒计时 ──
        if st.phase == Phase.DWELL:
            st.dwell_remaining = max(0.0, st.dwell_remaining - dt)
            if st.dwell_remaining <= 0:
                st.phase = Phase.TRACTION
            return ControlCommands()

        target = self.track.next_station_ahead(train.position)

        # ── 跳站检测 ──
        if st._last_target_station_id and target is not None and target.id != st._last_target_station_id:
            old_station = self.track.get_station_by_id(st._last_target_station_id)
            if old_station is not None and train.position > old_station.chainage:
                if old_station.id != st._dwell_station_id:
                    if train.speed < 0.1 and abs(train.position - old_station.chainage) <= 50.0:
                        st.phase = Phase.DWELL
                        st.dwell_remaining = old_station.dwell_time
                        st._dwell_station_id = old_station.id
                        return ControlCommands()
                    st._dwell_station_id = old_station.id
        if target is not None:
            st._last_target_station_id = target.id

        if target is None:
            if train.speed > 0.1:
                return ControlCommands(brake_level=1.0)
            return ControlCommands()

        track_params = self.track.query_at(train.position)
        speed_limit = effective_speed_limit_kmh(track_params, self.vehicle_params)
        v_cruise = self.sim_params.target_speed_ratio * speed_limit
        brake_dist = self._brake_trigger_distance(train)
        dist_to_station = target.chainage - train.position

        # ── 到站停稳检测 ──
        if train.speed < 0.1 and abs(dist_to_station) <= tol:
            st.phase = Phase.DWELL
            st.dwell_remaining = target.dwell_time
            st._dwell_station_id = target.id
            self._brake_pid.reset()
            return ControlCommands()

        if train.speed < 0.1 and dist_to_station > tol and train.position > tol:
            current_station = self.track.station_at(train.position, half_length=50.0)
            if current_station is not None and current_station.id != st._dwell_station_id:
                st.phase = Phase.DWELL
                st.dwell_remaining = current_station.dwell_time
                st._dwell_station_id = current_station.id
                self._brake_pid.reset()
                return ControlCommands()

        if train.speed < 0.1 and dist_to_station > tol:
            st.phase = Phase.TRACTION

        # ── TRACTION: 开环满牵引 ──
        if st.phase == Phase.TRACTION:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                return self._braking_step(train, target, dt)
            if train.speed >= v_cruise - 2.0:
                st.phase = Phase.COASTING
                return ControlCommands()
            return ControlCommands(traction_level=1.0)

        # ── COASTING: 惰行 + 开环补偿 ──
        if st.phase == Phase.COASTING:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                return self._braking_step(train, target, dt)
            curve_speed = PIDController.braking_curve_speed(
                max(dist_to_station, 1.0), self.sim_params.pid.comfort_decel
            )
            dynamic_min = min(curve_speed * 0.4, self.sim_params.coasting_min_speed)
            dynamic_min = max(dynamic_min, 5.0)
            if train.speed < dynamic_min:
                st.phase = Phase.TRACTION
                return ControlCommands(traction_level=1.0)
            comp = self._coasting_compensation(train, track_params)
            return ControlCommands(traction_level=comp, phase="coasting")

        # ── BRAKING: 前馈 + P 微调 ──
        return self._braking_step(train, target, dt)

    # ── 制动阶段核心 ──

    def _braking_step(
        self, train: TrainState, target: Station, dt: float
    ) -> ControlCommands:
        """前馈制动 + P 微调。

        前馈：根据运动学 a = v²/2d 计算所需减速度，减去阻力贡献后反推制动级位。
        P 微调：以 ATO 制动曲线为目标做归一化误差修正。
        """
        remaining = max(target.chainage - train.position, 0.0)
        pp = self.sim_params.pid

        # 蠕行
        if remaining <= pp.deadband_d and train.speed < 3.0:
            return self._creep_brake(remaining)

        v_ms = train.speed / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass

        # 前馈：运动学所需减速度
        if remaining > 0.1:
            a_required = (v_ms * v_ms) / (2.0 * remaining)
        else:
            a_required = 0.0

        # 当前阻力也在帮忙减速
        track_params = self.track.query_at(train.position)
        resistance = self._calc_resistance(train, track_params)
        a_from_resistance = resistance / mass

        # 制动力需要提供的减速度
        a_from_brake = max(0.0, a_required - a_from_resistance)
        brake_ff = (mass * a_from_brake) / self.vehicle_params.max_brake_force
        brake_ff = min(brake_ff, 1.0)

        # P 微调：以 ATO 制动曲线为目标
        v_target_kmh = PIDController.braking_curve_speed(remaining, pp.comfort_decel)
        if v_target_kmh > 1.0:
            error = (train.speed - v_target_kmh) / v_target_kmh
        else:
            error = 0.0
        trim = self._brake_pid.compute(error)

        brake = max(0.0, min(brake_ff + trim, 1.0))
        return ControlCommands(brake_level=brake)

    def _creep_brake(self, remaining_m: float) -> ControlCommands:
        """蠕行模式：制动力与剩余距离成正比。"""
        pp = self.sim_params.pid
        brake = min(remaining_m * pp.creep_gain, 0.5)
        brake = max(brake, 0.02)
        return ControlCommands(brake_level=brake)

    # ── 制动触发距离 ──

    def _brake_trigger_distance(self, train: TrainState) -> float:
        v_ms = max(train.speed, 0.0) / 3.6
        decel = self.sim_params.pid.comfort_decel
        if decel <= 0:
            return 0.0
        safety = self.sim_params.pid.brake_safety_factor
        return (v_ms * v_ms) / (2 * decel) * safety

    # ── 阻力计算（前馈用） ──

    def _calc_resistance(self, train: TrainState, track_params) -> float:
        """计算当前总阻力 (N)。"""
        from sim_engine.vehicle import resistance as R

        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params
        r_davis = R.davis_resistance(p, mass, train.speed)
        r_gradient = R.gradient_resistance(mass, track_params.gradient)
        r_curve = R.curve_resistance(mass, track_params.curvature, p.curve_resist_coeff)
        r_tunnel = R.tunnel_resistance(r_davis, track_params.is_tunnel, p.tunnel_resist_factor)
        return r_davis + r_curve + r_tunnel + r_gradient

    # ── 惰行补偿（与原相同） ──

    def _coasting_compensation(
        self, train: TrainState, track_params
    ) -> float:
        v_ms = abs(train.speed) / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params

        rolling = (p.davis_a + p.davis_b * v_ms) * mass * GRAVITY
        gradient_force = mass * GRAVITY * (track_params.gradient / 1000.0)
        f_target = rolling + gradient_force
        if f_target <= 0:
            return 0.0

        percent = interpolate_force_percent(p.traction_curve, train.speed)
        max_available = p.max_traction_force * percent
        if max_available <= 0:
            return 0.0

        level = f_target / max_available
        return min(max(level, 0.0), 1.0)
```

- [ ] **Step 2: 运行测试验证**

```bash
cd backend
pytest tests/test_signaling.py -v --tb=short 2>&1 | head -80
```
预期：制动相关测试失败（需要更新）

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/signaling/three_stage.py
git commit -m "feat(signaling): 前馈制动 + 开环牵引，重写制动逻辑"
```

---

### Task 4: 更新测试 — test_pid_controller.py

**Files:**
- Modify: `backend/tests/test_pid_controller.py`

- [ ] **Step 1: 重写测试文件**

```python
"""P-only 控制器单元测试。

覆盖：比例项、制动曲线、边界条件。
"""

from __future__ import annotations

import math

import pytest

from sim_engine.core.config import PidParams
from sim_engine.signaling.pid_controller import PIDController


# ── P-only compute ─────────────────────────────────────────────────

def test_p_only_compute():
    """error → kp × error。"""
    pid = PIDController(kp=0.02)
    assert pid.compute(0.5) == pytest.approx(0.01)
    assert pid.compute(-0.5) == pytest.approx(-0.01)


def test_p_only_zero_error():
    """误差为 0 时输出 0。"""
    pid = PIDController(kp=0.02)
    assert pid.compute(0.0) == 0.0


def test_p_only_reset_noop():
    """reset 不报错（P-only 无状态）。"""
    pid = PIDController(kp=0.02)
    pid.compute(0.5)
    pid.reset()  # 不应报错
    assert pid.compute(0.3) == pytest.approx(0.006)


# ── 制动曲线 ───────────────────────────────────────────────────────

def test_braking_curve_speed_zero_remaining():
    assert PIDController.braking_curve_speed(0.0, 0.8) == 0.0
    assert PIDController.braking_curve_speed(-5.0, 0.8) == 0.0


def test_braking_curve_speed_formula():
    v = PIDController.braking_curve_speed(100.0, 0.8)
    expected = math.sqrt(2 * 0.8 * 100.0) * 3.6
    assert v == pytest.approx(expected)


def test_braking_curve_speed_decreases_with_distance():
    v1 = PIDController.braking_curve_speed(200.0, 0.8)
    v2 = PIDController.braking_curve_speed(100.0, 0.8)
    v3 = PIDController.braking_curve_speed(10.0, 0.8)
    assert v1 > v2 > v3 > 0.0


# ── PidParams 默认值 ───────────────────────────────────────────────

def test_pid_params_defaults():
    p = PidParams()
    assert p.comfort_decel == 0.8
    assert p.kp_brake == 0.02
    assert p.creep_gain == 0.25
    assert p.deadband_d == 1.0
    assert p.brake_safety_factor == 1.02
```

- [ ] **Step 2: 运行测试验证**

```bash
cd backend
pytest tests/test_pid_controller.py -v --tb=short
```
预期：全部 PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_pid_controller.py
git commit -m "test(signaling): 更新 PID 测试为 P-only"
```

---

### Task 5: 更新测试 — test_signaling.py

**Files:**
- Modify: `backend/tests/test_signaling.py`

- [ ] **Step 1: 更新测试文件**

关键变更：
1. 删除 `test_traction_when_below_target_speed`（满牵引 1.0，不再验证 PID）
2. 删除 `test_traction_pid_partial_near_target`（不再有牵引 PID）
3. 更新 `test_braking_command` — 制动不再是满制动，验证前馈输出
4. 更新 `test_braking_pid_partial_near_target` — 验证前馈 + P 微调
5. 更新 `test_brake_trigger_distance_formula` — 安全系数改为 1.02
6. 更新 `test_brake_trigger_distance_zero_mass` — 安全系数改为 1.02
7. 更新 `test_full_cycle_to_station` — 模拟使用完整动力学
8. 新增 `test_braking_feed_forward_numerical` — 前馈数值验证
9. 新增 `test_braking_stop_accuracy` — 多步模拟停车精度

```python
# 需要替换/更新的测试函数：

# 删除：
# test_traction_when_below_target_speed（第173行）
# test_traction_pid_partial_near_target（第183行）

# 更新 test_braking_command（第327行）：
def test_braking_command():
    """制动阶段由前馈输出制动力（超速时满制动）。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.BRAKING
    # 距站台 40m，速度 50 km/h → 前馈输出 ≈ 1.0
    train = _make_train(position=960.0, speed=50.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert cmd.brake_level > 0.5
    assert cmd.traction_level == 0.0

# 更新 test_braking_pid_partial_near_target（第338行）：
def test_braking_pid_partial_near_target():
    """接近制动曲线目标时前馈输出部分制动力。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.BRAKING
    # 距站台 50m，速度 33 km/h → 接近曲线目标，应输出适中制动力
    train = _make_train(position=950.0, speed=33.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert 0.1 < cmd.brake_level < 0.8

# 更新 test_brake_trigger_distance_formula（第426行）：
def test_brake_trigger_distance_formula():
    """制动触发距离 = v²/(2·comfort_decel) × safety_factor。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(speed=72.0, mass=260000.0)
    v_ms = 72.0 / 3.6
    expected = (v_ms * v_ms) / (2 * 0.8) * 1.02  # safety_factor=1.02
    assert ctrl._brake_trigger_distance(train) == pytest.approx(expected)

# 更新 test_brake_trigger_distance_zero_mass（第442行）：
def test_brake_trigger_distance_zero_mass():
    """新公式不再依赖 mass。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(speed=50.0, mass=0.0)
    v_ms = 50.0 / 3.6
    expected = (v_ms * v_ms) / (2 * 0.8) * 1.02
    assert ctrl._brake_trigger_distance(train) == pytest.approx(expected)

# 更新 test_coasting_to_braking_when_near_station（第313行）：
# 安全系数改为 1.02，注释中的预期值也需要更新
def test_coasting_to_braking_when_near_station():
    """当位置 + 制动距离 ≥ 站台中心时进入制动。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.COASTING
    train = _make_train(position=900.0, speed=60.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    # brake_dist = (16.67²)/(2×0.8)×1.02 ≈ 177.1m
    # position + brake_dist = 900 + 177.1 = 1077.1 > 1000 → 应触发制动
    assert cmd.brake_level > 0.0
    assert ctrl.signal_state.phase == Phase.BRAKING

# 新增：前馈数值验证
def test_braking_feed_forward_formula():
    """验证前馈制动级位的数值正确性。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    ctrl._state.phase = Phase.BRAKING
    # 距站台 150m，速度 54 km/h (15 m/s)
    # a_required = 15²/(2×150) = 0.75 m/s²
    # 平坡阻力 ≈ (0.01+0.0001×15)×260000×9.81 ≈ 29.3kN
    # a_from_resistance = 29300/260000 ≈ 0.113 m/s²
    # a_from_brake = 0.75 - 0.113 = 0.637 m/s²
    # brake_ff = 260000×0.637/350000 ≈ 0.473
    train = _make_train(position=850.0, speed=54.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert 0.3 < cmd.brake_level < 0.7

# 新增：多步模拟制动停车精度
def test_braking_stop_accuracy():
    """多步模拟后列车应停在站台容差内。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    train = _make_train(position=750.0, speed=64.0, mass=260000.0)
    ctrl._state.phase = Phase.BRAKING

    for _ in range(2000):
        cmd = ctrl.compute_commands(train, dt=0.1)
        # 简单动力学
        v_ms = train.speed / 3.6
        mass = train.mass
        if cmd.brake_level > 0:
            accel = -350000 * cmd.brake_level / mass
        else:
            # 阻力自然减速
            resistance = (0.01 + 0.0001 * v_ms) * mass * 9.81
            accel = -resistance / mass
        new_v_ms = max(v_ms + accel * 0.1, 0.0)
        train = _make_train(
            position=train.position + new_v_ms * 0.1,
            speed=new_v_ms * 3.6,
            mass=mass,
        )
        if train.speed < 0.1 and abs(train.position - 1000.0) <= 1.0:
            break

    # 停在站台附近
    assert abs(train.position - 1000.0) <= 5.0
    assert train.speed < 0.1
```

- [ ] **Step 2: 运行测试验证**

```bash
cd backend
pytest tests/test_signaling.py -v --tb=short
```
预期：全部 PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_signaling.py
git commit -m "test(signaling): 更新制动测试为前馈逻辑"
```

---

### 自检清单

1. **Spec 覆盖**：前馈制动 → Task 3 ✓，开环牵引 → Task 3 ✓，P-only PID → Task 2 ✓，精简配置 → Task 1 ✓，蠕行模式 → Task 3 ✓，触发距离 → Task 3 ✓
2. **占位符检查**：所有代码块均已填充完整 ✓
3. **类型一致性**：`PidParams` 字段变化在 Task 1 定义，Task 2/3 使用一致 ✓，`PIDController(kp)` 在 Task 2 定义，Task 3 用 `PIDController(kp=...)` ✓