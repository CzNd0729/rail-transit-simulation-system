"""仿真控制接口（/api/v1/simulation）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/v1")


def _get_sim_manager():
    from sim_engine.app import sim_manager
    return sim_manager


@router.get("/simulation/status")
async def get_status() -> dict:
    return {"code": 0, "message": "success", "data": _get_sim_manager().get_status()}


@router.post("/simulation/start")
async def start_simulation(body: dict | None = None) -> dict:
    config = body or {}
    result = _get_sim_manager().start(passenger_load=config.get("passengerLoad", 0.6))
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/pause")
async def pause_simulation() -> dict:
    result = await _get_sim_manager().pause()
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/resume")
async def resume_simulation() -> dict:
    result = _get_sim_manager().resume()
    if "code" in result:
        raise HTTPException(status_code=409, detail=result["detail"])
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/stop")
async def stop_simulation() -> dict:
    result = await _get_sim_manager().stop()
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/reset")
async def reset_simulation() -> dict:
    result = _get_sim_manager().reset()
    return {"code": 0, "message": "success", "data": result}


@router.post("/simulation/step")
async def step_simulation() -> dict:
    sim = _get_sim_manager()
    snapshot = sim.step()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "runState": sim.orchestrator.run_state.value,
            "simulationTime": sim.orchestrator.clock.elapsed,
            "snapshot": snapshot,
        },
    }


@router.put("/simulation/speed")
async def set_speed(body: dict) -> dict:
    multiplier = body.get("speedMultiplier", 1)
    valid = [0.5, 1, 2, 5, 10, 50]
    if multiplier not in valid:
        raise HTTPException(status_code=400, detail=f"speedMultiplier 必须为 {valid} 之一")
    result = _get_sim_manager().set_speed(multiplier)
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
    csv_text = _get_sim_manager().get_csv_export()
    return PlainTextResponse(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=\"simulation_run.csv\""},
    )