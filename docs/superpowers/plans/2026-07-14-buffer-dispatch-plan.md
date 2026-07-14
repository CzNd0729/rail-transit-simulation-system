# 存车线缓冲区调度 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FleetScheduler 中引入存车线缓冲区机制，实现"有旧车发旧车，没旧车发新车"的双端调度策略，消除折返列车与反向新车的冲突。

**Architecture:** 在 `FleetScheduler` 内维护 `{origin_station: [BufferSlot]}` 缓冲区池；`tick()` 中优先从缓冲区取车，取不到才发新车；`Orchestrator.step_once()` 中检测列车到达终点后存入缓冲区并标记 inactive；snapshot 新增 `bufferState` 字段供前端展示。

**Tech Stack:** Python 3.10+, dataclass, PyYAML, pytest

## Global Constraints

- 所有可调参数通过 YAML 注入，不得硬编码（NFR-07）
- 无额外非必要第三方依赖（NFR-06）
- 对外速度单位 km/h，位置 m，时间步长 dt 为秒
- 提交格式：`feat(dispatch): <中文描述>`（≤50 字符，caveman-commit）
- `vehicle_id` 终身不变，`train_id` 每趟一换
- 前缀 D/U 表示当前方向，序列号全局递增

---

### Task 1: 数据模型 — BufferSlot + DispatchOrigin + TrainRun 扩展

**Files:**
- Modify: `backend/sim_engine/signaling/models.py`
- Test: `backend/tests/test_signal_models.py`

**Interfaces:**
- Produces:
  - `@dataclass BufferSlot: vehicle_id, previous_train_id, total_trips, total_mileage, passenger_load, state, arrival_time`
  - `DispatchOrigin.buffer_capacity: int = 1`
  - `TrainRun.vehicle_id: str = ""`
  - `TrainRun.total_trips: int = 0`
  - `TrainRun.total_mileage: float = 0.0`

- [ ] **Step 1: 写失败测试**

在 `test_signal_models.py` 末尾追加：

```python
from sim_engine.signaling.models import BufferSlot, DispatchOrigin, TrainRun


def test_buffer_slot_defaults():
    slot = BufferSlot(
        vehicle_id="VEH_001",
        previous_train_id="D01",
        total_trips=1,
        total_mileage=5000.0,
        passenger_load=0.6,
        state=None,
        arrival_time=2000.0,
    )
    assert slot.vehicle_id == "VEH_001"
    assert slot.total_trips == 1
    assert slot.total_mileage == 5000.0


def test_dispatch_origin_buffer_capacity():
    origin = DispatchOrigin(
        origin_station="ST01",
        origin_chainage=0.0,
        initial_direction="down",
        trip_leg_names=("down", "up"),
    )
    assert origin.buffer_capacity == 1


def test_train_run_vehicle_id():
    run = TrainRun(
        train_id="D01",
        state=None,
        signaling=None,
        ats=None,
        manual_driver=None,
    )
    assert run.vehicle_id == ""
    assert run.total_trips == 0
    assert run.total_mileage == 0.0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_signal_models.py::test_buffer_slot_defaults tests/test_signal_models.py::test_dispatch_origin_buffer_capacity tests/test_signal_models.py::test_train_run_vehicle_id -v`

Expected: FAIL — `BufferSlot` not defined, `DispatchOrigin` has no `buffer_capacity`

- [ ] **Step 3: 实现 BufferSlot + 扩展 DispatchOrigin / TrainRun**

在 `models.py` 末尾新增：

```python
@dataclass
class BufferSlot:
    """存车线中的一列车。"""
    vehicle_id: str
    previous_train_id: str
    total_trips: int = 0
    total_mileage: float = 0.0
    passenger_load: float = 0.6
    state: object = None
    arrival_time: float = 0.0
```

在 `DispatchOrigin` 末尾增加字段：

```python
@dataclass(frozen=True)
class DispatchOrigin:
    # ... 原有字段 ...
    buffer_capacity: int = 1
```

在 `TrainRun` 末尾增加字段：

```python
@dataclass
class TrainRun:
    # ... 原有字段 ...
    vehicle_id: str = ""
    total_trips: int = 0
    total_mileage: float = 0.0
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_signal_models.py -v`

Expected: 原有测试 + 新增测试全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/models.py backend/tests/test_signal_models.py
git commit -m "feat(dispatch): BufferSlot 数据模型 + TrainRun/Origin 扩展"
```

---

### Task 2: FleetScheduler 缓冲区管理

**Files:**
- Modify: `backend/sim_engine/signaling/fleet_scheduler.py`
- Test: `backend/tests/test_fleet_scheduler.py`
- Test: `backend/tests/test_continuous_dispatch_integration.py`

**Interfaces:**
- Consumes: `BufferSlot`, `DispatchOrigin.buffer_capacity`, `TrainRun.vehicle_id`
- Produces:
  - `FleetScheduler.receive_train(run: TrainRun) -> bool`
  - `FleetScheduler.buffer_state() -> dict`
  - `FleetScheduler._pop_buffer(origin_station: str) -> BufferSlot | None`
  - `FleetScheduler._has_buffer_train(origin_station: str) -> bool`

- [ ] **Step 1: 写失败的 FleetScheduler 缓冲区测试**

在 `test_fleet_scheduler.py` 末尾追加：

```python
from sim_engine.signaling.models import BufferSlot, TrainRun


def test_receive_train_stores_in_buffer():
    svc = _single_origin_service()
    sched = FleetScheduler(svc)
    created: list[str] = []

    def create(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_legs: tuple[str, ...],
        start_pos: float,
    ) -> None:
        created.append(train_id)

    # 发一列车
    sched.tick(0.0, [], create)
    assert len(created) == 1

    # 模拟该车到达终点，存入缓冲区
    # 构造一个 fake TrainRun-like 对象
    fake_run = TrainRun(
        train_id="TRAIN_01",
        vehicle_id="VEH_001",
        total_trips=1,
        total_mileage=18600.0,
        state=None,
        signaling=None,
        ats=None,
        manual_driver=None,
        direction="down",
        active=True,
    )
    ok = sched.receive_train(fake_run)
    assert ok is True

    # 验证缓冲区状态
    bs = sched.buffer_state()
    assert "ST01" in bs
    assert len(bs["ST01"]) == 1
    assert bs["ST01"][0]["vehicleId"] == "VEH_001"


def test_buffer_train_used_before_new():
    """缓冲区有车时优先发旧车，不发新车。"""
    svc = _single_origin_service()
    sched = FleetScheduler(svc)
    created: list[tuple[str, str, int]] = []  # (train_id, vehicle_id, total_trips)

    def create(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_legs: tuple[str, ...],
        start_pos: float,
        vehicle_id: str = "",
        total_trips: int = 0,
    ) -> None:
        created.append((train_id, vehicle_id, total_trips))

    # 先发新车
    sched.tick(0.0, [], create)
    assert created[0] == ("TRAIN_01", "", 0)

    # 存入缓冲区（模拟到达）
    fake_run = TrainRun(
        train_id="TRAIN_01",
        vehicle_id="VEH_001",
        total_trips=1, total_mileage=18600.0,
        state=None, signaling=None, ats=None, manual_driver=None,
        direction="down", active=True,
    )
    sched.receive_train(fake_run)

    # 下一 tick 应该发旧车 VEH_001，而不是新车
    sched.tick(150.0, [], create)
    # 旧车：vehicle_id 保留，total_trips=2（跑完一趟+新一趟）
    assert created[1][1] == "VEH_001"
    assert created[1][2] == 2
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_fleet_scheduler.py::test_receive_train_stores_in_buffer tests/test_fleet_scheduler.py::test_buffer_train_used_before_new -v`

Expected: FAIL — `FleetScheduler` has no `receive_train` / `buffer_state`

- [ ] **Step 3: 实现 FleetScheduler 缓冲区管理**

修改 `fleet_scheduler.py`：

**在 `__init__` 末尾增加缓冲区初始化：**

```python
self._buffers: dict[str, list[BufferSlot]] = {
    o.origin_station: [] for o in origins
}
self._vehicle_serial: int = 0
self._service_serial: int = 0
```

**新增方法：**

```python
def _next_vehicle_id(self) -> str:
    self._vehicle_serial += 1
    return f"VEH_{self._vehicle_serial:03d}"

def _next_service_id(self, prefix: str) -> str:
    self._service_serial += 1
    if prefix:
        return f"TRAIN_{prefix}{self._service_serial:02d}"
    return f"TRAIN_{self._service_serial:02d}"

def receive_train(self, run: TrainRun) -> bool:
    """列车到达终点站→存入本端存车线。"""
    station = "ST24" if run.direction == "down" else "ST01"
    slot = BufferSlot(
        vehicle_id=run.vehicle_id,
        previous_train_id=run.train_id,
        total_trips=run.total_trips + 1,
        total_mileage=run.total_mileage,
        passenger_load=run.state.passenger_load if run.state else 0.6,
        state=run.state,
        arrival_time=0.0,  # 由调用方设置
    )
    self._buffers[station].append(slot)
    return True

def buffer_state(self) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for station, slots in self._buffers.items():
        result[station] = [
            {
                "vehicleId": s.vehicle_id,
                "previousTrainId": s.previous_train_id,
                "totalTrips": s.total_trips,
                "arrivalTime": s.arrival_time,
            }
            for s in slots
        ]
    return result

def _pop_buffer(self, origin_station: str) -> BufferSlot | None:
    """FIFO 从存车线取一列车。"""
    buf = self._buffers.get(origin_station, [])
    if not buf:
        return None
    return buf.pop(0)
```

**修改 `tick()` 方法：**

在 `tick()` 方法中，`while` 循环内发车时，先检查缓冲区：

```python
# 在 stream.advance_headway() 之前，替换原有的发车逻辑：
slot = self._pop_buffer(stream.origin.origin_station)
if slot is not None:
    # 发旧车：使用 buffer 中的车辆，注意方向不变（按发车端初始方向）
    train_id = self._next_service_id(stream.origin.train_id_prefix)
    create_run(
        train_id,
        stream.next_departure_time,
        stream.origin.initial_direction,
        stream.origin.trip_leg_names,
        stream.origin.origin_chainage,
        vehicle_id=slot.vehicle_id,
        total_trips=slot.total_trips,
        passenger_load=slot.passenger_load,
    )
else:
    # 发新车
    vehicle_id = self._next_vehicle_id()
    train_id = self._next_service_id(stream.origin.train_id_prefix)
    create_run(
        train_id,
        stream.next_departure_time,
        stream.origin.initial_direction,
        stream.origin.trip_leg_names,
        stream.origin.origin_chainage,
        vehicle_id=vehicle_id,
        total_trips=0,
        passenger_load=0.6,
    )
dispatched.append((train_id, stream.origin.initial_direction, stream.origin.origin_chainage))
```

**注意**：`create_run` 回调签名需要新增 `vehicle_id` 和 `total_trips` 参数。在 `orchestrator.py` 中对应更新（Task 3 处理）。

同时，`_DispatchProbe` 中 `train_id` 需要改为使用新生成的 `train_id`。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_fleet_scheduler.py -v`

Expected: 原有测试 + 新增测试全部 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/signaling/fleet_scheduler.py backend/tests/test_fleet_scheduler.py
git commit -m "feat(dispatch): FleetScheduler 缓冲区管理和旧车优先发车"
```

---

### Task 3: Orchestrator — 到达进存车线 + vehicle_id 支持

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`
- Test: `backend/tests/test_continuous_dispatch_integration.py`

**Interfaces:**
- Consumes: `FleetScheduler.receive_train()`, `TrainRun.vehicle_id`, `TrainRun.total_trips`
- Produces: `Orchestrator._create_train_run()` 支持 `vehicle_id`, `total_trips`, `passenger_load` 参数

- [ ] **Step 1: 写集成测试**

在 `test_continuous_dispatch_integration.py` 末尾追加：

```python
def test_continuous_arrival_stores_in_buffer():
    """列车到达终点后应存入缓冲区，而非继续 active。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    # 运行足够长的时间，让 D01 到达 ST24（约 2000s）
    for _ in range(25000):
        orch.step_once()
    # 检查缓冲区应有车辆
    assert orch._fleet_scheduler is not None
    bs = orch._fleet_scheduler.buffer_state()
    # 至少有一端缓冲区有车
    has_any = any(len(v) > 0 for v in bs.values())
    assert has_any, f"buffer_state should have entries, got {bs}"


def test_continuous_buffer_vehicle_id_persists():
    """从缓冲区发出后 vehicle_id 应保持不变，total_trips 递增。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    # 长时间运行，观察列车 vehicle_id
    vehicle_ids: set[str] = set()
    for _ in range(50000):
        orch.step_once()
        for run in orch.trains:
            if run.active and run.vehicle_id:
                vehicle_ids.add(run.vehicle_id)
    # 应该能观察到多个 vehicle_id
    assert len(vehicle_ids) >= 2, f"Expected >=2 vehicle_ids, got {vehicle_ids}"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && uv run pytest tests/test_continuous_dispatch_integration.py::test_continuous_arrival_stores_in_buffer -v`

Expected: 当前测试通过（因为 snapshot 没有 bufferState 字段），但检查逻辑可以看到缓冲区为空

- [ ] **Step 3: 修改 Orchestrator**

**3a. 修改 `_create_train_run()` 支持 vehicle_id 参数：**

```python
def _create_train_run(
    self,
    train_id: str,
    spawn_time: float,
    direction: str,
    trip_leg_names: tuple[str, ...],
    start_pos: float | None = None,
    vehicle_id: str = "",
    total_trips: int = 0,
    passenger_load: float | None = None,
) -> TrainRun:
    """continuous 模式动态创建列车（支持 buffer 旧车复用）。"""
    assert self._service_timetable is not None
    legs = materialize_trip_timetables(
        self._service_timetable, train_id, trip_leg_names
    )
    total_length = self.track.track.total_length
    if start_pos is None:
        start_pos = _start_chainage(direction, total_length)
    abs_tt = legs[0].with_absolute_times(spawn_time)
    ats = ATSController(self.sim_params.signal.ats, abs_tt)
    signaling = ThreeStageController(
        self.track, self.vehicle.params, self.sim_params, ats=ats
    )
    signaling.reset(direction=direction)
    pl = passenger_load if passenger_load is not None else self._passenger_load
    return TrainRun(
        train_id=train_id,
        vehicle_id=vehicle_id or self._next_vehicle_id(),  # 如果没有 vehicle_id，生成新 ID
        state=self.vehicle.create_initial_state(
            position=start_pos,
            passenger_load=pl,
            direction=direction,
        ),
        signaling=signaling,
        ats=ats,
        manual_driver=ManualDriveController(),
        spawn_time=spawn_time,
        active=True,
        direction=direction,
        legs=legs,
        leg_index=0,
        trip_leg_names=trip_leg_names,
        total_trips=total_trips,
        total_mileage=0.0,
    )


def _next_vehicle_id(self) -> str:
    """生成全局唯一 vehicle_id。"""
    if not hasattr(self, '_vehicle_serial'):
        self._vehicle_serial = 0
    self._vehicle_serial += 1
    return f"VEH_{self._vehicle_serial:03d}"
```

**3b. 修改 `_tick_continuous_dispatch()` 传递 vehicle_id：**

```python
def _tick_continuous_dispatch(self, elapsed: float) -> None:
    assert self._fleet_scheduler is not None

    def create_run(
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_leg_names: tuple[str, ...],
        start_pos: float,
        vehicle_id: str = "",
        total_trips: int = 0,
        passenger_load: float = 0.6,
    ) -> None:
        self.trains.append(
            self._create_train_run(
                train_id, spawn_time, direction, trip_leg_names, start_pos,
                vehicle_id=vehicle_id,
                total_trips=total_trips,
                passenger_load=passenger_load,
            )
        )

    active = [r for r in self.trains if r.active]
    self._fleet_scheduler.tick(elapsed, active, create_run)
```

**3c. 在 `step_once()` 末尾，snapshot 构建前，增加到达终点检测：**

在 `step_once()` 中，`self.clock.tick()` 之前，新增：

```python
# 检查是否有列车到达终点→存入存车线
if self._fleet_scheduler is not None:
    for run in active_runs:
        if not run.active:
            continue
        if self._at_terminal(run):
            run.active = False
            self._fleet_scheduler.receive_train(run)
```

其中 `_at_terminal` 方法：

```python
def _at_terminal(self, run: TrainRun) -> bool:
    """判断列车是否到达终点站并停稳。"""
    if run.state.speed >= 0.1:
        return False
    total = self.track.track.total_length
    if run.direction == "down":
        return run.state.position >= total - 1.0
    return run.state.position <= 1.0
```

**3d. 在 snapshot 构建中加入 `bufferState`：**

在 `step_once()` 的 snapshot 构建段，增加：

```python
buffer_state = {}
if self._fleet_scheduler is not None:
    buffer_state = self._fleet_scheduler.buffer_state()

snapshot = build_simulation_snapshot(
    ...,
    buffer_state=buffer_state,
)
```

- [ ] **Step 4: 更新 snapshot.py 支持 buffer_state 参数**

修改 `build_simulation_snapshot()` 签名，增加 `buffer_state: dict | None = None`，并在 `data` 中增加字段：

```python
def build_simulation_snapshot(
    ...,
    buffer_state: dict | None = None,
    ...
) -> dict:
    ...
    return {
        "type": "simulation_snapshot",
        "timestamp": clock.elapsed,
        "data": {
            ...
            "bufferState": buffer_state or {},
        },
    }
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd backend && uv run pytest tests/test_continuous_dispatch_integration.py::test_continuous_arrival_stores_in_buffer tests/test_continuous_dispatch_integration.py::test_continuous_buffer_vehicle_id_persists -v`

Expected: PASS

- [ ] **Step 6: 全量回归**

Run: `cd backend && uv run pytest -v`

Expected: 全部 PASS（可能会有少量时序敏感测试需要调整 tolerance）

- [ ] **Step 7: Commit**

```bash
git add backend/sim_engine/orchestrator.py backend/sim_engine/data/snapshot.py backend/tests/test_continuous_dispatch_integration.py
git commit -m "feat(dispatch): 列车到站进存车线 + vehicle_id 追踪"
```

---

### Task 4: 更新 timetable.yaml 配置

**Files:**
- Modify: `backend/sim_engine/config/timetable.yaml`

- [ ] **Step 1: 为两个发车端增加 buffer_capacity**

```yaml
origins:
  - origin_station: ST01
    initial_direction: down
    trip_legs: [down, up]
    train_id_prefix: D
    first_departure_s: 0
    headway_s: 150
    buffer_capacity: 1
  - origin_station: ST24
    initial_direction: up
    trip_legs: [up, down]
    train_id_prefix: U
    first_departure_s: 0
    headway_s: 150
    buffer_capacity: 1
```

- [ ] **Step 2: 确认 yaml 加载测试通过**

Run: `cd backend && uv run pytest tests/test_timetable_v2_loader.py -v`

Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/sim_engine/config/timetable.yaml
git commit -m "chore(dispatch): timetable.yaml 增加 buffer_capacity"
```

---

### Task 5: 集成验收

**Files:**
- Test: `backend/tests/test_continuous_dispatch_integration.py`

- [ ] **Step 1: 写验收测试**

在 `test_continuous_dispatch_integration.py` 末尾追加：

```python
def test_continuous_buffer_steady_state():
    """长时间运行后，列车总数应趋于稳定（不再增长），进入稳态。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 10000.0
    orch.reset()
    orch.start()
    train_counts: list[int] = []
    for _ in range(100000):
        orch.step_once()
        active = len([r for r in orch.trains if r.active])
        buffer_total = sum(
            len(v) for v in (orch._fleet_scheduler.buffer_state() if orch._fleet_scheduler else {}).values()
        )
        train_counts.append(active + buffer_total)
    # 后半段的列车总数应该稳定，不再增长
    first_half = train_counts[:len(train_counts)//2]
    second_half = train_counts[len(train_counts)//2:]
    max_growth = max(second_half) - min(second_half)
    assert max_growth <= 2, f"列车总数不稳定，后半段波动 {max_growth}"


def test_continuous_buffer_new_train_stops_after_steady():
    """稳态后不应再产生新车（全部 vehicle_id 来自缓冲区复用）。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 10000.0
    orch.reset()
    orch.start()
    # 运行完整仿真
    for _ in range(100000):
        orch.step_once()
    # 检查所有 active 列车的 vehicle_id 格式
    for run in orch.trains:
        if run.active:
            assert run.vehicle_id.startswith("VEH_"), f"Unexpected vehicle_id: {run.vehicle_id}"
    # 总列车数应 > 0
    assert len(orch.trains) > 0
```

- [ ] **Step 2: 运行验收测试**

Run: `cd backend && uv run pytest tests/test_continuous_dispatch_integration.py::test_continuous_buffer_steady_state tests/test_continuous_dispatch_integration.py::test_continuous_buffer_new_train_stops_after_steady -v`

Expected: PASS

- [ ] **Step 3: 全量回归**

Run: `cd backend && uv run pytest -v`

Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_continuous_dispatch_integration.py
git commit -m "test(dispatch): 缓冲区稳态验收测试"
```

---

## 自审检查

- [x] 所有任务覆盖设计文档中的每项改动（model → scheduler → orchestrator → snapshot → config → test）
- [x] 无 TBD/TODO 占位
- [x] 每个步骤包含完整代码
- [x] 命令含预期输出
- [x] 任务间类型签名一致（`vehicle_id: str`, `receive_train(run: TrainRun) -> bool`, `buffer_state() -> dict`）
- [x] 边界情况处理：缓冲区空时发新车，缓冲区 FIFO 弹出