# 迭代一 MVP 最终闭环 — 设计规格

> 日期：2026-07-09  
> 状态：待评审  
> 前置：E2E 验收闭环（7e64bee）、车辆联调（21c87da）、后端 Web 服务层（dev）

## 1. 背景与现状

### 1.1 迭代一目标（摘自 `docs/迭代一_MVP需求文档.md`）

在最短时间内跑通「单列车 A 站→B 站→C 站」完整仿真闭环，前后端联合验证场景 1~4。

### 1.2 已完成（截至 2026-07-09）

| 层级 | 内容 | 证据 |
|------|------|------|
| 后端核心引擎 | 轨道/车辆/供电/信号/编排器/记录器 | `backend/sim_engine/`，178+ pytest |
| 后端 API | REST 生命周期 + WS 推送 + CSV 导出 | `api/`, `ws/manager.py` |
| 前端 UI | 综合/车辆视图、控制面板、ECharts、线路图 | `frontend/src/` |
| 前后端适配 | `apiAdapter`、bootstrap、lineLayoutAdapter | `21c87da`, `7e64bee` |
| Mock 回放 | 离线演示完整可用 | `VITE_USE_MOCK=true` 默认 |

### 1.3 剩余差距（阻塞验收签字）

对照 `docs/迭代一_MVP需求文档.md` 与 `docs/superpowers/specs/2026-07-08-iter1-mvp-e2e-acceptance-checklist.md`：

| # | 差距 | 需求编号 | 影响场景 |
|---|------|---------|---------|
| G1 | 后端不支持按区段 ID 更新坡度/曲率/限速 | UI-PARAM-02、TRK | 场景 2（30‰ 上坡）Live 模式失败 |
| G2 | WS 快照缺少 `track.currentSegment`（API 8.4.2 已定义） | UI-VW-01 | 综合视图 Live 区段参数不同步 |
| G3 | 信号运行相位未暴露给前端 | UI-VW-04 | 状态卡片「信号授权」硬编码「正常」 |
| G4 | 线路参数无「恢复默认」 | UI-PARAM-05 | 场景 2 后无法一键还原 |
| G5 | 前端无区段选择交互 | UI-PARAM-02 | 参数面板编辑的是全局值，非「选中区段」 |
| G6 | 后端缺验收级集成测试 | 场景 1 | `test_full_run` 仅检查接近终点，未验证停站/对标 |
| G7 | `backend/frontend/CLAUDE.md` 状态表过时 | 文档 | 误导后续开发 |

### 1.4 明确不在本迭代范围

- 运行历史 API（`/simulation/runs` 持久化）— stub 可保留
- VHC-09 能耗计算、UI-VHC-04/05 阻力/能耗图表
- TrackView / PowerView / SignalView 新功能（迭代二/三）
- 隐藏 TopBar 多余视图标签（可选打磨，非阻塞）

---

## 2. 目标

**在 `VITE_USE_MOCK=false` 下，使验收清单场景 1~4 全部可勾选通过，Mock 模式行为不回归。**

成功标准：

1. 用户在线路图上选中 SEC02，将坡度改为 30‰，纵断面图更新，重跑后 B→C 运行时间变长
2. 综合视图「信号授权」卡片显示当前运行相位（牵引/惰行/制动/站停）
3. 后端集成测试断言 A→B→C 全程：牵引至 ~64 km/h、B/C 站停 30s、终到 C 停稳
4. `uv run pytest` 与 `npm test` 全部 PASS

---

## 3. 方案对比

### 方案 A：前后端联合补齐区段参数 + 信号相位（推荐）

后端扩展 `PUT /params` 与 WS 快照；前端增加区段选择与适配层映射。一次性闭合 G1~G6。

- **优点**：与 `API接口文档.md` 8.4.2 `track.currentSegment` 对齐；Live/Mock 共用 UI
- **缺点**：需同时改 backend + frontend

### 方案 B：仅前端 Mock 补丁

Mock 模式已有 SEC02 坡度覆盖（`mvpLineLayout.ts`），只补 Live 前端展示，不改后端。

- **优点**：改动小
- **缺点**：**无法通过 Live 验收场景 2/4**；与 API 文档不一致

### 方案 C：拆成两个子项目先后交付

先后端区段 API（G1/G2/G6），再前端区段选择（G5/G4/G3）。

- **优点**：可分批 review
- **缺点**：中间态无法完整验收；本差距规模适合单 PR

**推荐方案 A。**

---

## 4. 架构设计

### 4.1 区段参数数据流

```
用户点击线路图区段
    → Context.selectedSegmentId = "SEC02"
    → TrackParams 显示该区段 gradient/curvature/speed_limit
    → updateParams({ track: { segment_id, gradient } })
    → WS param_update / REST PUT /params
    → simulation_manager.update_params()
    → TrackPathService.update_segment("SEC02", gradient=30)
    → 下一步 query_at() 使用新坡度
    → snapshot.track.currentSegment 反映变更
    → lineLayoutAdapter 更新 profileSegments → 纵断面图刷新
```

### 4.2 后端变更

#### 4.2.1 `TrackPathService` 新增方法

```python
def get_segment_by_id(self, segment_id: str) -> Segment | None
def update_segment(self, segment_id: str, **fields) -> Segment  # gradient/curvature/speed_limit/is_tunnel
def segment_at_position(self, chainage: float) -> Segment | None  # 包装 _segment_at
```

#### 4.2.2 `SimulationManager` 状态

- `_selected_segment_id: str` — 默认 `"SEC01"`，可由 `PUT /params` 的 `track.segmentId` 设置
- `get_params()` — `track` 返回选中区段参数（非列车当前位置）
- `update_params()` — 支持：

```json
{
  "track": {
    "segmentId": "SEC02",
    "gradient": 30,
    "curvature": 1200,
    "speedLimit": 80
  }
}
```

- 仿真 `running` 时拒绝修改 track 参数（返回 409 或忽略并记录 warning）

#### 4.2.3 WS 快照扩展（对齐 API 8.4.2）

`build_simulation_snapshot()` 增加参数 `current_segment: Segment | None` 与 `running_phase: str`：

```json
"track": {
  "occupancy": [],
  "switchStates": [],
  "currentSegment": {
    "id": "SEC02",
    "gradient": 30,
    "curvature": 1200,
    "speedLimit": 80,
    "isTunnel": false
  }
},
"signaling": {
  "controlCommands": [{
    "trainId": "TRAIN_01",
    "tractionLevel": 1.0,
    "brakeLevel": 0,
    "emergencyBrake": false,
    "runningPhase": "traction"
  }],
  "emergencyBrakes": []
}
```

`runningPhase` 取值：`traction` | `coasting` | `braking` | `dwell`（来自 `ThreeStageController.signal_state.phase`）。

#### 4.2.4 验收集成测试

新增 `test_scenario1_abc_full_journey`：

- 从配置启动，跑至 C 站停稳（position ≥ 3199, speed < 0.1）
- 断言途中最高速度 ∈ [60, 68] km/h（0.8×80 容差）
- 断言 recorder 中存在 B 站（chainage ≈ 1500）与 C 站停稳记录
- 断言总仿真时间 > 60s（含两次 30s 站停）

### 4.3 前端变更

#### 4.3.1 Context 扩展

```typescript
interface AppState {
  selectedSegmentId: string | null;
  // ...
}
```

Action：`SET_SELECTED_SEGMENT`

#### 4.3.2 区段选择 UI

- `LineDiagram.tsx`：`TrackSegment` 点击 → `setSelectedSegment(seg.id)`
- 选中区段高亮边框（`TrackSegment` 新增 `selected` prop）
- `ParamPanel` 标题显示当前区段 ID

#### 4.3.3 TrackParams 改造

- 读取 `selectedSegmentId` + `lineLayout.segments` 显示对应参数
- `updateParams` 携带 `segment_id`（snake_case 内部 → camelCase `segmentId` 出站）
- 新增「恢复默认」按钮：从 `mvpLineLayout` / `track.yaml` 默认值还原当前区段

#### 4.3.4 apiAdapter 扩展

- `parseServerSnapshot`：映射 `track.currentSegment` → 更新 `params.track` 与 `profileSegments`
- `parseServerSnapshot`：读取 `controlCommands[0].runningPhase` → `signaling.commands[0].running_phase`
- `toApiParamUpdate`：增加 `segmentId` 字段

#### 4.3.5 StatusCards

「信号授权」卡片显示 `runningPhase` 中文标签（牵引/惰行/制动/站停），无数据时显示 `--`。

### 4.4 Mock 模式兼容

- Mock 路径继续使用 `mvpLineLayout.buildProfileSegments(gradient)` 覆盖 SEC02
- `selectedSegmentId` 在 Mock 下同样驱动 `TrackParams` 与纵断面
- `npm test` 现有 mock 测试不得破坏

---

## 5. 错误处理

| 场景 | 行为 |
|------|------|
| 无效 segmentId | 后端返回 400，`updated` 为空 |
| running 状态改 track | 后端拒绝，HTTP 409 |
| 未选中区段 | 前端默认选中第一个 segment |
| WS 快照无 currentSegment | 前端 fallback 到 params.track |

---

## 6. 测试策略

| 层 | 内容 |
|----|------|
| 后端单元 | `test_track.py` 新增 update_segment；`test_api.py` 新增 track 区段更新 |
| 后端集成 | `test_orchestrator.py` 场景 1 全程 |
| 前端单元 | `apiAdapter.test.ts` currentSegment/runningPhase；`lineLayoutAdapter.test.ts` 不变 |
| 前端组件 | `TrackParams` 区段绑定（可选 vitest） |
| 手工 | 按 `iter1-mvp-e2e-acceptance-checklist.md` 勾选场景 1~4 |

---

## 7. 文档同步

验收通过后更新：

- `backend/CLAUDE.md` — 轨道/信号/编排器标为「已实现」
- `frontend/CLAUDE.md` — 迭代一功能表标为「已实现」

---

## 8. 自审清单

- [x] 无 TBD / 占位符
- [x] 与 `API接口文档.md` 8.4.2 `currentSegment` 一致
- [x] 范围聚焦单 PR，不含运行历史持久化
- [x] Mock 与 Live 双路径明确
- [x] 场景 1~4 均可追溯到具体任务
