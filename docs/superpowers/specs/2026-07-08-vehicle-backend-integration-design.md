# 车辆系统前后端联调 — 设计规格

> 日期：2026-07-08  
> 状态：待评审  
> 前置：Mock 参数化轨迹（9523745）、后端 Web 服务层（dev 分支）

## 1. 背景与现状

### 已完成

| 层级 | 内容 |
|------|------|
| 后端 VHC-01~07 | 动力学、牵引曲线、Davis/坡度/弯道/隧道阻力、限速 — `backend/sim_engine/vehicle/` |
| 后端 API | REST + WebSocket 快照推送 — `simulation_manager.py` |
| 前端 UI-VHC-01~03 | 速度/加速度曲线、工况指示 — **Mock 模式下完整可用** |
| 前端 Mock | 参数化轨迹生成、回放器、chartHistory |

### 缺口（迭代一 MVP 验收阻塞项）

1. **`VITE_USE_MOCK=false` 时车辆视图无法正常工作** — WS 快照 camelCase 与前端 snake_case 不兼容
2. **启动时不拉取后端参数** — 始终用 `DEFAULT_VEHICLE_PARAMS`
3. **出站消息格式不匹配** — `param_update` 字段命名、倍率控制未走后端已有 REST
4. **生命周期消息未处理** — `init_state` / `simulation_status` / `simulation_complete`
5. **工况 `stopped`** — 后端停车态，前端 `ModeIndicator` 无对应样式
6. **CSV 导出** — UI 已有，Mock 模式下不可用（需真实仿真录制）

### 明确不在本迭代范围

- UI-VHC-04 阻力分解、UI-VHC-05 能耗累计（需求文档标注后续迭代）
- VHC-09 能耗计算逻辑
- Mock 与后端物理完全对齐（VHC-05/06/08 差异修复 — 另开任务）
- 手动驾驶 / 司机台 WS 消息

## 2. 目标

**在 `VITE_USE_MOCK=false` 时，车辆视图 UI-VHC-01~03 + 控制面板 + CSV 导出，能驱动后端真实仿真引擎完成 MVP 验收场景 1（A→B→C 单列车）。**

Mock 模式保持不变，作为离线开发 fallback。

## 3. 方案对比

### 方案 A：前端适配层（推荐）

在前端增加 API 适配器，统一处理 camelCase ↔ 内部类型；扩展 `useWebSocket` 消息分发；启动时 REST 引导参数。

- 优点：改动集中在前端，不阻塞后端发布；Mock 与 Live 共用 UI 组件
- 缺点：适配层需维护与 API 文档同步

### 方案 B：后端改 snake_case

后端 snapshot 改为 snake_case 与前端类型一致。

- 优点：前端零适配
- 缺点：与 `API接口文档.md` 8.4 节 camelCase 约定冲突；影响已有测试与文档

### 方案 C：继续深化 Mock

补齐 mock VHC-05/06/08，暂不对接后端。

- 优点：演示效果可控
- 缺点：**无法完成迭代一 MVP 真实联调验收**；与团队后端进度脱节

**推荐方案 A。**

## 4. 架构

```
Backend (camelCase WS/REST)
        │
        ▼
  apiAdapter.ts          ← 入站：snapshot/init_state/params
  outboundAdapter.ts     ← 出站：param_update 等
        │
        ▼
  SimulationContext      ← 现有 snake_case 状态
        │
        ▼
  VehicleView 组件       ← 无需改动数据消费方式
```

### 4.1 入站适配 (`parseServerSnapshot`)

| API 字段 (camelCase) | 内部字段 (snake_case) |
|----------------------|------------------------|
| speedMultiplier | speed_multiplier |
| passengerCount | passenger_count |
| pantographVoltage | pantograph_voltage |
| powerDemand | power_demand |
| doorStatus | door_status |
| faultAlarm | fault_alarm |
| mode: "stopped" | mode: "coasting" + speed=0（或扩展 TrainMode） |

### 4.2 出站适配 (`toApiParams`)

`SimulationParams` snake_case → API camelCase（`empty_mass` → `emptyMass` 等），仅映射 MVP 已支持字段。

### 4.3 倍率控制

`SpeedSelector` 改为调用 `PUT /api/v1/simulation/speed`（已有 REST），成功后更新本地 `clock.speed_multiplier`。Mock 模式仍走 `useMockReplay.setSpeedMultiplier`。

### 4.4 启动引导

`App` 或专用 `useBootstrapConfig` hook：

1. 若 `USE_MOCK` → 跳过
2. 否则 `GET /api/v1/params` + 可选 `GET /config/vehicle`
3. `dispatch({ type: 'INIT_PARAMS', payload })`

### 4.4 WebSocket 消息扩展

| 消息 | 动作 |
|------|------|
| init_state | 写入 config/params 初始状态 |
| simulation_snapshot | 经适配器 → RUNTIME_UPDATE |
| simulation_status | 更新 runState |
| simulation_complete | runState → stopped |

## 5. 组件影响

| 文件 | 变更 |
|------|------|
| `utils/apiAdapter.ts` | 新建 — 入站/出站转换 |
| `hooks/useWebSocket.ts` | 扩展消息处理 |
| `hooks/useBootstrap.ts` | 新建 — REST 引导 |
| `hooks/useSimulation.ts` | param 发送走 outbound 适配 |
| `components/control/SpeedSelector.tsx` | REST 倍率 |
| `components/views/vehicle/ModeIndicator.tsx` | 支持 stopped / 零速展示 |
| `types/simulation.ts` | TrainMode 增加 `stopped`；ServerMessage 扩展 |
| `App.tsx` | 挂载 bootstrap hook |

**不改动：** `mock/*`、`useMockReplay.ts`、曲线组件数据读取逻辑。

## 6. 测试策略

1. **单元测试** — `apiAdapter.test.ts`：snapshot/params 往返转换
2. **组件测试** — ModeIndicator stopped 态
3. **手动 E2E** — 后端 `uvicorn` + 前端 `VITE_USE_MOCK=false`，验收：
   - 启动后曲线实时更新
   - 倍率切换生效
   - 参数修改后下次 start 反映（或 WS param_update 即时反映）
   - CSV 导出非空

## 7. 验收标准

- [ ] `VITE_USE_MOCK=false` 时 UI-VHC-01~03 正常显示后端数据
- [ ] 工况指示器在停车时显示「停稳」或 stopped 态
- [ ] 仿真控制（启停暂停单步）与后端状态同步
- [ ] 倍率 1×/5×/10× 通过 REST 生效
- [ ] CSV 导出可下载含 time/position/speed/acceleration 的文件
- [ ] `VITE_USE_MOCK=true` 行为与现网一致（回归）
- [ ] `npm test` 全通过

## 8. 后续迭代（不在本文范围）

| 优先级 | 内容 |
|--------|------|
| P1 | Mock 补齐 VHC-05/06，站台 ±1m 对标 |
| P2 | UI-VHC-04 阻力分解（消费 snapshot 中 tractionForce/totalResistance） |
| P2 | UI-VHC-05 能耗累计（依赖 VHC-09 后端） |
| P3 | 多列车快照 |
