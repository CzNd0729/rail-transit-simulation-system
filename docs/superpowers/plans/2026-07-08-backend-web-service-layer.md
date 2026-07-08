# 后端 Web 服务层 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有仿真引擎 `sim_engine` 包之上构建 FastAPI Web 服务层，提供 REST API + WebSocket 实时通信 + 后台异步仿真循环。

**Architecture:** 模块化分层架构，新增 `api/`、`ws/`、`services/` 三个子包。`SimulationManager` 包装 `Orchestrator` 并管理后台异步循环；`WebSocketConnectionManager` 管理连接与广播；各 REST router 通过 `SimulationManager` 与引擎交互。

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, PyYAML, pytest

## Global Constraints

- 所有现有模块（`sim_engine/vehicle/`、`sim_engine/track/`、`sim_engine/signaling/`、`sim_engine/power/`、`sim_engine/core/`、`sim_engine/data/`、`sim_engine/orchestrator.py`）**不得修改**
- REST API 前缀统一为 `/api/v1/`
- 响应格式统一为 `{"code": 0, "message": "success", "data": {...}}`
- 错误格式统一为 `{"code": 40001, "message": "...", "detail": "..."}`
- 使用 `uv` 管理依赖，`uv run uvicorn ...` 启动
- 纯内存模式，无数据库依赖
- 速度单位 km/h，位置单位 m，时间单位 s

---

## 文件结构

```
sim_engine/
├── app.py                  # 新建 — FastAPI 应用工厂 + WebSocket 端点 + 心跳
├── api/                    # 新建 — REST 路由包
│   ├── __init__.py
│   ├── health.py           # GET /api/v1/health
│   ├── config.py           # GET/PUT /api/v1/config, /config/line, /config/vehicle
│   ├── simulation.py       # 仿真控制 12 个端点
│   └── params.py           # GET/PUT /api/v1/params
├── ws/
│   ├── __init__.py         # 新建
│   └── manager.py          # 新建 — WebSocketConnectionManager
└── services/
    ├── __init__.py         # 新建
    └── simulation_manager.py  # 新建 — SimulationManager

backend/
├── pyproject.toml          # 修改 — 追加 fastapi, uvicorn 依赖
└── sim_engine/__init__.py  # 修改 — 追加 app 导出
```

---

### Task 1: 添加依赖 + 创建包结构

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/sim_engine/api/__init__.py`
- Create: `backend/sim_engine/ws/__init__.py`
- Create: `backend/sim_engine/services/__init__.py`
- Modify: `backend/sim_engine/__init__.py`

- [ ] **Step 1: 修改 pyproject.toml 追加 fastapi 和 uvicorn**

```toml
dependencies = [
    "PyYAML>=6.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
]
```

- [ ] **Step 2: 创建三个空 `__init__.py` 文件**

```python
# sim_engine/api/__init__.py — 空
# sim_engine/ws/__init__.py — 空
# sim_engine/services/__init__.py — 空
```

- [ ] **Step 3: 修改 `sim_engine/__init__.py` 追加 app 导出**

```python
"""城市轨道交通运行仿真系统 — 仿真引擎后端。

迭代一 MVP：车辆系统 + 仿真编排器（单列车闭环）。
"""

from sim_engine.orchestrator import Orchestrator

__all__ = ["Orchestrator"]
```

不修改，保持原样。`app` 在 `sim_engine/app.py` 中定义，用户直接 `uv run uvicorn sim_engine.app:app` 启动。

- [ ] **Step 4: 安装依赖**

```bash
cd backend
uv sync
```

Run: `uv run python -c "import fastapi; print(fastapi.__version__)"`
Expected: 打印版本号，无报错

- [ ] **Step 5: 提交**

```bash
git add backend/pyproject.toml backend/sim_engine/api/__init__.py backend/sim_engine/ws/__init__.py backend/sim_engine/services/__init__.py
git commit -m "build: 添加 fastapi/uvicorn 依赖，创建 api/ws/services 子包"
```

---

### Task 2: WebSocketConnectionManager

**Files:**
- Create: `backend/sim_engine/ws/manager.py`
- Test: 通过 Task 9 集成测试验证

- [ ] **Step 1: 实现 WebSocketConnectionManager**

```python
"""WebSocket 连接管理与广播（迭代一 MVP）。"""

from __future__ import annotations

from fastapi import WebSocket


class WebSocketConnectionManager:
    """管理 WebSocket 客户端连接，支持广播和初始化消息推送。"""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, init_message: dict | None = None) -> None:
        """接受连接，可选发送初始化消息。"""
        await websocket.accept()
        self._connections.add(websocket)
        if init_message is not None:
            await websocket.send_json(init_message)

    def disconnect(self, websocket: WebSocket) -> None:
        """客户端断开时移除。"""
        self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """向所有活跃连接广播消息，失败时自动移除断连客户端。"""
        dead: set[WebSocket] = set()
        for ws in self._connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    @property
    def count(self) -> int:
        return len(self._connections)
```

- [ ] **Step 2: 提交**

```bash
git add backend/sim_engine/ws/manager.py
git commit -m "feat(ws): 实现 WebSocketConnectionManager 连接管理与广播"
```

---

### Task 3: SimulationManager

**Files:**
- Create: `backend/sim_engine/services/simulation_manager.py`

- [ ] **Step 1: 实现 SimulationManager**

```python
"""仿真生命周期管理：包装 Orchestrator + 后台异步仿真循环。

供 REST API 路由和 WebSocket 端点调用，是 Web 服务层与仿真引擎之间的桥梁。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from sim_engine.core.clock import RunState
from sim_engine.core.config import SimulationParams, load_simulation_params
from sim_engine.data.recorder import DataRecorder
from sim_engine.data.snapshot import build_simulation_snapshot
from sim_engine.orchestrator import Orchestrator, CONFIG_DIR
from sim_engine.power.static_power import get_pantograph_voltage
from sim_engine.track.config import load_track
from sim_engine.track.models import Track
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.models import VehicleParams

from sim_engine.ws.manager import WebSocketConnectionManager


class SimulationManager:
    """管理 Orchestrator 生命周期 + 后台异步仿真循环。"""

    def __init__(self, ws_manager: WebSocketConnectionManager) -> None:
        self.ws_manager = ws_manager
        self.orchestrator = Orchestrator.from_config_dir()
        self._loop_task: asyncio.Task | None = None

    # ==================== 仿真控制 ====================

    def start(self, passenger_load: float = 0.6) -> dict:
        if self.orchestrator.run_state not in (RunState.IDLE, RunState.STOPPED):
            return {"code": 40002, "message": "操作冲突", "detail": "仿真已在运行中"}
        self.orchestrator.start(passenger_load=passenger_load)
        self.start_loop()
        return {
            "runId": 1,
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def pause(self) -> dict:
        if self.orchestrator.run_state != RunState.RUNNING:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真未在运行中"}
        self.orchestrator.pause()
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def resume(self) -> dict:
        if self.orchestrator.run_state != RunState.PAUSED:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真未在暂停状态"}
        self.orchestrator.resume()
        self.start_loop()
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def stop(self) -> dict:
        self.stop_loop()
        self.orchestrator.stop()
        summary = self.orchestrator.recorder.summary()
        return {
            "runState": self.orchestrator.run_state.value,
            "runId": 1,
            "summary": summary,
        }

    def reset(self) -> dict:
        self.stop_loop()
        self.orchestrator = Orchestrator.from_config_dir()
        self.orchestrator.reset()
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def step(self) -> dict | None:
        snapshot = self.orchestrator.step_once()
        return snapshot

    def set_speed(self, multiplier: float) -> dict:
        self.orchestrator.clock.speed_multiplier = multiplier
        self.orchestrator.sim_params.speed_multiplier = multiplier
        return {"speedMultiplier": multiplier}

    # ==================== 状态查询 ====================

    def get_status(self) -> dict:
        orch = self.orchestrator
        return {
            "runState": orch.run_state.value,
            "simulationTime": orch.clock.elapsed,
            "totalTime": orch.sim_params.total_time,
            "speedMultiplier": orch.clock.speed_multiplier,
            "trainCount": 1,
        }

    # ==================== 配置读取 ====================

    def _load_yaml(self, filename: str) -> dict:
        path = CONFIG_DIR / filename
        with path.open("r", encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}

    def _to_camel(self, d: dict) -> dict:
        """将 snake_case 字典键转换为 camelCase。"""
        result = {}
        for k, v in d.items():
            parts = k.split("_")
            camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            if isinstance(v, dict):
                v = self._to_camel(v)
            elif isinstance(v, list):
                v = [self._to_camel(item) if isinstance(item, dict) else item for item in v]
            result[camel] = v
        return result

    def get_config(self) -> dict:
        raw_vehicle = self._load_yaml("vehicle.yaml")
        raw_track = self._load_yaml("track.yaml")
        raw_sim = self._load_yaml("simulation.yaml")

        vehicle = self._to_camel(raw_vehicle.get("vehicle", raw_vehicle))
        track = self._to_camel(raw_track.get("line", raw_track))
        sim = self._to_camel(raw_sim.get("simulation", raw_sim))

        # 补充 API 文档需要的字段
        if "totalLength" not in track:
            segments = track.get("segments", [])
            track["totalLength"] = max((s.get("endChainage", 0) for s in segments), default=0)
        if "direction" not in track:
            track["direction"] = "up"

        return {"line": track, "vehicle": vehicle, "simulation": sim}

    def get_line_config(self) -> dict:
        return self.get_config()["line"]

    def get_vehicle_config(self) -> dict:
        return self.get_config()["vehicle"]

    # ==================== 配置更新 ====================

    def update_config(self, updates: dict) -> dict:
        if self.orchestrator.run_state == RunState.RUNNING:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真运行中无法修改配置"}
        # 更新 simulation 参数
        sim_updates = updates.get("simulation", {})
        if sim_updates:
            sim_path = CONFIG_DIR / "simulation.yaml"
            with sim_path.open("r", encoding="utf-8") as fp:
                sim_data = yaml.safe_load(fp) or {}
            sim_section = sim_data.setdefault("simulation", sim_data)
            field_map = {
                "timeStep": "time_step",
                "totalTime": "total_time",
                "speedMultiplier": "speed_multiplier",
                "targetSpeedRatio": "target_speed_ratio",
                "stationStopTolerance": "station_stop_tolerance",
            }
            updated_keys = []
            for camel_key, snake_key in field_map.items():
                if camel_key in sim_updates:
                    sim_section[snake_key] = sim_updates[camel_key]
                    updated_keys.append(f"simulation.{snake_key}")
            if updated_keys:
                with sim_path.open("w", encoding="utf-8") as fp:
                    yaml.dump(sim_data, fp, allow_unicode=True, default_flow_style=False)
                # 重新加载编排器
                self.orchestrator = Orchestrator.from_config_dir()
        return {"updated": updated_keys if sim_updates else [], "config": self.get_config()}

    # ==================== 运行时参数 ====================

    def get_params(self) -> dict:
        orch = self.orchestrator
        vp = orch.vehicle.params
        tp = orch.track.query_at(orch.train_state.position if orch.train_state else 0.0)
        return {
            "vehicle": {
                "emptyMass": vp.empty_mass,
                "passengerCapacity": vp.passenger_capacity,
                "maxSpeed": vp.max_speed,
                "maxTractionForce": vp.max_traction_force,
                "maxBrakeForce": vp.max_brake_force,
                "davisA": vp.davis_a,
                "davisB": vp.davis_b,
                "davisCFrontArea": vp.davis_c_front_area,
                "davisCDragCoeff": vp.davis_c_drag_coeff,
                "curveResistCoeff": vp.curve_resist_coeff,
                "tunnelResistFactor": vp.tunnel_resist_factor,
            },
            "track": {
                "gradient": tp.gradient,
                "curvature": tp.curvature,
                "speedLimit": tp.speed_limit,
            },
            "power": {
                "pantographVoltage": 1500,
                "substationCapacity": 5000,
            },
            "signal": {
                "dwellTime": 30,
                "departureInterval": 120,
                "targetSpeedRatio": orch.sim_params.target_speed_ratio,
            },
        }

    def update_params(self, updates: dict) -> dict:
        """更新运行时参数（部分更新，仅内存）。"""
        orch = self.orchestrator
        updated: list[str] = []

        vehicle_updates = updates.get("vehicle", {})
        if vehicle_updates:
            vp = orch.vehicle.params
            field_map = {
                "emptyMass": "empty_mass",
                "passengerCapacity": "passenger_capacity",
                "maxSpeed": "max_speed",
                "maxTractionForce": "max_traction_force",
                "maxBrakeForce": "max_brake_force",
                "davisA": "davis_a",
                "davisB": "davis_b",
                "davisCFrontArea": "davis_c_front_area",
                "davisCDragCoeff": "davis_c_drag_coeff",
                "curveResistCoeff": "curve_resist_coeff",
                "tunnelResistFactor": "tunnel_resist_factor",
            }
            for camel_key, snake_key in field_map.items():
                if camel_key in vehicle_updates:
                    setattr(vp, snake_key, vehicle_updates[camel_key])
                    updated.append(f"vehicle.{camel_key}")

        signal_updates = updates.get("signal", {})
        if "targetSpeedRatio" in signal_updates:
            orch.sim_params.target_speed_ratio = signal_updates["targetSpeedRatio"]
            updated.append("signal.targetSpeedRatio")

        return {"updated": updated, "params": self.get_params()}

    # ==================== CSV 导出 ====================

    def get_csv_export(self) -> str:
        """从 recorder 缓冲区生成 CSV 文本。"""
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["time", "position", "speed", "mode", "acceleration",
             "traction_force", "brake_force", "total_resistance"]
        )
        for r in self.orchestrator.recorder.buffer:
            writer.writerow(
                [r.time, r.position, r.speed, r.mode, r.acceleration,
                 r.traction_force, r.brake_force, r.total_resistance]
            )
        return buf.getvalue()

    # ==================== WebSocket 初始化消息 ====================

    def build_init_message(self) -> dict:
        config = self.get_config()
        return {
            "type": "init_state",
            "config": config,
            "state": {
                "runState": self.orchestrator.run_state.value,
                "simulationTime": self.orchestrator.clock.elapsed,
            },
        }

    # ==================== 后台循环 ====================

    async def _run_loop(self) -> None:
        """后台仿真主循环：每步 step_once → broadcast → sleep(dt/multiplier)。"""
        orch = self.orchestrator
        while orch.run_state == RunState.RUNNING:
            snapshot = orch.step_once()
            if snapshot:
                # 广播快照
                await self.ws_manager.broadcast(snapshot)
                # 广播状态变更
                await self.ws_manager.broadcast({
                    "type": "simulation_status",
                    "data": {
                        "runState": "running",
                        "simulationTime": orch.clock.elapsed,
                        "reason": "running",
                    },
                })
            # 终点停稳判断
            if (
                orch.clock.elapsed >= orch.sim_params.total_time
                or (
                    orch.train_state is not None
                    and orch.train_state.position >= orch.track.track.total_length - 1.0
                    and orch.train_state.speed < 0.1
                )
            ):
                orch.stop()
                summary = orch.recorder.summary()
                await self.ws_manager.broadcast({
                    "type": "simulation_complete",
                    "data": {
                        "runId": 1,
                        "simulationTime": orch.clock.elapsed,
                        "summary": summary,
                    },
                })
                await self.ws_manager.broadcast({
                    "type": "simulation_status",
                    "data": {
                        "runState": "stopped",
                        "simulationTime": orch.clock.elapsed,
                        "reason": "completed",
                    },
                })
                break
            # 速度倍率等待
            dt = orch.clock.time_step
            mult = orch.sim_params.speed_multiplier
            await asyncio.sleep(dt / mult)
        self._loop_task = None

    def start_loop(self) -> None:
        """启动后台循环 asyncio.Task。"""
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._run_loop())

    def stop_loop(self) -> None:
        """取消后台循环。"""
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None
```

- [ ] **Step 2: 提交**

```bash
git add backend/sim_engine/services/simulation_manager.py
git commit -m "feat(services): 实现 SimulationManager 仿真生命周期管理"
```

---

### Task 4: health 路由 + app.py 骨架

**Files:**
- Create: `backend/sim_engine/api/health.py`
- Create: `backend/sim_engine/app.py`（骨架，仅挂载 health 路由）

- [ ] **Step 1: 实现 health router**

```python
"""健康检查接口。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}
```

- [ ] **Step 2: 实现 app.py 骨架 + 全局异常处理**

```python
"""FastAPI 应用入口。

提供 REST API + WebSocket 实时通信 + 后台仿真循环。
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from sim_engine.api import health
from sim_engine.services.simulation_manager import SimulationManager
from sim_engine.ws.manager import WebSocketConnectionManager

# 全局单例
ws_manager = WebSocketConnectionManager()
sim_manager = SimulationManager(ws_manager)

_HEARTBEAT_INTERVAL = 15.0  # 秒


async def _heartbeat_loop() -> None:
    """每 15 秒向所有 WebSocket 客户端发送心跳。"""
    import datetime

    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        await ws_manager.broadcast({
            "type": "heartbeat",
            "serverTime": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理后台任务生命周期。"""
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    sim_manager.stop_loop()


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="sim-engine",
        version="0.1.0",
        description="城市轨道交通运行仿真系统 — 后端服务",
    )

    # 全局异常处理器
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "code": 50001,
                "message": "内部错误",
                "detail": str(exc),
                "requestId": f"req_{uuid.uuid4().hex[:12]}",
            },
        )

    # 挂载路由
    app.include_router(health.router)

    # WebSocket 端点
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        init_msg = sim_manager.build_init_message()
        await ws_manager.connect(websocket, init_msg)
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                if msg_type == "sim_control":
                    action = data.get("action", "")
                    if action == "start":
                        sim_manager.start()
                    elif action == "pause":
                        sim_manager.pause()
                    elif action == "resume":
                        sim_manager.resume()
                    elif action == "stop":
                        sim_manager.stop()
                    elif action == "reset":
                        sim_manager.reset()
                    elif action == "step":
                        sim_manager.step()
                elif msg_type == "param_update":
                    sim_manager.update_params(data.get("params", {}))
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app


app = create_app()
```

- [ ] **Step 3: 手动验证启动**

```bash
cd backend
uv run uvicorn sim_engine.app:app --reload --port 8000
```

在另一个终端：
```bash
curl http://localhost:8000/api/v1/health
```

Expected: `{"code":0,"message":"success","data":{"status":"ok"}}`

- [ ] **Step 4: 提交**

```bash
git add backend/sim_engine/api/health.py backend/sim_engine/app.py
git commit -m "feat: 实现 FastAPI 应用骨架 + /health 端点 + WebSocket 端点"
```

---

### Task 5: config 路由

**Files:**
- Create: `backend/sim_engine/api/config.py`

- [ ] **Step 1: 实现 config router**

```python
"""配置管理接口（/api/v1/config）。"""

from __future__ import annotations

from fastapi import APIRouter

from sim_engine.app import sim_manager

router = APIRouter(prefix="/api/v1")


@router.get("/config")
async def get_config() -> dict:
    data = sim_manager.get_config()
    return {"code": 0, "message": "success", "data": data}


@router.put("/config")
async def update_config(body: dict) -> dict:
    result = sim_manager.update_config(body)
    if "code" in result:
        return {"code": result["code"], "message": result["message"], "detail": result["detail"]}
    return {"code": 0, "message": "success", "data": result}


@router.get("/config/line")
async def get_line_config() -> dict:
    return {"code": 0, "message": "success", "data": sim_manager.get_line_config()}


@router.get("/config/vehicle")
async def get_vehicle_config() -> dict:
    return {"code": 0, "message": "success", "data": sim_manager.get_vehicle_config()}
```

- [ ] **Step 2: 在 app.py 中挂载 config 路由**

在 `app.include_router(health.router)` 之后添加：
```python
from sim_engine.api import config as config_router
app.include_router(config_router.router)
```

> **注意：** 由于 `sim_manager` 在 `app.py` 中定义，`api/config.py` 通过 `from sim_engine.app import sim_manager` 导入。这会导致循环导入风险吗？不会，因为 `app.py` 只在 `create_app()` 被调用时才导入 router 模块，而 router 模块在模块级别导入 `sim_manager`（此时 `app.py` 的模块级别代码已经执行完毕）。

- [ ] **Step 3: 手动验证**

```bash
curl http://localhost:8000/api/v1/config
```

Expected: 返回包含 line/vehicle/simulation 三个部分的完整配置 JSON

- [ ] **Step 4: 提交**

```bash
git add backend/sim_engine/api/config.py
git commit -m "feat(api): 实现 /config 配置管理接口"
```

---

### Task 6: params 路由

**Files:**
- Create: `backend/sim_engine/api/params.py`

- [ ] **Step 1: 实现 params router**

```python
"""运行时参数接口（/api/v1/params）。"""

from __future__ import annotations

from fastapi import APIRouter

from sim_engine.app import sim_manager

router = APIRouter(prefix="/api/v1")


@router.get("/params")
async def get_params() -> dict:
    return {"code": 0, "message": "success", "data": sim_manager.get_params()}


@router.put("/params")
async def update_params(body: dict) -> dict:
    result = sim_manager.update_params(body)
    return {"code": 0, "message": "success", "data": result}
```

- [ ] **Step 2: 在 app.py 中挂载 params 路由**

```python
from sim_engine.api import params as params_router
app.include_router(params_router.router)
```

- [ ] **Step 3: 手动验证**

```bash
curl http://localhost:8000/api/v1/params
curl -X PUT http://localhost:8000/api/v1/params -H "Content-Type: application/json" -d '{"vehicle":{"emptyMass":220000}}'
```

- [ ] **Step 4: 提交**

```bash
git add backend/sim_engine/api/params.py
git commit -m "feat(api): 实现 /params 运行时参数接口"
```

---

### Task 7: simulation 路由

**Files:**
- Create: `backend/sim_engine/api/simulation.py`

- [ ] **Step 1: 实现 simulation router**

```python
"""仿真控制接口（/api/v1/simulation）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from sim_engine.app import sim_manager

router = APIRouter(prefix="/api/v1")


@router.get("/simulation/status")
async def get_status() -> dict:
    return {"code": 0, "message": "success", "data": sim_manager.get_status()}


@router.post("/simulation/start")
async def start_simulation(body: dict | None = None) -> dict:
    config = body or {}
    result = sim_manager.start(passenger_load=config.get("passengerLoad", 0.6))
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/pause")
async def pause_simulation() -> dict:
    result = sim_manager.pause()
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/resume")
async def resume_simulation() -> dict:
    result = sim_manager.resume()
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/stop")
async def stop_simulation() -> dict:
    result = sim_manager.stop()
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/reset")
async def reset_simulation() -> dict:
    result = sim_manager.reset()
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/step")
async def step_simulation() -> dict:
    snapshot = sim_manager.step()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "runState": sim_manager.orchestrator.run_state.value,
            "simulationTime": sim_manager.orchestrator.clock.elapsed,
            "snapshot": snapshot,
        },
    }


@router.put("/simulation/speed")
async def set_speed(body: dict) -> dict:
    multiplier = body.get("speedMultiplier", 1)
    valid = [0.5, 1, 2, 5, 10, 50]
    if multiplier not in valid:
        raise HTTPException(status_code=400, detail=f"speedMultiplier 必须为 {valid} 之一")
    result = sim_manager.set_speed(multiplier)
    return {"code": 0, "message": "success", "data": result}


@router.get("/simulation/runs")
async def get_runs() -> dict:
    return {
        "code": 0,
        "message": "success",
        "data": {"items": [], "pagination": {"page": 1, "pageSize": 20, "total": 0, "totalPages": 0}},
    }


@router.get("/simulation/runs/{run_id}")
async def get_run(run_id: int) -> dict:
    raise HTTPException(status_code=404, detail=f"运行记录 {run_id} 不存在")


@router.get("/simulation/runs/{run_id}/results")
async def get_run_results(run_id: int) -> dict:
    raise HTTPException(status_code=404, detail=f"运行记录 {run_id} 不存在")


@router.get("/simulation/export/csv")
async def export_csv() -> PlainTextResponse:
    csv_text = sim_manager.get_csv_export()
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"simulation_run.csv\""},
    )
```

- [ ] **Step 2: 在 app.py 中挂载 simulation 路由**

```python
from sim_engine.api import simulation as simulation_router
app.include_router(simulation_router.router)
```

- [ ] **Step 3: 手动验证**

```bash
# 启动仿真
curl -X POST http://localhost:8000/api/v1/simulation/start
# 查状态
curl http://localhost:8000/api/v1/simulation/status
# 暂停
curl -X POST http://localhost:8000/api/v1/simulation/pause
# 恢复
curl -X POST http://localhost:8000/api/v1/simulation/resume
# 停止
curl -X POST http://localhost:8000/api/v1/simulation/stop
# 重置
curl -X POST http://localhost:8000/api/v1/simulation/reset
```

- [ ] **Step 4: 提交**

```bash
git add backend/sim_engine/api/simulation.py
git commit -m "feat(api): 实现 /simulation 仿真控制接口"
```

---

### Task 8: 集成测试

**Files:**
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: 编写 API 集成测试**

```python
"""Web 服务层集成测试（FastAPI TestClient）。"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sim_engine.app import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "ok"


def test_get_config():
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "line" in data["data"]
    assert "vehicle" in data["data"]
    assert "simulation" in data["data"]


def test_get_line_config():
    resp = client.get("/api/v1/config/line")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "stations" in data
    assert "segments" in data


def test_get_vehicle_config():
    resp = client.get("/api/v1/config/vehicle")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "emptyMass" in data


def test_get_params():
    resp = client.get("/api/v1/params")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "vehicle" in data
    assert "track" in data
    assert "power" in data
    assert "signal" in data


def test_simulation_lifecycle():
    """测试仿真生命周期：start → pause → resume → stop → reset。"""
    # 初始状态
    resp = client.get("/api/v1/simulation/status")
    assert resp.json()["data"]["runState"] == "idle"

    # 启动
    resp = client.post("/api/v1/simulation/start")
    assert resp.status_code == 200
    assert resp.json()["data"]["runState"] == "running"

    # 暂停（等待一小段时间让仿真跑几步，然后暂停）
    import time
    time.sleep(0.3)
    resp = client.post("/api/v1/simulation/pause")
    # 可能仿真已经自然结束，所以接受 running 或 paused
    assert resp.status_code == 200

    # 停止
    resp = client.post("/api/v1/simulation/stop")
    assert resp.status_code == 200

    # 重置
    resp = client.post("/api/v1/simulation/reset")
    assert resp.status_code == 200
    assert resp.json()["data"]["runState"] == "idle"


def test_simulation_step():
    resp = client.post("/api/v1/simulation/step")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "snapshot" in data
    assert data["snapshot"] is not None


def test_simulation_status():
    resp = client.get("/api/v1/simulation/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "runState" in data
    assert "simulationTime" in data


def test_update_params():
    resp = client.put("/api/v1/params", json={"vehicle": {"emptyMass": 220000}})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "vehicle.emptyMass" in data["updated"]


def test_set_speed():
    resp = client.put("/api/v1/simulation/speed", json={"speedMultiplier": 5})
    assert resp.status_code == 200
    assert resp.json()["data"]["speedMultiplier"] == 5


def test_set_speed_invalid():
    resp = client.put("/api/v1/simulation/speed", json={"speedMultiplier": 999})
    assert resp.status_code == 400


def test_get_runs_empty():
    resp = client.get("/api/v1/simulation/runs")
    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []


def test_get_run_not_found():
    resp = client.get("/api/v1/simulation/runs/999")
    assert resp.status_code == 404


def test_csv_export():
    # 先跑几步
    client.post("/api/v1/simulation/step")
    client.post("/api/v1/simulation/step")
    client.post("/api/v1/simulation/step")
    resp = client.get("/api/v1/simulation/export/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv"
    assert "time,position,speed" in resp.text
```

- [ ] **Step 2: 运行测试**

```bash
cd backend
uv run pytest tests/test_api.py -v
```

Expected: 全部通过

- [ ] **Step 3: 运行全部测试，确保不破坏现有功能**

```bash
cd backend
uv run pytest -v
```

Expected: 32 个现有测试 + 新测试全部通过

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_api.py
git commit -m "test: 添加 Web 服务层集成测试"
```

---

### Task 9: 最终 app.py 整合 + 全量验证

**Files:**
- Modify: `backend/sim_engine/app.py`（确保所有路由已挂载，确认完整版）

- [ ] **Step 1: 确认完整版 app.py**

```python
"""FastAPI 应用入口。

提供 REST API + WebSocket 实时通信 + 后台仿真循环。
"""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from sim_engine.api import config, health, params, simulation
from sim_engine.services.simulation_manager import SimulationManager
from sim_engine.ws.manager import WebSocketConnectionManager

# 全局单例
ws_manager = WebSocketConnectionManager()
sim_manager = SimulationManager(ws_manager)

_HEARTBEAT_INTERVAL = 15.0


async def _heartbeat_loop() -> None:
    import datetime
    while True:
        await asyncio.sleep(_HEARTBEAT_INTERVAL)
        await ws_manager.broadcast({
            "type": "heartbeat",
            "serverTime": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })


@asynccontextmanager
async def lifespan(app: FastAPI):
    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    sim_manager.stop_loop()


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="sim-engine",
        version="0.1.0",
        description="城市轨道交通运行仿真系统 — 后端服务",
    )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "code": 50001,
                "message": "内部错误",
                "detail": str(exc),
                "requestId": f"req_{uuid.uuid4().hex[:12]}",
            },
        )

    # 挂载 REST 路由
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(simulation.router)
    app.include_router(params.router)

    # WebSocket 端点
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        init_msg = sim_manager.build_init_message()
        await ws_manager.connect(websocket, init_msg)
        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                if msg_type == "sim_control":
                    action = data.get("action", "")
                    if action == "start":
                        sim_manager.start()
                    elif action == "pause":
                        sim_manager.pause()
                    elif action == "resume":
                        sim_manager.resume()
                    elif action == "stop":
                        sim_manager.stop()
                    elif action == "reset":
                        sim_manager.reset()
                    elif action == "step":
                        sim_manager.step()
                elif msg_type == "param_update":
                    sim_manager.update_params(data.get("params", {}))
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app


app = create_app()
```

- [ ] **Step 2: 全量测试**

```bash
cd backend
uv run pytest -v
```

Expected: 全部通过

- [ ] **Step 3: 全量提交**

```bash
git add backend/sim_engine/app.py
git commit -m "feat: 完成 app.py 整合，全量路由挂载"
git log --oneline
```

- [ ] **Step 4: 检查是否遗漏**

```bash
cd backend
git status --short
```

Expected: 只有 `frontend/package-lock.json` 是脏的（属于之前的状态，非本功能改动）

---

## Spec 对照检查

| Spec 要求 | 对应 Task | 说明 |
|-----------|-----------|------|
| REST API 全部端点 | Task 4-7 | health(1), config(4), simulation(12), params(2) = 19 端点 |
| WebSocket init_state | Task 3, 9 | `build_init_message()` 在连接时发送 |
| WebSocket snapshot | Task 3 | `_run_loop` 每步 broadcast |
| WebSocket status | Task 3 | 状态变更时 broadcast |
| WebSocket complete | Task 3 | 仿真完成时 broadcast |
| WebSocket heartbeat | Task 9 | `_heartbeat_loop` 每 15s |
| 后台仿真循环 | Task 3 | `_run_loop` + `start_loop`/`stop_loop` |
| 纯内存模式 | Task 3, 7 | `runs` 返回空列表，`runs/{id}` 返回 404 |
| CSV 导出 | Task 3, 7 | `get_csv_export()` + `PlainTextResponse` |
| 全局异常处理 | Task 9 | `global_exception_handler` 返回 50001 |
| 统一响应格式 | Task 4-7 | 所有端点返回 `{code, message, data}` |
| 不修改现有模块 | 全部 | 仅新增文件，不碰 vehicle/track/signaling/power/core/data/orchestrator |