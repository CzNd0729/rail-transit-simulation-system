"""方案保存/加载/对比接口（/api/v1/scenarios）。

方案存储为 backend/sim_engine/data/scenarios/*.json，
使用 json 标准库读写，不引入数据库。"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from sim_engine.core.clock import RunState

router = APIRouter(prefix="/api/v1")
SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


def _get_sim_manager():
    from sim_engine.app import sim_manager
    return sim_manager


def _ensure_dir() -> None:
    """确保 scenarios 目录存在。"""
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)


def _file_path(scenario_id: str) -> Path:
    return SCENARIOS_DIR / f"{scenario_id}.json"


def _generate_id() -> str:
    """生成方案 ID：scenario_<日期>_<序号>"""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    existing = list(SCENARIOS_DIR.glob(f"scenario_{date_str}_*.json"))
    seq = len(existing) + 1
    return f"scenario_{date_str}_{seq:03d}"


def _read_scenario(scenario_id: str) -> dict:
    """读取方案 JSON 文件，不存在时抛 404。"""
    path = _file_path(scenario_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"方案 {scenario_id} 不存在")
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"方案数据异常: {e}")


def _write_scenario(data: dict) -> None:
    """写入方案 JSON 文件。"""
    _ensure_dir()
    path = _file_path(data["id"])
    try:
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"方案保存失败: {e}")


def _list_scenarios() -> list[dict]:
    """扫描 scenarios 目录，按创建时间倒序返回所有方案摘要。"""
    _ensure_dir()
    items: list[dict] = []
    for path in sorted(SCENARIOS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True):
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            items.append({
                "id": data.get("id", path.stem),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "createdAt": data.get("createdAt", ""),
                "totalTime": data.get("result", {}).get("totalTime"),
                "netEnergy": data.get("result", {}).get("netEnergy"),
                "avgSpeed": data.get("result", {}).get("avgSpeed"),
                "maxSpeed": data.get("result", {}).get("maxSpeed"),
            })
        except (json.JSONDecodeError, OSError):
            # 损坏文件跳过
            continue
    return items


# ==================== API 端点 ====================


@router.get("/scenarios")
async def list_scenarios() -> dict:
    """获取所有方案摘要列表。"""
    return {"code": 0, "message": "success", "data": {"scenarios": _list_scenarios()}}


@router.post("/scenarios")
async def save_scenario(body: dict) -> dict:
    """保存当前参数+仿真结果为方案。

    请求体: { name, description? }
    要求引擎处于 IDLE/STOPPED 状态，且至少运行过一次仿真。
    """
    sim = _get_sim_manager()
    orch = sim.orchestrator

    # 校验引擎状态
    if orch.run_state == RunState.RUNNING:
        raise HTTPException(status_code=409, detail="仿真运行中无法保存方案，请先暂停或停止仿真")
    if orch.run_state == RunState.PAUSED:
        raise HTTPException(status_code=409, detail="仿真暂停中无法保存方案，请先停止仿真")

    # 校验是否有仿真结果
    sn = sim.get_last_snapshot()
    summary = sim._last_summary  # 由 stop() 或 _run_loop() 设置
    if summary is None:
        raise HTTPException(status_code=400, detail="请先运行一次仿真后再保存方案")

    # 收集参数
    params = sim.get_params()

    # 收集仿真配置
    sim_config = orch.sim_params
    config_section = {
        "trainCount": sim_config.train_count,
        "bidirectional": sim_config.bidirectional,
    }

    # 收集运行统计
    stats = sim.get_run_stats()

    # 提取结果指标
    power_data = sn.get("data", {}).get("power", {}) if sn else {}
    traction_energy = power_data.get("totalConsumption", 0.0)  # kWh
    regen_energy = power_data.get("totalRegeneration", 0.0)  # kWh
    net_energy = round(traction_energy - regen_energy, 4)

    result = {
        "totalTime": round(summary.get("total_time", 0.0), 2),
        "totalDistance": round(summary.get("max_position", 0.0), 2),
        "avgSpeed": round(summary.get("avg_speed", 0.0), 2),
        "maxSpeed": round(summary.get("max_speed", 0.0), 2),
        "tractionEnergy": round(traction_energy, 4),
        "regenEnergy": round(regen_energy, 4),
        "netEnergy": net_energy,
        "minVoltage": round(stats["minVoltage"], 2),
        "peakPower": round(stats["peakPower"], 2),
    }

    # 组装方案
    scenario_id = _generate_id()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scenario = {
        "id": scenario_id,
        "name": body.get("name", "").strip(),
        "description": body.get("description", "").strip(),
        "createdAt": now,
        "params": {
            "vehicle": params.get("vehicle", {}),
            "signal": params.get("signal", {}),
            "power": params.get("power", {}),
            "simulation": config_section,
        },
        "result": result,
    }

    if not scenario["name"]:
        raise HTTPException(status_code=400, detail="方案名称不能为空")

    _write_scenario(scenario)
    return {"code": 0, "message": "success", "data": {"id": scenario_id, "name": scenario["name"]}}


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str) -> dict:
    """获取方案完整详情。"""
    data = _read_scenario(scenario_id)
    return {"code": 0, "message": "success", "data": data}


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str) -> dict:
    """删除方案。"""
    path = _file_path(scenario_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"方案 {scenario_id} 不存在")
    try:
        path.unlink()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"方案删除失败: {e}")
    return {"code": 0, "message": "success", "data": {"success": True}}


@router.put("/scenarios/{scenario_id}/apply")
async def apply_scenario(scenario_id: str) -> dict:
    """加载方案参数到当前引擎。

    1. 读取方案 JSON
    2. 重置引擎
    3. 逐项写入参数
    4. 返回当前配置给前端刷新
    """
    sim = _get_sim_manager()
    orch = sim.orchestrator

    if orch.run_state == RunState.RUNNING:
        raise HTTPException(status_code=409, detail="仿真运行中无法加载方案，请先暂停或停止仿真")

    data = _read_scenario(scenario_id)
    params = data.get("params", {})

    # 1. 重置引擎
    sim.reset()

    # 2. 应用 simulation 配置（写入 YAML）
    sim_cfg = params.get("simulation", {})
    if sim_cfg:
        camel_map = {
            "trainCount": "trainCount",
            "bidirectional": "bidirectional",
        }
        sim_updates: dict = {}
        for key in ("trainCount", "bidirectional"):
            if key in sim_cfg:
                sim_updates[key] = sim_cfg[key]
        if sim_updates:
            sim.update_config({"simulation": sim_updates})

    # 3. 应用 vehicle / signal / track 参数（内存更新）
    runtime_updates: dict = {}
    if "vehicle" in params:
        runtime_updates["vehicle"] = params["vehicle"]
    if "signal" in params:
        runtime_updates["signal"] = params["signal"]
    if "track" in params:
        runtime_updates["track"] = params["track"]
    if runtime_updates:
        sim.update_params(runtime_updates)

    # 4. 返回当前配置
    return {"code": 0, "message": "success", "data": {"config": sim.get_config()}}
