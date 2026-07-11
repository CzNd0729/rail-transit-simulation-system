"""ATPController 单元测试（单列车 SIG-04）。"""

from __future__ import annotations

from sim_engine.core.config import AtpConfig
from sim_engine.signaling.atp import ATPController
from sim_engine.signaling.models import SafetyStatus


def test_overspeed_triggers_eb():
    atp = ATPController(AtpConfig(overspeed_margin=0.05))
    limit = 80.0
    assert atp.check_overspeed(84.0, limit) == SafetyStatus.NORMAL
    assert atp.check_overspeed(84.1, limit) == SafetyStatus.EMERGENCY_BRAKE


def test_ma_end_is_target_station():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    profile = atp.build_ma_profile("T1", train_position=500.0, target_station_chainage=1000.0)
    assert profile.ma_end_chainage == 1000.0
    assert profile.safety_distance == 300.0


def test_ma_end_without_target_is_train_position():
    atp = ATPController(AtpConfig())
    profile = atp.build_ma_profile("T1", train_position=500.0, target_station_chainage=None)
    assert profile.ma_end_chainage == 500.0


def test_atp_speed_limit_applies_margin():
    atp = ATPController(AtpConfig(overspeed_margin=0.05))
    assert atp.atp_speed_limit(80.0) == 76.0
