"""ATOController 单元测试。"""

from __future__ import annotations

from sim_engine.signaling.ato import ATOController


def test_target_speed_zero_at_station():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    assert ato.target_speed_on_curve(0.0) == 0.0


def test_target_speed_positive_before_station():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    v = ato.target_speed_on_curve(100.0)
    assert v > 0.0


def test_braking_trim_increases_when_overspeed():
    ato = ATOController(kp_brake=0.02, comfort_decel=0.8)
    remaining = 200.0
    target = ato.target_speed_on_curve(remaining)
    low = ato.compute_brake_level(speed_kmh=target * 0.5, remaining_m=remaining)
    high = ato.compute_brake_level(speed_kmh=target * 1.5, remaining_m=remaining)
    assert high >= low
    assert 0.0 <= high <= 1.0
