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