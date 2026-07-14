"""FastAPI 应用入口。
提供 REST API + WebSocket 实时通信 + 后台仿真循环。

支持两种启动模式:
  - 常规模式: 仅对接前端（默认）
  - 外部系统模式: 额外连接 PLC/网络屏/信号屏硬件

由 __main__.py 通过环境变量 SIM_ENGINE_EXTERNAL 控制。
"""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sim_engine.api import config, health, params, scenarios, simulation
from sim_engine.services.simulation_manager import SimulationManager
from sim_engine.ws.manager import WebSocketConnectionManager

# 全局单例
ws_manager = WebSocketConnectionManager()

# 读取外部系统模式标志（由 __main__.py 设置）
_external_mode = os.environ.get("SIM_ENGINE_EXTERNAL", "0") == "1"
sim_manager = SimulationManager(ws_manager, external_mode=_external_mode)

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
    # 启动后打印服务连接信息
    mode_label = "外部系统模式" if _external_mode else "常规模式"
    port = _get_port()
    display_host = os.environ.get("SIM_ENGINE_HOST", "localhost")
    print(f"\n  ✅ 仿真引擎已启动 [{mode_label}]")
    print(f"  REST API:   http://{display_host}:{port}")
    print(f"  WebSocket:  ws://{display_host}:{port}/ws")
    print(f"  API 文档:   http://{display_host}:{port}/docs\n")

    heartbeat_task = asyncio.create_task(_heartbeat_loop())
    yield
    heartbeat_task.cancel()
    sim_manager.stop_loop()
    print("  仿真引擎已关闭")


def _get_port() -> int:
    """从环境变量或默认值获取监听端口。"""
    raw = os.environ.get("SIM_ENGINE_PORT", "8000")
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 8000


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title="sim-engine",
        version="0.1.0",
        description="城市轨道交通运行仿真系统 — 后端服务",
    )

    # CORS 配置 — 允许前端 dev server 跨域访问
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
    app.include_router(config.router)
    app.include_router(params.router)
    app.include_router(simulation.router)
    app.include_router(scenarios.router)

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
                        await sim_manager.pause()
                    elif action == "resume":
                        sim_manager.resume()
                    elif action == "stop":
                        await sim_manager.stop()
                    elif action == "reset":
                        sim_manager.reset()
                    elif action == "step":
                        sim_manager.step()
                elif msg_type == "param_update":
                    sim_manager.update_params(data.get("params", {}))
                elif msg_type == "manual_control":
                    eb = data.get("emergencyBrake")
                    if eb is not None:
                        sim_manager.set_emergency_brake(eb)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app


app = create_app()