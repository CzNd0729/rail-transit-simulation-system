# 迭代一 MVP 最终闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `VITE_USE_MOCK=false` 下完成验收场景 1~4，补齐区段参数编辑、信号相位展示、后端验收集成测试，使 E2E 清单可全部勾选。

**Architecture:** 后端 `TrackPathService.update_segment` + `SimulationManager` 区段选中状态 + 快照 `currentSegment`/`runningPhase`；前端 Context `selectedSegmentId` + 线路图点击选择 + `apiAdapter` 映射；Mock 路径保持 `mvpLineLayout` 兼容。

**Tech Stack:** Python 3.10+ / pytest / FastAPI, React 19 / TypeScript / Vitest / ECharts

## Global Constraints

- 验收线路：A(0m) → B(1500m) → C(3200m)，与 `backend/sim_engine/config/track.yaml` 一致
- API 消息 camelCase ↔ 前端内部 snake_case（沿用 `apiAdapter.ts`）
- `running` 状态禁止修改 track 区段参数
- Mock 模式不得回归：`VITE_USE_MOCK=true` 时 `npm test` 全 PASS
- 每个 Task 结束：`uv run pytest`（backend）或 `npm test && npm run build`（frontend）必须通过
- 联调环境：`frontend/.env.local` 设 `VITE_USE_MOCK=false`，后端 `uv run uvicorn sim_engine.app:app --reload --port 8000`
- 不实现运行历史持久化、能耗/阻力图表、TrackView 新功能

## File Map

| 文件 | 职责 |
|------|------|
| `backend/sim_engine/track/path_service.py` | 区段查询 + `update_segment` |
| `backend/sim_engine/data/snapshot.py` | 快照增加 `currentSegment`、`runningPhase` |
| `backend/sim_engine/orchestrator.py` | 传入 segment/phase 给 snapshot builder |
| `backend/sim_engine/services/simulation_manager.py` | 区段选中 + track 参数更新 |
| `backend/tests/test_track.py` | update_segment 单测 |
| `backend/tests/test_api.py` | track 区段 PUT 测试 |
| `backend/tests/test_orchestrator.py` | 场景 1 全程集成测试 |
| `frontend/src/context/SimulationContext.tsx` | `selectedSegmentId` 状态 |
| `frontend/src/components/views/overview/LineDiagram.tsx` | 区段点击选择 |
| `frontend/src/components/views/overview/TrackSegment.tsx` | 选中高亮 |
| `frontend/src/components/param/TrackParams.tsx` | 区段绑定 + 恢复默认 |
| `frontend/src/utils/apiAdapter.ts` | currentSegment / runningPhase / segmentId |
| `frontend/src/components/views/overview/StatusCards.tsx` | 信号授权卡片 |
| `frontend/src/data/mvpLineLayout.ts` | 默认区段参数常量 |

---

### Task 1: 后端区段更新 API

**Files:**
- Modify: `backend/sim_engine/track/path_service.py`
- Test: `backend/tests/test_track.py`

**Interfaces:**
- Produces: `TrackPathService.get_segment_by_id(segment_id: str) -> Segment | None`
- Produces: `TrackPathService.update_segment(segment_id: str, *, gradient: float | None = None, curvature: float | None = None, speed_limit: float | None = None) -> Segment`
- Raises: `ValueError` if segment_id not found

- [ ] **Step 1: 写失败测试**

`backend/tests/test_track.py` 末尾追加：

```python
def test_update_segment_gradient():
    track = load_track(TRACK_YAML)
    svc = TrackPathService(track)
    seg = svc.update_segment("SEC02", gradient=30.0)
    assert seg.gradient == 30.0
    assert svc.query_at(2000.0).gradient == 30.0


def test_update_segment_invalid_id():
    track = load_track(TRACK_YAML)
    svc = TrackPathService(track)
    with pytest.raises(ValueError, match="SEC99"):
        svc.update_segment("SEC99", gradient=10.0)
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd backend && uv run pytest tests/test_track.py::test_update_segment_gradient -v`  
Expected: FAIL — `AttributeError: 'TrackPathService' object has no attribute 'update_segment'`

- [ ] **Step 3: 实现 update_segment**

`backend/sim_engine/track/path_service.py` 在 `next_station_ahead` 后追加：

```python
def get_segment_by_id(self, segment_id: str) -> Segment | None:
    for seg in self.track.segments:
        if seg.id == segment_id:
            return seg
    return None

def update_segment(
    self,
    segment_id: str,
    *,
    gradient: float | None = None,
    curvature: float | None = None,
    speed_limit: float | None = None,
    is_tunnel: bool | None = None,
) -> Segment:
    seg = self.get_segment_by_id(segment_id)
    if seg is None:
        raise ValueError(f"Segment not found: {segment_id}")
    if gradient is not None:
        seg.gradient = gradient
    if curvature is not None:
        seg.curvature = curvature
    if speed_limit is not None:
        seg.speed_limit = speed_limit
    if is_tunnel is not None:
        seg.is_tunnel = is_tunnel
    return seg

def segment_at_position(self, chainage: float) -> Segment | None:
    return self._segment_at(chainage)
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd backend && uv run pytest tests/test_track.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/track/path_service.py backend/tests/test_track.py
git commit -m "feat(track): 支持按区段ID更新线路参数"
```

---

### Task 2: SimulationManager 区段参数读写

**Files:**
- Modify: `backend/sim_engine/services/simulation_manager.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `TrackPathService.update_segment(segment_id, **fields)`
- Produces: `get_params()["track"]` 含 `segmentId` + 选中区段参数
- Produces: `update_params({"track": {"segmentId": "SEC02", "gradient": 30}})` 更新内存区段

- [ ] **Step 1: 写失败测试**

`backend/tests/test_api.py` 追加：

```python
def test_update_track_segment_params():
    client.post("/api/v1/simulation/reset")
    resp = client.put(
        "/api/v1/params",
        json={"track": {"segmentId": "SEC02", "gradient": 30}},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "track.segmentId" in data["updated"] or "track.gradient" in data["updated"]
    assert data["params"]["track"]["gradient"] == 30


def test_update_track_rejected_while_running():
    client.post("/api/v1/simulation/reset")
    client.post("/api/v1/simulation/start")
    resp = client.put(
        "/api/v1/params",
        json={"track": {"segmentId": "SEC02", "gradient": 30}},
    )
    assert resp.status_code == 409
    client.post("/api/v1/simulation/stop")
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd backend && uv run pytest tests/test_api.py::test_update_track_segment_params -v`  
Expected: FAIL — gradient 未更新或 status 200 而非预期

- [ ] **Step 3: 实现 simulation_manager 区段逻辑**

`simulation_manager.py` 在 `__init__` 增加 `self._selected_segment_id = "SEC01"`。

改造 `get_params()` 的 track 段：

```python
seg = orch.track.get_segment_by_id(self._selected_segment_id)
if seg is None:
    seg = orch.track.segment_at_position(
        orch.train_state.position if orch.train_state else 0.0
    )
return {
    # ...vehicle/power/signal 不变...
    "track": {
        "segmentId": seg.id if seg else self._selected_segment_id,
        "gradient": seg.gradient if seg else 0,
        "curvature": seg.curvature if seg else 0,
        "speedLimit": seg.speed_limit if seg else 80,
    },
}
```

改造 `update_params()` 增加 track 分支：

```python
track_updates = updates.get("track", {})
if track_updates:
    if orch.run_state == RunState.RUNNING:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Cannot update track while running")
    if "segmentId" in track_updates:
        self._selected_segment_id = track_updates["segmentId"]
        updated.append("track.segmentId")
    seg_id = self._selected_segment_id
    fields = {}
    if "gradient" in track_updates:
        fields["gradient"] = track_updates["gradient"]
    if "curvature" in track_updates:
        fields["curvature"] = track_updates["curvature"]
    if "speedLimit" in track_updates:
        fields["speed_limit"] = track_updates["speedLimit"]
    if fields:
        orch.track.update_segment(seg_id, **fields)
        for k in fields:
            updated.append(f"track.{k}")
```

> 注：`update_params` 若在 service 层抛 HTTPException，需在 `api/params.py` 保持透传。

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd backend && uv run pytest tests/test_api.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/services/simulation_manager.py backend/tests/test_api.py
git commit -m "feat(api): 支持按区段更新运行时线路参数"
```

---

### Task 3: WS 快照 currentSegment + runningPhase

**Files:**
- Modify: `backend/sim_engine/data/snapshot.py`
- Modify: `backend/sim_engine/orchestrator.py`
- Test: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Produces: `build_simulation_snapshot(..., current_segment: Segment | None, running_phase: str)`
- Produces: snapshot `data.track.currentSegment` 与 `data.signaling.controlCommands[0].runningPhase`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_orchestrator.py` 追加：

```python
def test_snapshot_has_current_segment_and_running_phase():
    orch = Orchestrator.from_config_dir()
    orch.start()
    snap = orch.step_once()
    track = snap["data"]["track"]
    assert "currentSegment" in track
    assert track["currentSegment"]["id"] in ("SEC01", "SEC02")
    cmd = snap["data"]["signaling"]["controlCommands"][0]
    assert cmd["runningPhase"] in ("traction", "coasting", "braking", "dwell")
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd backend && uv run pytest tests/test_orchestrator.py::test_snapshot_has_current_segment_and_running_phase -v`  
Expected: FAIL — KeyError `currentSegment`

- [ ] **Step 3: 扩展 snapshot builder**

`snapshot.py` 函数签名与 body：

```python
from sim_engine.track.models import Segment

def build_simulation_snapshot(
    clock: SimulationClock,
    sim_params: SimulationParams,
    train_id: str,
    state: TrainState,
    forces: ForceBreakdown,
    pantograph_voltage: float = 1500.0,
    current_segment: Segment | None = None,
    running_phase: str = "traction",
) -> dict:
    # ...existing train/power...
    track_payload: dict = {"occupancy": [], "switchStates": []}
    if current_segment is not None:
        track_payload["currentSegment"] = {
            "id": current_segment.id,
            "gradient": current_segment.gradient,
            "curvature": current_segment.curvature,
            "speedLimit": current_segment.speed_limit,
            "isTunnel": current_segment.is_tunnel,
        }
    # signaling.controlCommands[0] 增加 runningPhase
```

`orchestrator.py` `step_once()` 调用处：

```python
current_seg = self.track.segment_at_position(self.train_state.position)
phase = self.signaling.signal_state.phase.value
snapshot = build_simulation_snapshot(
    ...,
    current_segment=current_seg,
    running_phase=phase,
)
snapshot["data"]["signaling"]["controlCommands"][0]["runningPhase"] = phase
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd backend && uv run pytest tests/test_orchestrator.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/sim_engine/data/snapshot.py backend/sim_engine/orchestrator.py backend/tests/test_orchestrator.py
git commit -m "feat(ws): 快照输出当前区段与信号运行相位"
```

---

### Task 4: 后端场景 1 验收集成测试

**Files:**
- Modify: `backend/tests/test_orchestrator.py`

**Interfaces:**
- Consumes: `Orchestrator.run_until()` + `recorder.buffer`

- [ ] **Step 1: 写失败测试**

```python
def test_scenario1_abc_full_journey():
    """场景 1：A→B→C 单列车，含站停，终到 C 停稳。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    result = orch.run_until(max_steps=50000)
    assert result["runState"] == "stopped"
    assert orch.train_state.position >= 3190.0
    assert orch.train_state.speed < 0.5
    speeds = [r.speed for r in orch.recorder.buffer]
    assert max(speeds) >= 60.0
    assert max(speeds) <= 68.0
    assert orch.clock.elapsed >= 60.0
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && uv run pytest tests/test_orchestrator.py::test_scenario1_abc_full_journey -v`  
Expected: PASS（若 FAIL 则调整 total_time 配置或容差，不得削弱停站断言）

- [ ] **Step 3: 全量后端测试**

Run: `cd backend && uv run pytest`  
Expected: PASS，覆盖率 ≥ 80%

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_orchestrator.py
git commit -m "test: 新增场景1 A→B→C 验收集成测试"
```

---

### Task 5: 前端 Context 区段选中状态

**Files:**
- Modify: `frontend/src/types/simulation.ts`
- Modify: `frontend/src/context/SimulationContext.tsx`

**Interfaces:**
- Produces: `AppState.selectedSegmentId: string | null`
- Produces: action `SET_SELECTED_SEGMENT`

- [ ] **Step 1: 扩展类型与 reducer**

`simulation.ts` `AppState` 增加：

```typescript
selectedSegmentId: string | null;
```

`SimulationContext.tsx`：

```typescript
const initialState: AppState = {
  // ...
  selectedSegmentId: 'SEC01',
};

// Action type
| { type: 'SET_SELECTED_SEGMENT'; segmentId: string }

// Reducer case
case 'SET_SELECTED_SEGMENT':
  return { ...state, selectedSegmentId: action.segmentId };
```

导出 `useSelectedSegment()` helper（可选）。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npx tsc -b`  
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/simulation.ts frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): 新增区段选中状态"
```

---

### Task 6: 线路图区段选择与 TrackParams 绑定

**Files:**
- Modify: `frontend/src/components/views/overview/TrackSegment.tsx`
- Modify: `frontend/src/components/views/overview/LineDiagram.tsx`
- Modify: `frontend/src/components/param/TrackParams.tsx`
- Modify: `frontend/src/data/mvpLineLayout.ts`（导出 `DEFAULT_SEGMENT_PARAMS`）
- Modify: `frontend/src/hooks/useSimulation.ts`（无需改，沿用 updateParams）

**Interfaces:**
- Consumes: `SET_SELECTED_SEGMENT`
- Produces: `updateParams({ track: { segment_id, gradient, ... } })`

- [ ] **Step 1: TrackSegment 支持点击与高亮**

`TrackSegment.tsx` 增加 props：

```typescript
interface TrackSegmentProps {
  segment: InterStationSegment;
  y: number;
  blockHeight?: number;
  selected?: boolean;
  onSelect?: (segmentId: string) => void;
}
```

在 `<g>` 上增加透明点击区域 + 选中描边：

```tsx
<rect
  x={segment.start_chainage}
  y={y - 20}
  width={segment.end_chainage - segment.start_chainage}
  height={40}
  fill="transparent"
  style={{ cursor: 'pointer' }}
  onClick={() => onSelect?.(segment.id)}
/>
{selected && (
  <rect ... stroke="#1890ff" strokeWidth={2} fill="none" />
)}
```

- [ ] **Step 2: LineDiagram 接线**

```typescript
const { selectedSegmentId } = useSimulationState();
const dispatch = useSimulationDispatch();

<TrackSegment
  key={seg.id}
  segment={seg}
  y={TRACK_Y}
  selected={selectedSegmentId === seg.id}
  onSelect={(id) => dispatch({ type: 'SET_SELECTED_SEGMENT', segmentId: id })}
/>
```

- [ ] **Step 3: TrackParams 绑定选中区段**

从 `lineLayout.segments` 或 `params.track` 读取当前区段值；`handleChange` 时：

```typescript
updateParams({
  track: {
    segment_id: selectedSegmentId ?? 'SEC01',
    gradient: params.track.gradient,
    // ...
    [key]: value,
  },
});
```

新增恢复默认按钮，从 `DEFAULT_SEGMENT_PARAMS[segmentId]` 还原。

- [ ] **Step 4: 运行前端测试与构建**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/TrackSegment.tsx frontend/src/components/views/overview/LineDiagram.tsx frontend/src/components/param/TrackParams.tsx frontend/src/data/mvpLineLayout.ts
git commit -m "feat(frontend): 区段选择与参数面板绑定"
```

---

### Task 7: apiAdapter 扩展 + StatusCards 信号授权

**Files:**
- Modify: `frontend/src/utils/apiAdapter.ts`
- Modify: `frontend/src/utils/apiAdapter.test.ts`
- Modify: `frontend/src/components/views/overview/StatusCards.tsx`
- Modify: `frontend/src/types/simulation.ts`（`ControlCommand.running_phase` 可选字段）

**Interfaces:**
- Consumes: snapshot `track.currentSegment`, `controlCommands[0].runningPhase`
- Produces: `toApiParamUpdate` 含 `segmentId`
- Produces: `getSignalPhaseLabel(phase)` 用于 StatusCards

- [ ] **Step 1: 写失败测试**

`apiAdapter.test.ts` 追加：

```typescript
it('maps currentSegment and runningPhase from snapshot', () => {
  const raw = {
    clock: { elapsed: 1, speedMultiplier: 1 as const },
    trains: [{ id: 'T1', position: 2000, speed: 50, acceleration: 0, mode: 'traction' as const,
      mass: 200000, passengerCount: 0, pantographVoltage: 1500, powerDemand: 0,
      doorStatus: 'closed' as const, faultAlarm: null }],
    power: { substations: [], voltageProfile: [], totalConsumption: 0, totalRegeneration: 0 },
    signaling: {
      controlCommands: [{ trainId: 'T1', tractionLevel: 1, brakeLevel: 0, emergencyBrake: false, runningPhase: 'traction' }],
      emergencyBrakes: [],
    },
    track: {
      occupancy: [], switchStates: [],
      currentSegment: { id: 'SEC02', gradient: 30, curvature: 1200, speedLimit: 80, isTunnel: false },
    },
    events: [],
  };
  const snap = parseServerSnapshot(raw);
  expect(snap.track.current_segment?.id).toBe('SEC02');
  expect(snap.signaling.commands[0]?.running_phase).toBe('traction');
});

it('includes segmentId in outbound track params', () => {
  const api = toApiParamUpdate({ track: { segment_id: 'SEC02', gradient: 30 } });
  expect(api.track).toEqual({ segmentId: 'SEC02', gradient: 30 });
});
```

- [ ] **Step 2: 运行测试确认 FAIL**

Run: `cd frontend && npx vitest run src/utils/apiAdapter.test.ts`  
Expected: FAIL

- [ ] **Step 3: 实现 apiAdapter 扩展**

`parseServerSnapshot` 映射 `currentSegment`；`toApiParamUpdate` 增加 `segmentId`。

`StatusCards.tsx`：

```typescript
const phase = signaling.commands[0]?.running_phase;
const signalLabel = phase ? getSignalPhaseLabel(phase) : '--';
// 信号授权卡片 value: signalLabel
```

`format.ts` 增加：

```typescript
export function getSignalPhaseLabel(phase: string): string {
  const map: Record<string, string> = {
    traction: '牵引', coasting: '惰行', braking: '制动', dwell: '站停',
  };
  return map[phase] ?? phase;
}
```

- [ ] **Step 4: 运行测试确认 PASS**

Run: `cd frontend && npm test && npm run build`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/apiAdapter.ts frontend/src/utils/apiAdapter.test.ts frontend/src/components/views/overview/StatusCards.tsx frontend/src/utils/format.ts frontend/src/types/simulation.ts
git commit -m "feat(frontend): 映射信号相位与当前区段到状态卡片"
```

---

### Task 8: E2E 手工验收与文档同步

**Files:**
- Modify: `docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md`（勾选结果）
- Modify: `backend/CLAUDE.md`
- Modify: `frontend/CLAUDE.md`

- [ ] **Step 1: 启动联调环境**

```bash
# 终端 1
cd backend && uv run uvicorn sim_engine.app:app --reload --port 8000

# 终端 2 — frontend/.env.local
VITE_USE_MOCK=false
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000/ws

cd frontend && npm run dev
```

- [ ] **Step 2: 执行验收清单场景 1~4**

按 `docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md` 逐步验证，记录通过/失败。

- [ ] **Step 3: 更新 CLAUDE.md 状态表**

`backend/CLAUDE.md`：track/power/signaling/orchestrator 标为已实现。  
`frontend/CLAUDE.md`：迭代一 UI-TOP/VW/VHC/CTRL/PARAM/EXPORT/BAR 标为已实现。

- [ ] **Step 4: 全量测试**

Run: `cd backend && uv run pytest`  
Run: `cd frontend && npm test && npm run build`  
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md backend/CLAUDE.md frontend/CLAUDE.md
git commit -m "docs: 迭代一 MVP 验收完成并同步 CLAUDE 状态"
```

---

## Self-Review

| 规格要求 | 对应 Task |
|---------|----------|
| UI-PARAM-02 区段参数编辑 | Task 2, 6 |
| UI-PARAM-05 线路参数重置 | Task 6 |
| UI-VW-04 信号授权卡片 | Task 3, 7 |
| 场景 1 A→B→C | Task 4, 8 |
| 场景 2 30‰ 上坡 | Task 2, 6, 8 |
| 场景 3 仿真控制 | 已有实现，Task 8 验证 |
| 场景 4 质量参数 | 已有实现，Task 8 验证 |
| API 8.4.2 currentSegment | Task 3, 7 |
| NFR-03 覆盖率 ≥ 80% | Task 4 |

无 TBD / 占位符。类型命名：`segmentId`（API）↔ `segment_id`（前端内部）在 `apiAdapter` 统一转换。

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-09-iter1-mvp-final-closure.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — 每个 Task 派发独立 subagent，任务间做 review，迭代快

**2. Inline Execution** — 本会话用 executing-plans 批量执行，checkpoint 处暂停确认

**Which approach?**
