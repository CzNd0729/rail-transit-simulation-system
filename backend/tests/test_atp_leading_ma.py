"""ATP MA 前车约束测试。"""

from __future__ import annotations

from sim_engine.core.config import AtpConfig
from sim_engine.signaling.atp import ATPController


def test_ma_end_capped_by_leading_train():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    ma_end = atp.ma_end_chainage(
        train_position=1000.0,
        target_station_chainage=3000.0,
        leading_chainage=1500.0,
    )
    assert ma_end == 1200.0  # 1500 - 300


def test_ma_end_without_leading_uses_target():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    ma_end = atp.ma_end_chainage(1000.0, 3000.0, None)
    assert ma_end == 3000.0


def test_ma_end_not_below_train_position():
    atp = ATPController(AtpConfig(safety_distance=300.0))
    ma_end = atp.ma_end_chainage(
        train_position=1000.0,
        target_station_chainage=3000.0,
        leading_chainage=1100.0,
    )
    assert ma_end == 1000.0
