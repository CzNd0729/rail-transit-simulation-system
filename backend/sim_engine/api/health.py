"""健康检查接口。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict:
    return {"code": 0, "message": "success", "data": {"status": "ok"}}