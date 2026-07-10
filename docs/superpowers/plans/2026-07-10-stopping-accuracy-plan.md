# 停车精度测量与显示 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在列车运行过程中实时测量并显示距前方站台的距离，停稳后该值即为停车误差。

**Architecture:** 每步仿真中 `ThreeStageController` 计算 `distance_to_station`，通过 `Orchestrator.step_once` 写入 `TrainState`，再经 `build_simulation_snapshot` 推送到前端。前端 `StatusCards` 新增一张"距站台"卡片实时显示该值。

**Tech Stack:** Python 3.10+ (后端), React 19 + TypeScript (前端), WebSocket (通信)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `backend/sim_engine/vehicle/models.py` | 修改 | `TrainState` 增加 `distance_to_station` 和 `target_station_id` 字段 |
| `backend/sim_engine/signaling/three_stage.py` | 修改 | `TrainSignalState` 增加距离字段，`compute_commands` 末尾更新距离 |
| `backend/sim_engine/orchestrator.py` | 修改 | `step_once` 中从信号状态复制距离到 `TrainState` |
| `backend/sim_engine/data/snapshot.py` | 修改 | `trains[]` 中增加 `distanceToStation` 和 `targetStationId` |
| `backend/tests/test_signaling.py` | 修改 | 新增停车精度相关测试 |
| `frontend/src/types/simulation.ts` | 修改 | `TrainState` 和 `ApiTrainState` 增加距离字段 |
| `frontend/src/utils/apiAdapter.ts` | 修改 | `mapTrain` 中映射新字段 |
| `frontend/src/components/views/overview/StatusCards.tsx` | 修改 | 新增"距站台"卡片 |
| `docs/superpowers/specs/2026-07-10-stopping-accuracy-design.md` | 已提交 | 设计文档 |

---

### Task 1: 后端 — `TrainState` 增加距离字段

**Files:**
- Modify: `backend/sim_engine/vehicle/models.py:124-154`

**Interfaces:**
- Consumes: 无
- Produces: `TrainState.distance_to_station: float`, `TrainState.target_station_id: str`

- [ ] **Step 1: 在 `TrainState` 中增加两个字段**

在 `TrainState` dataclass 的 `regen_energy` 字段之后添加：

```python
distance_to_station: float = 0.0
"""距当前目标站距离 (m)。正值 = 距站台还有多远，负值 = 已冲过站台。"""

target_station_id: str = ""
"""当前目标站 ID。无目标站时为空字符串。"""
```

- [ ] **Step 2: 确认修改**

用 `git diff` 确认改动只涉及 `TrainState` 的两个新字段。

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/vehicle/models.py
git commit -m "feat(vehicle): TrainState 增加 distance_to_station 和 target_station_id"
```

---

### Task 2: 后端 — `ThreeStageController` 计算距站距离

**Files:**
- Modify: `backend/sim_engine/signaling/three_stage.py:32-39` (TrainSignalState), `:160-273` (compute_commands)

**Interfaces:**
- Consumes: `TrainState.position`, `TrackPathService.next_station_ahead()`
- Produces: `TrainSignalState.distance_to_station`, `TrainSignalState.target_station_id`

- [ ] **Step 1: 在 `TrainSignalState` 中增加字段**

```python
@dataclass
class TrainSignalState:
    phase: Phase = Phase.TRACTION
    dwell_remaining: float = 0.0
    _dwell_station_id: str = ""
    _last_target_station_id: str = ""
    _brake_target_id: str = ""
    distance_to_station: float = 0.0
    """距当前目标站距离 (m)。"""
    target_station_id: str = ""
    """当前目标站 ID。"""
```

- [ ] **Step 2: 在 `compute_commands` 末尾更新距离**

在 `compute_commands` 方法的 `return` 语句之前（在所有逻辑分支之后）插入距离更新代码。找到 `target` 变量已确定的位置，在方法末尾的每个 `return` 之前更新距离。

由于 `compute_commands` 有多个 return 路径，最佳位置是在 `target` 确定后的公共逻辑处。将距离更新放在方法末尾的 `return self._braking_output(...)` 之前，以及处理 `target is None` 的分支之后。

具体修改：在 `compute_commands` 方法的 `return self._braking_output(train, target, dt)` 这行之前（第 273 行附近），以及 DWELL 阶段返回之前，添加：

```python
# 在 compute_commands 中，每个 return 之前更新距站距离
# 方法：在方法末尾添加一个统一的更新点
# 在 return self._braking_output(train, target, dt) 之前
```

更干净的实现方式：在 `compute_commands` 方法的 **最后一行**（最后一个 `return` 之前）添加一个统一更新逻辑。但因为有多个提前 return，需要在每个 return 前更新。

**最佳方案**：在 `compute_commands` 方法开头获取 `target` 之后，添加一个 `_update_distance` 辅助方法，在每个 return 前调用：

```python
def _update_distance(self, train: TrainState, target: Station | None) -> None:
    st = self._state
    if target is not None:
        st.target_station_id = target.id
        st.distance_to_station = target.chainage - train.position
    else:
        st.target_station_id = ""
        st.distance_to_station = 0.0
```

在 `compute_commands` 中，在每个 `return` 语句之前添加 `self._update_distance(train, target)`。

需要在方法中确定 `target` 变量在每个 return 处是否可用。检查后发现：

- L169-171 的 DWELL 阶段 return：target 尚未获取，此时距离应保持上一次的值 → 不需要更新
- L192-194 的跳站兜底检测 return：target 已获取 → 需更新
- L203-206 的 `target is None` return：target 为 None → 需更新
- L220-222 的到站停稳 return：target 已获取 → 需更新
- L227-233 的兜底到站 return：target 已获取 → 需更新
- L246-249 的 TRACTION 阶段 return：target 已获取 → 需更新
- L268-271 的 COASTING 阶段 return：target 已获取 → 需更新
- L273 的 BRAKING 阶段 return：target 已获取 → 需更新

**简化方案**：在每个 return 之前添加 `self._update_distance(train, target)`。共约 7 个插入点。

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/signaling/three_stage.py
git commit -m "feat(signaling): ThreeStageController 计算距站距离"
```

---

### Task 3: 后端 — `Orchestrator` 复制距离到 `TrainState` + `snapshot` 输出

**Files:**
- Modify: `backend/sim_engine/orchestrator.py:102-152`
- Modify: `backend/sim_engine/data/snapshot.py:38-50`

**Interfaces:**
- Consumes: `TrainSignalState.distance_to_station`, `TrainSignalState.target_station_id`
- Produces: WebSocket 快照中的 `distanceToStation` 和 `targetStationId`

- [ ] **Step 1: 在 `Orchestrator.step_once` 中复制距离**

在 `step_once` 方法中，`self.train_state = result.state` 之后，`self.clock.tick()` 之前添加：

```python
# 复制信号系统的距站距离到 TrainState（供 snapshot 输出）
sig_st = self.signaling.signal_state
self.train_state.distance_to_station = sig_st.distance_to_station
self.train_state.target_station_id = sig_st.target_station_id
```

- [ ] **Step 2: 在 `build_simulation_snapshot` 中输出距离字段**

在 `snapshot.py` 的 `build_simulation_snapshot` 函数中，`trains[]` 列表的字典内增加两个字段：

```python
"distanceToStation": state.distance_to_station,  # 距目标站距离 (m)
"targetStationId": state.target_station_id,       # 目标站 ID
```

放在 `"faultAlarm": None,` 之后。

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/orchestrator.py backend/sim_engine/data/snapshot.py
git commit -m "feat(core): 快照输出距站距离字段"
```

---

### Task 4: 后端 — 停车精度单元测试

**Files:**
- Modify: `backend/tests/test_signaling.py`
- Test: 新增 4 个测试函数

**Interfaces:**
- 测试 `ThreeStageController` 的 `signal_state.distance_to_station` 值

- [ ] **Step 1: 新增 `test_distance_to_station_running`**

在 `test_signaling.py` 末尾添加：

```python
# ── SIG-04: 停车精度 ────────────────────────────────────────────────

def test_distance_to_station_running():
    """列车在区间运行时距站距离为正。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # 列车在 ST01 (0m) 和 ST02 (1000m) 之间
    train = _make_train(position=500.0, speed=60.0)
    ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.distance_to_station == pytest.approx(500.0, abs=0.1)
    assert ctrl.signal_state.target_station_id == "ST02"


def test_distance_to_station_stopped_accurate():
    """在站台容差内停稳时距离 ≈ 0。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # ST02 在 1000m，容差 1.0m，停在 999.5m 应在容差内
    train = _make_train(position=999.5, speed=0.0)
    cmd = ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.phase == Phase.DWELL
    assert ctrl.signal_state.distance_to_station == pytest.approx(0.5, abs=0.01)  # 1000 - 999.5 = 0.5m


def test_distance_to_station_stopped_overrun():
    """冲过站台时距离为负。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # 越过 ST02 50m 但仍在低速（兜底检测范围）
    train = _make_train(position=1050.0, speed=0.05)
    ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.distance_to_station == pytest.approx(-50.0, abs=0.1)


def test_distance_to_station_no_target():
    """无前方目标站时距离为 0。"""
    ctrl = ThreeStageController(_make_track(), _make_vehicle_params(), _make_sim_params())
    # 已过最后一个站
    train = _make_train(position=1100.0, speed=20.0)
    ctrl.compute_commands(train, dt=0.1)
    assert ctrl.signal_state.distance_to_station == 0.0
    assert ctrl.signal_state.target_station_id == ""
```

- [ ] **Step 2: 运行测试验证通过**

```bash
cd backend && python -m pytest tests/test_signaling.py::test_distance_to_station_running tests/test_signaling.py::test_distance_to_station_stopped_accurate tests/test_signaling.py::test_distance_to_station_stopped_overrun tests/test_signaling.py::test_distance_to_station_no_target -v
```

Expected: 4 PASSED

- [ ] **Step 3: 运行全量信号测试确保不破坏现有功能**

```bash
cd backend && python -m pytest tests/test_signaling.py -v
```

Expected: 全部 PASSED

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_signaling.py
git commit -m "test(signaling): 停车精度距站距离单元测试"
```

---

### Task 5: 前端 — 类型定义扩展

**Files:**
- Modify: `frontend/src/types/simulation.ts:106-119` (TrainState)
- Modify: `frontend/src/types/simulation.ts:369-383` (ApiTrainState)

- [ ] **Step 1: `TrainState` 增加距离字段**

在 `TrainState` 接口的 `fault_alarm` 之前添加：

```typescript
distance_to_station: number;  // 距目标站距离 (m)
target_station_id: string;    // 目标站 ID
```

- [ ] **Step 2: `ApiTrainState` 增加距离字段**

在 `ApiTrainState` 接口的 `faultAlarm` 之前添加：

```typescript
distanceToStation: number;
targetStationId: string;
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/types/simulation.ts
git commit -m "feat(ui): TrainState 类型增加距站距离字段"
```

---

### Task 6: 前端 — API 适配层映射

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts:29-44`

- [ ] **Step 1: 在 `mapTrain` 中增加映射**

在 `mapTrain` 函数的 `fault_alarm: t.faultAlarm` 之后添加：

```typescript
distance_to_station: t.distanceToStation ?? 0,
target_station_id: t.targetStationId ?? "",
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/utils/apiAdapter.ts
git commit -m "feat(ui): apiAdapter 映射距站距离字段"
```

---

### Task 7: 前端 — StatusCards 新增「距站台」卡片

**Files:**
- Modify: `frontend/src/components/views/overview/StatusCards.tsx`

- [ ] **Step 1: 替换"信号授权"卡片为"距站台"卡片**

在 `StatusCards` 组件中，将最后一个卡片（信号授权）替换为：

```tsx
import { useSimulationState } from '../../../context/SimulationContext';

// 在组件内部，获取 lineLayout 用于查找站名
const { trains, lineLayout } = useSimulationState();
const train = trains[0];

// 计算距离显示文本和颜色
let distanceText = '--';
let distanceColor = '#808080';
if (train && train.target_station_id) {
  const station = lineLayout?.stations.find(s => s.id === train.target_station_id);
  const stationName = station?.name ?? train.target_station_id;
  const d = train.distance_to_station;
  if (d > 0) {
    distanceText = `距 ${stationName} ${d.toFixed(1)}m`;
  } else if (d === 0) {
    distanceText = `已到 ${stationName}`;
  } else {
    distanceText = `已过 ${stationName} ${Math.abs(d).toFixed(1)}m`;
  }
  distanceColor = Math.abs(d) <= 1.0 ? '#52c41a' : '#ff4d4f';
}

// 将 cards 数组最后一个改为：
const cards = [
  { label: '当前速度', value: train ? formatSpeed(train.speed) : '-- km/h', icon: '🏎️', color: '#1890ff' },
  { label: '受电弓电压', value: train ? formatVoltage(train.pantograph_voltage) : '-- V', icon: '⚡', color: '#faad14' },
  { label: '当前工况', value: train ? getModeLabel(train.mode) : '--', icon: '⚙️', color: train ? getModeColor(train.mode) : '#999' },
  { label: '距站台', value: distanceText, icon: '📍', color: distanceColor },
];
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/views/overview/StatusCards.tsx
git commit -m "feat(ui): StatusCards 新增距站台距离卡片"
```

---

### Task 8: 集成验证

- [ ] **Step 1: 后端全量测试**

```bash
cd backend && python -m pytest -v
```

Expected: 全部 PASSED

- [ ] **Step 2: 前端类型检查**

```bash
cd frontend && npx tsc --noEmit
```

Expected: 无类型错误

- [ ] **Step 3: 前端单元测试**

```bash
cd frontend && npm test -- --watchAll=false
```

Expected: 全部 PASSED

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "feat: 停车精度测量与显示全链路实现"
```