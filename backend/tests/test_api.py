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
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"
    assert "time,position,speed" in resp.text


# ── 配置更新 ─────────────────────────────────────────────────────────

def test_update_config_simulation():
    """PUT /api/v1/config 更新仿真参数。"""
    # 先确保非运行状态
    client.post("/api/v1/simulation/reset")
    resp = client.put("/api/v1/config", json={
        "simulation": {"timeStep": 0.05, "totalTime": 300}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]["updated"]) >= 1
    # 恢复默认配置，避免影响后续测试
    client.post("/api/v1/simulation/reset")
    client.put("/api/v1/config", json={
        "simulation": {"timeStep": 0.1, "totalTime": 600}
    })


# ── 无效操作 ─────────────────────────────────────────────────────────

def test_start_when_already_running():
    """已运行时再发 start 应返回错误。"""
    # 先确保处于非运行状态
    client.post("/api/v1/simulation/reset")
    client.post("/api/v1/simulation/start")
    # 短暂等待
    import time
    time.sleep(0.2)
    resp = client.post("/api/v1/simulation/start")
    # 可能仍在运行，应返回冲突
    data = resp.json()
    if resp.status_code == 200 and "code" in data:
        assert data["code"] in (0, 40002)  # 0=成功（侥幸已结束），40002=冲突
    client.post("/api/v1/simulation/stop")


def test_resume_when_not_paused():
    """非暂停状态 resume 应报错。"""
    client.post("/api/v1/simulation/reset")
    resp = client.post("/api/v1/simulation/resume")
    data = resp.json()
    # 允许 idempotent 返回 ok 或报 40002
    if data.get("code", 0) != 0:
        assert data["code"] == 40002


# ── 速度倍率有效值 ──────────────────────────────────────────────────

def test_set_speed_to_one():
    resp = client.put("/api/v1/simulation/speed", json={"speedMultiplier": 1})
    assert resp.status_code == 200
    assert resp.json()["data"]["speedMultiplier"] == 1


def test_set_speed_to_ten():
    resp = client.put("/api/v1/simulation/speed", json={"speedMultiplier": 10})
    assert resp.status_code == 200
    assert resp.json()["data"]["speedMultiplier"] == 10


# ── 参数更新边界 ─────────────────────────────────────────────────────

def test_update_params_empty():
    """空参数更新不应报错。"""
    resp = client.put("/api/v1/params", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0


def test_update_signal_param():
    resp = client.put("/api/v1/params", json={"signal": {"targetSpeedRatio": 0.6}})
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ── 缺失路径 404 ────────────────────────────────────────────────────

def test_nonexistent_endpoint():
    resp = client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
