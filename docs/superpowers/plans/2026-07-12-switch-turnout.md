# 道岔子系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现道岔数据模型、SwitchManager、配置加载、snapshot 数据流，使前端 SwitchStatus 组件能从后端获取真正的道岔状态。

**Architecture:** 新增 `Switch` dataclass 和 `SwitchManager`（与 `OccupancyDetector` 对称设计），通过 `orchestrator` 每步 `update(dt)`、`snapshot` 透传，`apiAdapter` 映射到前端 Switch 接口，`SwitchStatus.tsx` 无需修改。

**Tech Stack:** Python 3.10+ dataclasses, YAML, TypeScript

## Global Constraints

- 后端 Python 3.10+，无额外非必要第三方依赖
- 所有参数通过配置文件注入
- 单元测试覆盖率 ≥ 90%
- 轨道道岔查询响应时间 ≤ 1ms（NFR-10）

---

### Task 1: Switch 数据模型 + YAML 配置

**Files:**
- Modify: `backend/sim_engine/track/models.py`
- Modify: `backend/sim_engine/config/track.yaml`
- Modify: `backend/sim_engine/track/config.py`
- Modify: `backend/sim_engine/track/__init__.py`

**Interfaces:**
- Produces: `Switch` dataclass (id, chainage, switch_type, normal_direction, reverse_direction, lateral_speed_limit, state, transition_time, transition_elapsed, _target_state)
- Produces: `Track.switches: list[Switch]`
- Produces: `load_track()` returns Track with switches loaded from YAML

- [ ] **Step 1: Add Switch dataclass to models.py**

In `backend/sim_engine/track/models.py`, add after `TrackCircuit` class (before `TrackLine`):

```python
@dataclass
class Switch:
    """道岔（TRK-06）。

    支持单开和交叉渡线两种类型，具有定位/反位/转换中三种状态，
    转换时延用于模拟机械切换过程。
    """

    id: str                          # 道岔 ID，如 SW01
    chainage: float                  # 道岔中心公里标 (m)
    switch_type: str                 # "single" / "crossover"
    normal_direction: str            # 定位方向，如 "main"
    reverse_direction: str           # 反位方向，如 "siding"
    lateral_speed_limit: float = 30.0  # 侧向限速 (km/h)
    state: str = "normal"            # "normal" / "reverse" / "transitioning"
    transition_time: float = 3.0     # 转换时延 (s)
    transition_elapsed: float = 0.0  # 已转换时间 (s)

    _target_state: str = field(default="normal", repr=False)

    def __post_init__(self) -> None:
        if self._target_state not in ("normal", "reverse"):
            object.__setattr__(self, "_target_state", self.state)
```

Add `switches` field to `Track` (after `circuits` field):

```python
@dataclass
class Track:
    name: str
    direction: str = "down"
    stations: list[Station] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    circuits: list[TrackCircuit] = field(default_factory=list)
    switches: list[Switch] = field(default_factory=list)   # ← NEW
    lines: list[TrackLine] = field(default_factory=list)

    @property
    def total_length(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end_chainage for s in self.segments)
```

- [ ] **Step 2: Add switch config to track.yaml**

In `backend/sim_engine/config/track.yaml`, append after the `track_circuits` section:

```yaml

  # ── 道岔配置（TRK-06）────────────────────────────────
  # 4 组道岔：两端折返 + 中间关键站侧线
  switches:
    - { id: SW01, chainage: 50,    switch_type: crossover, normal_direction: main, reverse_direction: siding, lateral_speed_limit: 30, state: normal }
    - { id: SW02, chainage: 7300,  switch_type: single,    normal_direction: main, reverse_direction: siding, lateral_speed_limit: 30, state: normal }
    - { id: SW03, chainage: 15900, switch_type: single,    normal_direction: main, reverse_direction: siding, lateral_speed_limit: 30, state: normal }
    - { id: SW04, chainage: 18550, switch_type: crossover, normal_direction: main, reverse_direction: siding, lateral_speed_limit: 30, state: normal }
```

- [ ] **Step 3: Load switch config in config.py**

In `backend/sim_engine/track/config.py`, add `Switch` to imports and add switch loading:

```python
from .models import Segment, Station, Switch, Track, TrackCircuit
```

After the `circuits` list comprehension (before `return Track(...)`), add:

```python
    switches = [
        Switch(
            id=s["id"],
            chainage=float(s["chainage"]),
            switch_type=str(s.get("switch_type", "single")),
            normal_direction=str(s.get("normal_direction", "main")),
            reverse_direction=str(s.get("reverse_direction", "siding")),
            lateral_speed_limit=float(s.get("lateral_speed_limit", 30.0)),
            state=str(s.get("state", "normal")),
        )
        for s in data.get("switches", [])
    ]
```

Update the `return Track(...)` call to include `switches`:

```python
    return Track(
        name=data.get("name", "线路"),
        direction=str(data.get("direction", "down")),
        stations=stations,
        segments=segments,
        circuits=circuits,
        switches=switches,
    )
```

- [ ] **Step 4: Export Switch in __init__.py**

In `backend/sim_engine/track/__init__.py`, import `Switch`:

```python
from .models import Segment, Station, Switch, Track, TrackCircuit, TrackLine
```

Add `"Switch"` to `__all__`:

```python
__all__ = [
    "Segment",
    "Station",
    "Switch",
    "Track",
    "TrackCircuit",
    "TrackLine",
    "TrackPathService",
    "OccupancyDetector",
    "load_track",
]
```

- [ ] **Step 5: Verify config loading**

Run (from `backend/`):

```bash
python -c "from sim_engine.track.config import load_track; t = load_track('sim_engine/config/track.yaml'); print(f'Switches: {len(t.switches)}'); [print(f'  {s.id} @ {s.chainage}m, type={s.switch_type}, state={s.state}') for s in t.switches]"
```

Expected output:
```
Switches: 4
  SW01 @ 50.0m, type=crossover, state=normal
  SW02 @ 7300.0m, type=single, state=normal
  SW03 @ 15900.0m, type=single, state=normal
  SW04 @ 18550.0m, type=crossover, state=normal
```

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/track/models.py backend/sim_engine/config/track.yaml backend/sim_engine/track/config.py backend/sim_engine/track/__init__.py
git commit -m "feat(track): add Switch dataclass and YAML config loading"
```

---

### Task 2: SwitchManager (`switch.py`)

**Files:**
- Create: `backend/sim_engine/track/switch.py`

**Interfaces:**
- Consumes: `Switch` dataclass from Task 1
- Produces: `SwitchManager` class with `query(switch_id) -> Switch|None`, `set_state(switch_id, target) -> bool`, `update(dt) -> None`, `switch_list() -> list[dict]`

- [ ] **Step 1: Write the test file**

Create `backend/tests/test_switch.py`:

```python
"""SwitchManager 单元测试（TRK-06/TRK-08/TRK-09）。"""

from sim_engine.track.models import Switch
from sim_engine.track.switch import SwitchManager


def make_switches():
    return [
        Switch(id="SW01", chainage=50, switch_type="crossover",
               normal_direction="main", reverse_direction="siding",
               lateral_speed_limit=30, state="normal", transition_time=3.0),
        Switch(id="SW02", chainage=7300, switch_type="single",
               normal_direction="main", reverse_direction="siding",
               lateral_speed_limit=30, state="normal", transition_time=3.0),
    ]


class TestSwitchManagerQuery:
    def test_query_existing_switch(self):
        mgr = SwitchManager(make_switches())
        sw = mgr.query("SW01")
        assert sw is not None
        assert sw.id == "SW01"
        assert sw.state == "normal"

    def test_query_nonexistent_returns_none(self):
        mgr = SwitchManager(make_switches())
        assert mgr.query("SW99") is None

    def test_query_empty_manager(self):
        mgr = SwitchManager([])
        assert mgr.query("SW01") is None


class TestSwitchManagerSetState:
    def test_set_state_normal_to_reverse(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "reverse")
        assert ok is True
        sw = mgr.query("SW01")
        assert sw is not None
        assert sw.state == "transitioning"
        assert sw._target_state == "reverse"
        assert sw.transition_elapsed == 0.0

    def test_set_state_invalid_target(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "invalid")
        assert ok is False
        sw = mgr.query("SW01")
        assert sw.state == "normal"

    def test_set_state_already_transitioning(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        ok = mgr.set_state("SW01", "normal")  # Should reject
        assert ok is False
        sw = mgr.query("SW01")
        assert sw._target_state == "reverse"  # Target unchanged

    def test_set_state_same_as_current(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "normal")
        assert ok is False  # Already in normal, no-op

    def test_set_state_nonexistent_switch(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW99", "reverse")
        assert ok is False


class TestSwitchManagerUpdate:
    def test_update_transitions_after_full_time(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(3.0)
        sw = mgr.query("SW01")
        assert sw.state == "reverse"
        assert sw.transition_elapsed == 3.0
        assert sw._target_state == "reverse"

    def test_update_partial_transition(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(1.5)
        sw = mgr.query("SW01")
        assert sw.state == "transitioning"
        assert sw.transition_elapsed == 1.5

    def test_update_multiple_switches(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.set_state("SW02", "reverse")
        mgr.update(3.0)
        assert mgr.query("SW01").state == "reverse"
        assert mgr.query("SW02").state == "reverse"

    def test_update_no_transitioning_does_nothing(self):
        mgr = SwitchManager(make_switches())
        mgr.update(1.0)
        assert mgr.query("SW01").state == "normal"


class TestSwitchManagerSwitchList:
    def test_switch_list_default_states(self):
        mgr = SwitchManager(make_switches())
        lst = mgr.switch_list()
        assert len(lst) == 2
        assert lst[0]["switchId"] == "SW01"
        assert lst[0]["state"] == "normal"
        assert lst[0]["chainage"] == 50
        assert lst[0]["type"] == "crossover"
        assert lst[0]["normalDirection"] == "main"
        assert lst[0]["reverseDirection"] == "siding"
        assert lst[0]["lateralSpeedLimit"] == 30

    def test_switch_list_reflects_transition(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(1.0)
        lst = mgr.switch_list()
        sw = next(s for s in lst if s["switchId"] == "SW01")
        assert sw["state"] == "transitioning"
        assert sw["transitionElapsed"] == 1.0

    def test_switch_list_empty(self):
        mgr = SwitchManager([])
        assert mgr.switch_list() == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_switch.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'sim_engine.track.switch'`

- [ ] **Step 3: Implement SwitchManager**

Create `backend/sim_engine/track/switch.py`:

```python
"""道岔管理器（TRK-06/TRK-08/TRK-09）。

管理道岔定位/反位状态的切换，模拟机械转换时延。
"""

from __future__ import annotations

from .models import Switch


class SwitchManager:
    """道岔状态管理器。

    每个道岔有三种状态：normal（定位）、reverse（反位）、
    transitioning（转换中）。切换需经过 3 秒转换时延。
    """

    def __init__(self, switches: list[Switch]):
        self._switches = {s.id: s for s in switches}

    # ── TRK-08：道岔状态查询 ──

    def query(self, switch_id: str) -> Switch | None:
        """查询道岔当前状态。返回 None 表示道岔不存在。"""
        return self._switches.get(switch_id)

    # ── TRK-09：道岔控制接口 ──

    def set_state(self, switch_id: str, target: str) -> bool:
        """设置道岔目标状态，启动转换时延。

        Args:
            switch_id: 道岔 ID
            target: "normal" 或 "reverse"

        Returns:
            True 表示已接受指令并开始转换，False 表示拒绝
            （道岔不存在、无效目标、已在转换中、已是目标状态）。
        """
        sw = self._switches.get(switch_id)
        if sw is None:
            return False
        if target not in ("normal", "reverse"):
            return False
        if sw.state == "transitioning":
            return False
        if sw.state == target:
            return False
        sw.state = "transitioning"
        sw.transition_elapsed = 0.0
        sw._target_state = target
        return True

    # ── 转换时延推进 ──

    def update(self, dt: float) -> None:
        """推进所有转换中道岔的 elapsed 时间。

        应在每个仿真步调用一次。
        """
        for sw in self._switches.values():
            if sw.state != "transitioning":
                continue
            sw.transition_elapsed += dt
            if sw.transition_elapsed >= sw.transition_time:
                sw.state = sw._target_state
                sw.transition_elapsed = sw.transition_time

    # ── 序列化 ──

    def switch_list(self) -> list[dict]:
        """返回道岔状态列表，供 snapshot 序列化。

        格式与 API 文档附录 B 对齐：
            {"switchId", "chainage", "type", "normalDirection",
             "reverseDirection", "lateralSpeedLimit", "state",
             "transitionElapsed", "transitionTime"}
        """
        return [
            {
                "switchId": s.id,
                "chainage": s.chainage,
                "type": s.switch_type,
                "normalDirection": s.normal_direction,
                "reverseDirection": s.reverse_direction,
                "lateralSpeedLimit": s.lateral_speed_limit,
                "state": s.state,
                "transitionElapsed": s.transition_elapsed,
                "transitionTime": s.transition_time,
            }
            for s in self._switches.values()
        ]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_switch.py -v --tb=short
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/track/switch.py backend/tests/test_switch.py
git commit -m "feat(track): add SwitchManager with query, set_state, transition delay"
```

---

### Task 3: Orchestrator + Snapshot 集成

**Files:**
- Modify: `backend/sim_engine/track/__init__.py`
- Modify: `backend/sim_engine/data/snapshot.py`
- Modify: `backend/sim_engine/orchestrator.py`

**Interfaces:**
- Consumes: `SwitchManager` from Task 2
- Produces: `build_simulation_snapshot(..., switch_states=...)` — snapshot 包含真实 switchStates
- Produces: `Orchestrator` 实例化并每步调用 `switch_manager.update(dt)`

- [ ] **Step 1: Export SwitchManager in __init__.py**

In `backend/sim_engine/track/__init__.py`, add import and export:

```python
from .switch import SwitchManager
```

Add `"SwitchManager"` to `__all__`:

```python
__all__ = [
    "Segment",
    "Station",
    "Switch",
    "SwitchManager",
    "Track",
    "TrackCircuit",
    "TrackLine",
    "TrackPathService",
    "OccupancyDetector",
    "load_track",
]
```

- [ ] **Step 2: Update snapshot.py to accept switch_states**

In `backend/sim_engine/data/snapshot.py`, add `switch_states` parameter:

```python
def build_simulation_snapshot(
    clock: SimulationClock,
    sim_params: SimulationParams,
    train_id: str,
    state: TrainState,
    forces: ForceBreakdown,
    pantograph_voltage: float = 1500.0,
    power_demand: float = 0.0,
    voltage_profile: list[dict] | None = None,
    substation_states: list | None = None,
    signaling_extra: dict | None = None,
    occupancy: list[dict] | None = None,
    switch_states: list[dict] | None = None,
) -> dict:
```

Replace the hardcoded `"switchStates": []` on line 109 with:

```python
            "track": {"occupancy": occupancy or [], "switchStates": switch_states or []},
```

- [ ] **Step 3: Integrate SwitchManager in orchestrator.py**

In `backend/sim_engine/orchestrator.py`, add import:

```python
from sim_engine.track.switch import SwitchManager
```

Add `switch_manager` field to `Orchestrator` dataclass (after `occupancy`):

```python
    occupancy: OccupancyDetector = field(default_factory=lambda: OccupancyDetector([]))
    switch_manager: SwitchManager = field(default_factory=lambda: SwitchManager([]))
    recorder: DataRecorder = field(default_factory=DataRecorder)
```

In `from_config_dir`, after the `occupancy = OccupancyDetector(...)` line, add:

```python
        switch_manager = SwitchManager(track.track.switches)
```

In the returned `cls(...)` call, add:

```python
        return cls(
            vehicle=vehicle,
            track=track,
            signaling=signaling,
            atp=atp,
            ats=ats,
            clock=clock,
            sim_params=sim_params,
            power_network=power_network,
            occupancy=occupancy,
            switch_manager=switch_manager,
        )
```

In `step_once`, after `self.occupancy.update(...)` (line 186), add:

```python
        # ── 道岔转换时延推进 ──
        self.switch_manager.update(dt)
```

In the `build_simulation_snapshot` call, add the `switch_states` parameter:

```python
        snapshot = build_simulation_snapshot(
            self.clock,
            self.sim_params,
            self.train_id,
            result.state,
            result.forces,
            pantograph_voltage=pantograph_voltage,
            power_demand=power_demand,
            voltage_profile=voltage_profile,
            substation_states=substation_states,
            occupancy=self.occupancy.occupancy_list(),
            switch_states=self.switch_manager.switch_list(),
            ...
```

In `reset`, after `self.occupancy.update({})`, reset switch states (optional — switches don't change on reset since they're controlled manually):

No change to reset needed — switches persist their state. But let's ensure clean state:

After `self.occupancy.update({})` (line 114), add:

```python
        # Reset all switches to normal
        for sw in self.switch_manager._switches.values():
            sw.state = "normal"
            sw.transition_elapsed = 0.0
            sw._target_state = "normal"
```

- [ ] **Step 4: Verify integration**

Run (from `backend/`):

```bash
python -c "from sim_engine.orchestrator import Orchestrator; o = Orchestrator.from_config_dir(); s = o.step_once(); print('switchStates:', s['data']['track']['switchStates'])"
```

Expected: 4 switch entries in `switchStates`, all with `"state": "normal"`.

- [ ] **Step 5: Run existing tests to verify no regression**

```bash
cd backend && python -m pytest tests/test_occupancy.py tests/test_track.py tests/test_switch.py -v --tb=short -q
```

Expected: All 79+ tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/sim_engine/track/__init__.py backend/sim_engine/data/snapshot.py backend/sim_engine/orchestrator.py
git commit -m "feat(track): integrate SwitchManager into orchestrator and snapshot"
```

---

### Task 4: Frontend apiAdapter 映射

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts`

**Interfaces:**
- Consumes: Backend `switchStates` (snakeCase from backend list)
- Produces: `switch_states: Switch[]` mapped to frontend `Switch` interface

- [ ] **Step 1: Add Switch import and map switchStates**

In `frontend/src/utils/apiAdapter.ts`, add `Switch` to import:

```typescript
import type {
  ApiControlCommand,
  ApiSimulationSnapshot,
  SimulationParams,
  SimulationSnapshot,
  SimulationStats,
  Switch,
  TrackCircuit,
  TrainState,
} from '../types/simulation';
```

Replace the hardcoded `switch_states: []` (line 100) with:

```typescript
      switch_states: ((raw.track?.switchStates ?? []) as Record<string, unknown>[]).map(
        (s): Switch => ({
          id: String(s.switchId ?? ''),
          chainage: Number(s.chainage ?? 0),
          type: (s.type as Switch['type']) ?? 'single',
          normal_direction: String(s.normalDirection ?? 'main'),
          reverse_direction: String(s.reverseDirection ?? 'siding'),
          lateral_speed_limit: Number(s.lateralSpeedLimit ?? 30),
          state: (s.state as Switch['state']) ?? 'normal',
        }),
      ),
```

- [ ] **Step 2: Update frameToSnapshot for consistency**

In `frontend/src/utils/frameToSnapshot.ts`, `switch_states: []` remains correct for mock replay mode (no switches in mock data). No change needed.

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit src/utils/apiAdapter.ts 2>&1
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/apiAdapter.ts
git commit -m "feat(frontend): map track.switchStates from backend in apiAdapter"
```

---

### Task 5: End-to-End Verification

- [ ] **Step 1: Start backend and verify WebSocket push**

Start backend in one terminal (refer to project's start script).

Connect via WebSocket or check logs — verify `track.switchStates` contains 4 entries with actual data (not empty array).

- [ ] **Step 2: Verify frontend SwitchStatus renders without mock**

Open the track view in browser. The `SwitchStatus` panel should show SW01–SW04 with 定位 (green) status — no longer falling back to mock data.

- [ ] **Step 3: Final test run**

```bash
cd backend && python -m pytest tests/test_switch.py tests/test_occupancy.py tests/test_track.py -v --tb=short
```

All tests must pass.

- [ ] **Step 4: Commit any remaining changes**

```bash
git status
git add -A
git commit -m "test(track): verify end-to-end switch data flow"
```
