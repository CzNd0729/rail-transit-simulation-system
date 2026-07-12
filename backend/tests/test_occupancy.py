"""轨道区段占用检测器单元测试（覆盖 TRK-07 / TRK-10 / TRK-11）。"""

from __future__ import annotations

import pytest

from sim_engine.track import OccupancyDetector, TrackCircuit


def make_circuits() -> list[TrackCircuit]:
    """3站2区段预置轨道电路。"""
    return [
        TrackCircuit("TC01", 0.0, 1500.0, "down"),
        TrackCircuit("TC02", 1500.0, 3200.0, "down"),
    ]


def make_detector() -> OccupancyDetector:
    return OccupancyDetector(make_circuits())


# ══════════════════════════════════════════════════════════════════════
# TRK-11: 区段占用更新
# ══════════════════════════════════════════════════════════════════════


class TestOccupancyUpdate:
    def test_initial_all_free(self):
        det = make_detector()
        s = det.state()
        assert all(not c.occupied for c in s)
        assert len(s) == 2

    def test_single_train_occupancy(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        s = det.state()
        assert s[0].occupied  # TC01
        assert not s[1].occupied  # TC02

    def test_train_in_second_circuit(self):
        det = make_detector()
        det.update({"TRAIN_01": (2000.0, "down")})
        s = det.state()
        assert not s[0].occupied  # TC01
        assert s[1].occupied  # TC02

    def test_cleared_between_updates(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        assert det.state()[0].occupied

        det.update({"TRAIN_01": (2000.0, "down")})
        assert not det.state()[0].occupied  # TC01 已出清
        assert det.state()[1].occupied  # TC02 已占用

    def test_clear_all_when_no_trains(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        det.update({})
        assert all(not c.occupied for c in det.state())

    def test_boundary_start_chainage(self):
        det = make_detector()
        det.update({"TRAIN_01": (0.0, "down")})
        assert det.state()[0].occupied

    def test_boundary_end_chainage(self):
        det = make_detector()
        det.update({"TRAIN_01": (3200.0, "down")})
        assert det.state()[1].occupied

    def test_before_first_circuit_clamps(self):
        det = make_detector()
        det.update({"TRAIN_01": (-100.0, "down")})
        assert det.state()[0].occupied  # 截断到第一个区段

    def test_after_last_circuit_clamps(self):
        det = make_detector()
        det.update({"TRAIN_01": (5000.0, "down")})
        assert det.state()[1].occupied  # 截断到最后一个区段

    def test_multi_train(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down"), "TRAIN_02": (2000.0, "down")})
        s = det.state()
        assert s[0].occupied  # TC01 被 TRAIN_01 占用
        assert s[1].occupied  # TC02 被 TRAIN_02 占用

    def test_state_is_copy(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        s1 = det.state()
        s2 = det.state()
        assert s1 is not s2  # 每次返回新副本
        assert s1[0] is not s2[0]


# ══════════════════════════════════════════════════════════════════════
# TRK-10: 单区段占用查询
# ══════════════════════════════════════════════════════════════════════


class TestOccupancyQuery:
    def test_query_circuit_found(self):
        det = make_detector()
        tc = det.query_circuit(500.0)
        assert tc is not None
        assert tc.id == "TC01"

    def test_query_circuit_second(self):
        det = make_detector()
        tc = det.query_circuit(2000.0)
        assert tc is not None
        assert tc.id == "TC02"

    def test_is_occupied(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        assert det.is_occupied(500.0)
        assert not det.is_occupied(2000.0)

    def test_query_beyond_range(self):
        det = make_detector()
        tc = det.query_circuit(999999.0)
        assert tc is not None  # 截断到最后一个区段
        assert tc.id == "TC02"


# ══════════════════════════════════════════════════════════════════════
# occupancy_list() 格式测试
# ══════════════════════════════════════════════════════════════════════


class TestOccupancyList:
    def test_format(self):
        det = make_detector()
        det.update({"TRAIN_01": (500.0, "down")})
        lst = det.occupancy_list()
        assert len(lst) == 2
        assert lst[0]["circuitId"] == "TC01"
        assert lst[0]["occupied"] is True
        assert lst[0]["startChainage"] == 0.0
        assert lst[0]["endChainage"] == 1500.0
        assert lst[0]["direction"] == "down"
        assert lst[1]["occupied"] is False

    def test_empty_circuits(self):
        det = OccupancyDetector([])
        assert det.occupancy_list() == []
        assert det.state() == []
        # update should not crash
        det.update({"TRAIN_01": (100.0, "down")})
