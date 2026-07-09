"""运行时参数接口（/api/v1/params）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1")


def _get_sim_manager():
    from sim_engine.app import sim_manager
    return sim_manager


@router.get("/params")
async def get_params() -> dict:
    return {"code": 0, "message": "success", "data": _get_sim_manager().get_params()}


@router.put("/params")
async def update_params(body: dict) -> dict:
    result = _get_sim_manager().update_params(body)
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}