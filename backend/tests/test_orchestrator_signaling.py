"""编排器信号集成测试（ATP/ATS snapshot）。"""

from __future__ import annotations


def test_overspeed_triggers_eb_in_snapshot(orchestrator):
    orch = orchestrator
    orch.start()
    orch.train_state.speed = 200.0
    snap = orch.step_once()
    cmd = snap["data"]["signaling"]["controlCommands"][0]
    assert cmd["emergencyBrake"] is True


def test_snapshot_has_signaling_extended_fields(orchestrator):
    orch = orchestrator
    orch.start()
    snap = orch.step_once()
    sig = snap["data"]["signaling"]
    cmd = sig["controlCommands"][0]
    assert cmd["runningPhase"] in ("traction", "coasting", "braking", "dwell")
    assert len(sig["speedLimits"]) == 1
    assert "atpLimit" in sig["speedLimits"][0]
    assert len(sig["maProfile"]) == 1
    assert "maEndChainage" in sig["maProfile"][0]
    assert "timetableDeviation" in sig


def test_late_arrival_timetable_deviation_in_snapshot(orchestrator):
    """晚点到站第二站时 snapshot 输出时刻表偏离。"""
    orch = orchestrator
    orch.start()
    orch.clock.elapsed = 130.0
    orch.train_state.position = 1099.5
    orch.train_state.speed = 0.0
    snap = orch.step_once()
    dev_list = snap["data"]["signaling"]["timetableDeviation"]
    assert len(dev_list) >= 1
    dev = dev_list[0]
    assert dev["stationId"] == "ST02"
    assert dev["delayArrival"] > 0
    assert dev["adjustedDwell"] > dev["nominalDwell"]
    assert orch.signaling.signal_state.dwell_remaining > dev["nominalDwell"]
