"""配置管理接口（/api/v1/config）。"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


def _get_sim_manager():
    from sim_engine.app import sim_manager
    return sim_manager


@router.get("/config")
async def get_config() -> dict:
    data = _get_sim_manager().get_config()
    return {"code": 0, "message": "success", "data": data}


@router.put("/config")
async def update_config(body: dict) -> dict:
    result = _get_sim_manager().update_config(body)
    if "code" in result:
        return {"code": result["code"], "message": result["message"], "detail": result["detail"]}
    return {"code": 0, "message": "success", "data": result}


@router.get("/config/line")
async def get_line_config() -> dict:
    return {"code": 0, "message": "success", "data": _get_sim_manager().get_line_config()}


@router.get("/config/vehicle")
async def get_vehicle_config() -> dict:
    return {"code": 0, "message": "success", "data": _get_sim_manager().get_vehicle_config()}