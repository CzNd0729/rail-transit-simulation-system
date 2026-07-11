"""train_following 占位模块测试。"""

from __future__ import annotations

from sim_engine.signaling.train_following import is_interval_safe


def test_interval_safe():
    assert is_interval_safe(1500, 1000, 500) is True
    assert is_interval_safe(1400, 1000, 500) is False


def test_interval_exactly_at_minimum():
    assert is_interval_safe(1000, 500, 500) is True
