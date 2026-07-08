"""FastAPI 应用入口。
提供 REST API + WebSocket 实时通信 + 后台仿真循环。"""

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