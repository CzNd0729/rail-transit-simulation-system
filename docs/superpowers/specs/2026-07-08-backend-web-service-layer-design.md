# 后端 Web 服务层设计文档

> 版本号: v1.0
> 日期: 2026-07-08
> 基于《详细设计文档》和《API 接口文档》编写，为迭代一 MVP 提供 REST + WebSocket 服务层实现方案。

---

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| v1.0 | 2026-07-08 | Claude | 初版发布 |

---

## 1. 概述

### 1.1 目标

在现有仿真引擎 `sim_engine` 包之上，构建 FastAPI Web 服务层，提供：
- REST API（配置管理、仿真控制、参数编辑、数据导出、健康检查）
- WebSocket 实时通信（仿真快照推送、状态变更通知、心跳）
- 后台异步仿真循环（按速度倍率自动推进仿真）

### 1.2 范围

**迭代一 MVP 实现范围：**
- REST API：全部端点实现，运行记录和预设方案相关返回空列表/404
- WebSocket：`init_state`、`simulation_snapshot`、`simulation_status`、`simulation_complete`、`heartbeat`
- 后台仿真循环：支持 start/pause/resume/stop，速度倍率控制
- 数据持久化：纯内存模式（无数据库），仿真结果通过 CSV 导出

**非范围（后续迭代实现）：**
- 数据库持久化（迭代二）
- 参数预设方案管理（迭代三）
- 手动驾驶控制（迭代三）
- 事件查询（迭代二）
- 司机台通信接口（迭代三）

### 1.3 依赖

```toml
# pyproject.toml 追加
dependencies = [
    "PyYAML>=6.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
]
```

---

## 2. 整体架构

```
┌──────────────────────────────────────────────────────────┐
│                    FastAPI Application                     │
│                                                           │
│  ┌───────────────┐  ┌──────────────────┐  ┌───────────┐  │
│  │  REST Routers  │  │  WebSocket       │  │ 后台定时  │  │
│  │  (api/*.py)   │  │  Endpoint (/ws)  │  │ 任务(心跳)│  │
│  └───────┬───────┘  └────────┬─────────┘  └───────────┘  │
│          │                   │                             │
│          └─────────┬─────────┘                             │
│                    │                                       │
│           ┌────────▼────────┐                              │
│           │ SimulationManager │                            │
│           │ (services/sim_mgr)│                            │
│           └────────┬────────┘                              │
│                    │                                       │
│           ┌────────▼────────┐                              │
│           │  Orchestrator   │  ← 现有模块，不动           │
│           │  (现有 orc.py)  │                              │
│           └─────────────────┘                              │
│                    │                                       │
│     ┌──────────────┼──────────────┐                        │
│     ▼              ▼              ▼                        │
│  VehicleSystem  TrackPath  ThreeStage  ...                │
│                   (现有模块，全部不动)                       │
└──────────────────────────────────────────────────────────┘
```

### 2.1 新增文件结构

```
sim_engine/
├── app.py                  # FastAPI 应用工厂 create_app()
├── api/                    # REST 路由模块
│   ├── __init__.py
│   ├── config.py           # /api/v1/config 相关 (4 个端点)
│   ├── simulation.py       # /api/v1/simulation 相关 (12 个端点)
│   ├── params.py           # /api/v1/params 相关 (2 个端点)
│   └── health.py           # /api/v1/health (1 个端点)
├── ws/
│   ├── __init__.py
│   └── manager.py          # WebSocketConnectionManager
└── services/
    ├── __init__.py
    └── simulation_manager.py  # SimulationManager
```

### 2.2 现有模块（完全不动）

```
sim_engine/
├── orchestrator.py      ✅ 不动，只 import 使用
├── vehicle/             ✅ 不动
├── track/               ✅ 不动
├── signaling/           ✅ 不动
├── power/               ✅ 不动
├── core/                ✅ 不动
├── data/                ✅ 不动
└── config/              ✅ 不动（YAML 配置文件）

backend/
└── examples/            ✅ 不动
```

---

## 3. 核心模块设计

### 3.1 SimulationManager

**文件：** `sim_engine/services/simulation_manager.py`

负责 Orchestrator 的包装和后台异步仿真循环的生命周期管理。

```python
class SimulationManager:
    orchestrator: Orchestrator
    _loop_task: asyncio.Task | None

    def __init__(self, ws_manager: WebSocketConnectionManager):
        self.orchestrator = Orchestrator.from_config_dir()
        self._ws_manager = ws_manager
        self._loop_task = None

    # 控制指令
    def start(self, passenger_load=0.6) -> dict: ...
    def pause(self) -> dict: ...
    def resume(self) -> dict: ...
    def stop(self) -> dict: ...
    def reset(self) -> dict: ...
    def step(self) -> dict | None: ...
    def set_speed(self, multiplier: float) -> dict: ...

    # 后台循环
    async def _run_loop(self):
        """每步 step_once() → broadcast → sleep(dt/multiplier)"""
        while self.orchestrator.run_state == RunState.RUNNING:
            snapshot = self.orchestrator.step_once()
            await self._ws_manager.broadcast({
                "type": "simulation_snapshot",
                "timestamp": self.orchestrator.clock.elapsed,
                "data": snapshot["data"],
            })
            # 终点停稳判断
            if self._should_stop():
                self.orchestrator.stop()
                await self._broadcast_complete()
                break
            # 速度倍率等待
            dt = self.orchestrator.clock.time_step
            mult = self.orchestrator.sim_params.speed_multiplier
            await asyncio.sleep(dt / mult)

    def start_loop(self):
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._run_loop())

    def stop_loop(self):
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None
```

**生命周期状态转换：**

| REST 操作 | 前状态 | 后状态 | 后台循环 |
|-----------|--------|--------|----------|
| start | idle | running | 启动 |
| pause | running | paused | 循环自然退出（while 条件不满足） |
| resume | paused | running | 重新启动 |
| stop | 任意 | stopped | 取消 |
| reset | 任意 | idle | 取消 |

### 3.2 WebSocketConnectionManager

**文件：** `sim_engine/ws/manager.py`

管理 WebSocket 客户端连接，支持广播和初始化消息推送。

```python
class WebSocketConnectionManager:
    _connections: set[WebSocket]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.add(websocket)
        # 发送 init_state
        await websocket.send_json(build_init_message(orchestrator))

    def disconnect(self, websocket: WebSocket):
        self._connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    async def broadcast_status(self, run_state: str, sim_time: float, reason: str):
        await self.broadcast({
            "type": "simulation_status",
            "data": {"runState": run_state, "simulationTime": sim_time, "reason": reason},
        })
```

### 3.3 app.py

**文件：** `sim_engine/app.py`

FastAPI 应用工厂，挂载路由和 WebSocket 端点。

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sim_engine.ws.manager import WebSocketConnectionManager
from sim_engine.services.simulation_manager import SimulationManager

ws_manager = WebSocketConnectionManager()
sim_manager = SimulationManager(ws_manager)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动心跳后台任务，关闭时清理循环。"""
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    sim_manager.stop_loop()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, title="sim-engine", version="0.1.0")
    # 挂载 REST 路由
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(simulation.router)
    app.include_router(params.router)
    # WebSocket 端点
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                _handle_ws_message(data)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
    return app

app = create_app()
```

**启动方式：**
```bash
uv run uvicorn sim_engine.app:app --reload --host 0.0.0.0 --port 8000
```

---

## 4. REST API 路由明细

### 4.1 health.py — `/api/v1/health`

| 方法 | 路径 | 行为 |
|------|------|------|
| GET | `/api/v1/health` | `{"code": 0, "message": "success", "data": {"status": "ok"}}` |

### 4.2 config.py — `/api/v1/config`

| 方法 | 路径 | 行为 | 迭代一实现 |
|------|------|------|-----------|
| GET | `/api/v1/config` | 读取三个 YAML 文件，组装为完整配置对象 | 完整实现 |
| PUT | `/api/v1/config` | 接收部分更新，写入 YAML（不允许 running 时修改） | 完整实现 |
| GET | `/api/v1/config/line` | 仅返回线路配置部分 | 完整实现 |
| GET | `/api/v1/config/vehicle` | 仅返回车辆配置部分 | 完整实现 |

**PUT /config 的校验规则：**
- 仿真运行中（run_state == running）返回 409 错误
- `timeStep` 必须为正数，`totalTime` 必须 ≥ 0
- `speedMultiplier` 必须在 `[0.5, 1, 2, 5, 10, 50]` 中

### 4.3 simulation.py — `/api/v1/simulation`

| 方法 | 路径 | 行为 |
|------|------|------|
| GET | `/api/v1/simulation/status` | 返回当前运行状态、仿真时间、速度倍率等 |
| POST | `/api/v1/simulation/start` | 启动仿真 + 启动后台循环 |
| POST | `/api/v1/simulation/pause` | 暂停仿真 |
| POST | `/api/v1/simulation/resume` | 恢复仿真 |
| POST | `/api/v1/simulation/stop` | 停止仿真 + 取消后台循环 |
| POST | `/api/v1/simulation/reset` | 重置仿真到初始状态 |
| POST | `/api/v1/simulation/step` | 单步执行一次仿真 |
| PUT | `/api/v1/simulation/speed` | 设置速度倍率 |
| GET | `/api/v1/simulation/runs` | 返回空列表（纯内存模式，暂无记录） |
| GET | `/api/v1/simulation/runs/{runId}` | 返回 404（暂无记录） |
| GET | `/api/v1/simulation/runs/{runId}/results` | 返回 404（暂无记录） |
| GET | `/api/v1/simulation/export/csv` | 调用 recorder.export_csv 返回 CSV 文本 |

**POST /simulation/start 行为：**
1. 如果当前状态为 idle，调用 `manager.start()`
2. 启动后台循环 `manager.start_loop()`
3. 返回 `{runId: 1, runState: "running", simulationTime: 0}`

### 4.4 params.py — `/api/v1/params`

| 方法 | 路径 | 行为 |
|------|------|------|
| GET | `/api/v1/params` | 从 Orchestrator 读取当前运行时参数 |
| PUT | `/api/v1/params` | 更新运行时参数（部分更新） |

---

## 5. WebSocket 通信协议

### 5.1 端点

```
ws://localhost:8000/ws
```

### 5.2 服务端 → 客户端消息

| 消息类型 | 触发时机 | 说明 |
|----------|---------|------|
| `init_state` | 客户端连接成功后立即发送 | 包含线路/车辆/仿真配置 + 当前运行状态 |
| `simulation_snapshot` | 每仿真步计算完成后 | 全量快照（列车/信号/供电/轨道） |
| `simulation_status` | 运行状态变更时 | 如 running → paused，含 reason 字段 |
| `simulation_complete` | 仿真自然完成时 | 含 summary（总距离、平均速度等） |
| `heartbeat` | 每 15 秒 | 仅含 serverTime |

### 5.3 客户端 → 服务端消息

| 消息类型 | 行为 |
|----------|------|
| `{"type": "sim_control", "action": "start"}` | 启动仿真 |
| `{"type": "sim_control", "action": "pause"}` | 暂停仿真 |
| `{"type": "sim_control", "action": "resume"}` | 恢复仿真 |
| `{"type": "sim_control", "action": "stop"}` | 停止仿真 |
| `{"type": "sim_control", "action": "reset"}` | 重置仿真 |
| `{"type": "sim_control", "action": "step"}` | 单步执行 |
| `{"type": "param_update", "params": {...}}` | 更新运行时参数 |

---

## 6. 错误处理

### 6.1 统一响应格式

**成功：**
```json
{"code": 0, "message": "success", "data": {...}}
```

**错误：**
```json
{"code": 40001, "message": "参数验证失败", "detail": "time_step 必须为正数", "requestId": "req_xxx"}
```

### 6.2 错误码

| code | message | HTTP 状态码 | 触发条件 |
|------|---------|-------------|----------|
| 0 | success | 200 | 请求成功 |
| 40001 | 参数验证失败 | 400 | 参数值不合法 |
| 40002 | 操作冲突 | 409 | 仿真未在运行中 / 已在运行中 |
| 40003 | 配置不完整 | 400 | 缺少必要配置项 |
| 40004 | 资源不存在 | 404 | 运行记录 ID 不存在 |
| 50001 | 内部错误 | 500 | 未捕获异常 |

### 6.3 全局异常处理器

在 `app.py` 中注册全局异常处理器，捕获所有未处理异常，返回 50001 错误。

---

## 7. 启动方式

```bash
# 开发模式（热重载）
cd backend
uv run uvicorn sim_engine.app:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uv run uvicorn sim_engine.app:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 8. 测试策略

### 8.1 单元测试

- `SimulationManager` 的 start/pause/resume/stop/reset/step 各状态转换
- `WebSocketConnectionManager` 的 connect/disconnect/broadcast
- 各 REST 路由的响应格式和错误码
- 后台循环的启动和取消

### 8.2 集成测试

- 使用 `TestClient` (FastAPI 的测试客户端) 测试完整 REST API
- 模拟 WebSocket 连接，验证消息推送

### 8.3 手动测试

```bash
# 启动服务
uv run uvicorn sim_engine.app:app --reload --port 8000

# 测试健康检查
curl http://localhost:8000/api/v1/health

# 测试启动仿真
curl -X POST http://localhost:8000/api/v1/simulation/start

# 测试获取状态
curl http://localhost:8000/api/v1/simulation/status
```

---

## 9. 后续迭代扩展点

| 迭代 | 扩展内容 | 影响文件 |
|------|---------|---------|
| 二 | 数据库持久化（SQLite） | 新增 `data/database.py`，修改 simulation.py |
| 二 | 事件查询 `/events` | 新增 `api/events.py` |
| 三 | 参数预设管理 | 扩展 `api/params.py` |
| 三 | 手动驾驶控制 | 新增 `api/control.py` |
| 三 | 司机台通信接口 | 新增 `api/drivercab.py` |
| 三 | 多列车支持 | 修改 `simulation_manager.py` |

---

## 附录 A：与现有代码的接口映射

| REST API | Orchestrator 方法 | 数据来源 |
|----------|------------------|---------|
| GET /config | — | 读取 YAML 文件 |
| GET /simulation/status | `orch.run_state`, `orch.clock.elapsed` | 直接读取属性 |
| POST /simulation/start | `orch.start()` | 调用方法 |
| POST /simulation/step | `orch.step_once()` | 调用方法，返回快照 |
| POST /simulation/stop | `orch.stop()` | 调用方法 |
| GET /simulation/export/csv | `orch.recorder.export_csv()` | 调用方法 |
| GET /params | `orch.vehicle.params` 等 | 从各子系统读取 |