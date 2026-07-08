"""WebSocket 集成测试（FastAPI TestClient）。

覆盖清单：
  - WS-CON-01  连接建立 + init_state 消息
  - WS-CON-02  多连接同时收到 init_state
  - WS-CTL-01  start → simulation_snapshot + simulation_status 广播
  - WS-CTL-02  step 推进仿真（通过 REST 验证副作用）
  - WS-CTL-03  pause 生命周期
  - WS-CTL-04  stop 生命周期
  - WS-CTL-05  reset 生命周期
  - WS-CTL-06  IDLE 下单步推进
  - WS-PRM-01  更新车辆运行时参数
  - WS-PRM-02  更新信号目标速度比
  - WS-DIS-01  断开连接后从管理器移除
  - WS-DIS-02  仿真运行时断连不崩溃
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sim_engine.app import app

client = TestClient(app)


# ==================== 辅助函数 ====================


def _reset() -> None:
    """重置仿真到 IDLE 状态。"""
    client.post("/api/v1/simulation/reset")


def _stop() -> None:
    """停止仿真。"""
    client.post("/api/v1/simulation/stop")


# ==================== Fixtures ====================


@pytest.fixture(autouse=True)
def _cleanup_after_test() -> None:
    """每个测试结束后清理仿真状态，避免测试间干扰。"""
    yield
    _stop()
    _reset()


# ==================== WS-CON: 连接管理 ====================


class TestWebSocketConnection:
    """WS-CON: 连接建立与初始化消息。"""

    def test_connect_receives_init_state(self) -> None:
        """WS-CON-01: 连接成功后立即收到 init_state 消息。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "init_state"
            assert "config" in msg
            assert "state" in msg
            assert msg["state"]["runState"] == "idle"
            # init_state 应包含完整配置
            assert "line" in msg["config"]
            assert "vehicle" in msg["config"]
            assert "simulation" in msg["config"]

    def test_multiple_connections_all_receive_init(self) -> None:
        """WS-CON-02: 多个连接各自收到独立的 init_state。"""
        _reset()
        with (
            client.websocket_connect("/ws") as ws1,
            client.websocket_connect("/ws") as ws2,
        ):
            msg1 = ws1.receive_json()
            msg2 = ws2.receive_json()
            assert msg1["type"] == "init_state"
            assert msg2["type"] == "init_state"
            assert msg1["state"]["runState"] == "idle"
            assert msg2["state"]["runState"] == "idle"


# ==================== WS-CTL: sim_control ====================


class TestWebSocketSimControl:
    """WS-CTL: sim_control 消息处理。"""

    def test_start_sends_snapshot(self) -> None:
        """WS-CTL-01: 发送 start 后收到 simulation_snapshot 和 simulation_status。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state

            ws.send_json({"type": "sim_control", "action": "start"})

            # 第一次广播：simulation_snapshot（后台异步循环在 step_once 后广播）
            snap = ws.receive_json()
            assert snap["type"] == "simulation_snapshot"
            assert "data" in snap
            assert "trains" in snap["data"]
            assert len(snap["data"]["trains"]) >= 1
            train = snap["data"]["trains"][0]
            assert "position" in train
            assert "speed" in train
            assert "mode" in train

            # 第二次广播：simulation_status (running)
            status = ws.receive_json()
            assert status["type"] == "simulation_status"
            assert status["data"]["runState"] == "running"

    def test_step_advances_clock(self) -> None:
        """WS-CTL-02: step 推进仿真一步（通过 REST 验证时钟推进）。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state

            resp = client.get("/api/v1/simulation/status")
            assert resp.status_code == 200
            initial_time = resp.json()["data"]["simulationTime"]

            ws.send_json({"type": "sim_control", "action": "step"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["simulationTime"] > initial_time

    def test_pause_changes_state(self) -> None:
        """WS-CTL-03: 运行中 pause 后状态变为 paused。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state
            ws.send_json({"type": "sim_control", "action": "start"})
            ws.receive_json()  # simulation_snapshot
            ws.receive_json()  # simulation_status (running)

            ws.send_json({"type": "sim_control", "action": "pause"})

            # 通过 REST 验证状态
            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["runState"] == "paused"

    def test_stop_from_running(self) -> None:
        """WS-CTL-04: 运行中 stop 后仿真停止。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state
            ws.send_json({"type": "sim_control", "action": "start"})
            ws.receive_json()  # simulation_snapshot
            ws.receive_json()  # simulation_status (running)

            ws.send_json({"type": "sim_control", "action": "stop"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["runState"] == "stopped"

    def test_reset_returns_to_idle(self) -> None:
        """WS-CTL-05: reset 后状态回到 idle。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state
            ws.send_json({"type": "sim_control", "action": "reset"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["runState"] == "idle"

    def test_step_from_idle(self) -> None:
        """WS-CTL-06: IDLE 状态下发送 step 仍可推进。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state

            resp = client.get("/api/v1/simulation/status")
            initial_time = resp.json()["data"]["simulationTime"]

            ws.send_json({"type": "sim_control", "action": "step"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["simulationTime"] > initial_time

    def test_pause_when_idle_no_crash(self) -> None:
        """IDLE 状态下 pause 不崩溃，状态保持不变。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state

            ws.send_json({"type": "sim_control", "action": "pause"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.json()["data"]["runState"] == "idle"

    def test_stop_when_idle_no_crash(self) -> None:
        """IDLE 状态下 stop 不崩溃（stop() 在任何状态下都会设为 stopped）。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()

            ws.send_json({"type": "sim_control", "action": "stop"})

            resp = client.get("/api/v1/simulation/status")
            assert resp.status_code == 200


# ==================== WS-PRM: param_update ====================


class TestWebSocketParamUpdate:
    """WS-PRM: param_update 消息处理。"""

    def test_update_vehicle_empty_mass(self) -> None:
        """WS-PRM-01: 更新车辆空载质量通过 REST 验证。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state

            ws.send_json({
                "type": "param_update",
                "params": {"vehicle": {"emptyMass": 220000}},
            })

            resp = client.get("/api/v1/params")
            assert resp.json()["data"]["vehicle"]["emptyMass"] == 220000

    def test_update_vehicle_max_brake_force(self) -> None:
        """更新车辆最大制动力。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()

            ws.send_json({
                "type": "param_update",
                "params": {"vehicle": {"maxBrakeForce": 400000}},
            })

            resp = client.get("/api/v1/params")
            assert resp.json()["data"]["vehicle"]["maxBrakeForce"] == 400000

    def test_update_signal_target_speed_ratio(self) -> None:
        """WS-PRM-02: 更新信号目标速度比。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()

            ws.send_json({
                "type": "param_update",
                "params": {"signal": {"targetSpeedRatio": 0.9}},
            })

            resp = client.get("/api/v1/params")
            assert resp.json()["data"]["signal"]["targetSpeedRatio"] == 0.9

    def test_partial_update_keeps_other_params(self) -> None:
        """部分更新不影响未涉及的参数。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()

            # 获取当前参数
            resp_before = client.get("/api/v1/params")
            davis_a_before = resp_before.json()["data"]["vehicle"]["davisA"]

            # 仅更新 maxSpeed
            ws.send_json({
                "type": "param_update",
                "params": {"vehicle": {"maxSpeed": 120}},
            })

            resp_after = client.get("/api/v1/params")
            assert resp_after.json()["data"]["vehicle"]["maxSpeed"] == 120
            # 其他参数不受影响
            assert resp_after.json()["data"]["vehicle"]["davisA"] == davis_a_before


# ==================== WS-DIS: 断开连接 ====================


class TestWebSocketDisconnect:
    """WS-DIS: 断开连接行为。"""

    def test_disconnect_cleans_up(self) -> None:
        """WS-DIS-01: 断开后连接从管理器移除，后续广播正常。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # init_state

        # 断开后，广播不再发给已断开连接，服务不崩溃
        # 通过 RPC 验证服务正常
        resp = client.get("/api/v1/simulation/status")
        assert resp.status_code == 200

    def test_disconnect_during_running_simulation(self) -> None:
        """WS-DIS-02: 仿真运行时断连不导致崩溃。"""
        _reset()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 丢弃 init_state
            ws.send_json({"type": "sim_control", "action": "start"})
            # 接收一帧确认启动成功
            ws.receive_json()

        # 断开后服务仍正常
        resp = client.get("/api/v1/simulation/status")
        assert resp.status_code == 200

    def test_reconnect_after_disconnect(self) -> None:
        """断开后重新连接能再次收到 init_state。"""
        _reset()
        # 第一次连接
        with client.websocket_connect("/ws") as ws1:
            msg1 = ws1.receive_json()
            assert msg1["type"] == "init_state"

        # 第二次连接
        with client.websocket_connect("/ws") as ws2:
            msg2 = ws2.receive_json()
            assert msg2["type"] == "init_state"
            assert msg2["state"]["runState"] == "idle"