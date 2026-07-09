"""轨道系统单元测试（覆盖 TRK-01 ~ TRK-04、配置加载）。"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sim_engine.track import Segment, Station, Track, TrackPathService, load_track

CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "sim_engine" / "config" / "track.yaml"
)


def make_track(
    name: str = "测试线",
    stations: list[Station] | None = None,
    segments: list[Segment] | None = None,
) -> Track:
    return Track(name=name, stations=stations or [], segments=segments or [])


def default_track() -> Track:
    """3站2区间预置线路。"""
    return make_track(
        stations=[
            Station("ST01", "A站", 0.0, 30.0),
            Station("ST02", "B站", 1500.0, 30.0),
            Station("ST03", "C站", 3200.0, 30.0),
        ],
        segments=[
            Segment("SEC01", 0.0, 1500.0, gradient=5.0, curvature=800.0, speed_limit=80.0, is_tunnel=False),
            Segment("SEC02", 1500.0, 3200.0, gradient=0.0, curvature=1200.0, speed_limit=80.0, is_tunnel=False),
        ],
    )


# ══════════════════════════════════════════════════════════════════════
# TRK-01: 一维线性路径建模
# ══════════════════════════════════════════════════════════════════════


class TestStationModel:
    def test_defaults(self):
        st = Station("S1", "测试站", 1000.0)
        assert st.dwell_time == 30.0
        assert st.platform_half_length == 15.0

    def test_custom_values(self):
        st = Station("S1", "X", 500.0, dwell_time=45.0, platform_half_length=20.0)
        assert st.id == "S1"
        assert st.name == "X"
        assert st.chainage == 500.0
        assert st.dwell_time == 45.0
        assert st.platform_half_length == 20.0


class TestSegmentModel:
    def test_defaults(self):
        seg = Segment("SG1", 0.0, 1000.0)
        assert seg.gradient == 0.0
        assert seg.curvature == 0.0
        assert seg.speed_limit == 80.0
        assert seg.is_tunnel is False

    def test_length_property(self):
        seg = Segment("SG1", 200.0, 1200.0)
        assert seg.length == 1000.0

    def test_tunnel_flag(self):
        seg = Segment("SG1", 0.0, 500.0, is_tunnel=True)
        assert seg.is_tunnel is True


class TestTrackModel:
    def test_empty_track_has_zero_length(self):
        track = make_track()
        assert track.total_length == 0.0

    def test_total_length_from_segments(self):
        track = make_track(segments=[
            Segment("S1", 0.0, 1000.0),
            Segment("S2", 1000.0, 2500.0),
        ])
        assert track.total_length == 2500.0

    def test_stations_and_segments(self):
        track = default_track()
        assert len(track.stations) == 3
        assert len(track.segments) == 2
        assert track.name == "测试线"


# ══════════════════════════════════════════════════════════════════════
# TRK-02: 位置查询（公里标 → 坡度/曲率/限速/隧道）
# ══════════════════════════════════════════════════════════════════════


class TestQueryAt:
    def test_query_first_segment(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(500.0)
        assert r.gradient == 5.0
        assert r.curvature == 800.0
        assert r.speed_limit == 80.0
        assert r.is_tunnel is False

    def test_query_second_segment(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(2500.0)
        assert r.gradient == 0.0
        assert r.curvature == 1200.0

    def test_query_exact_boundary(self):
        svc = TrackPathService(default_track())
        # 在 1500.0 边界上，两个区段都能匹配；线性扫描先命中 SEC01
        r_exact = svc.query_at(1500.0)
        assert r_exact.curvature == 800.0  # SEC01
        # 略微超过边界即进入 SEC02
        r_across = svc.query_at(1500.01)
        assert r_across.curvature == 1200.0  # SEC02

    def test_query_start_chainage(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(0.0)
        assert r.gradient == 5.0

    def test_query_end_chainage(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(3200.0)
        assert r.curvature == 1200.0

    def test_query_before_start_returns_first_segment(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(-100.0)
        assert r.gradient == 5.0  # clamps to first segment

    def test_query_beyond_end_returns_last_segment(self):
        svc = TrackPathService(default_track())
        r = svc.query_at(9999.0)
        assert r.curvature == 1200.0  # clamps to last segment

    def test_query_empty_track_returns_defaults(self):
        svc = TrackPathService(make_track())
        r = svc.query_at(100.0)
        assert r.gradient == 0.0
        assert r.curvature == 0.0
        assert r.speed_limit == 80.0  # TrackPointParams 默认值
        assert r.is_tunnel is False

    def test_tunnel_flag_returns_true(self):
        track = make_track(segments=[Segment("T1", 0.0, 500.0, is_tunnel=True)])
        svc = TrackPathService(track)
        r = svc.query_at(250.0)
        assert r.is_tunnel is True


# ══════════════════════════════════════════════════════════════════════
# TRK-03: 车站位置查询（车站 ID → 站台中心公里标）
# ══════════════════════════════════════════════════════════════════════


class TestGetStationById:
    def test_existing_id(self):
        svc = TrackPathService(default_track())
        st = svc.get_station_by_id("ST02")
        assert st is not None
        assert st.name == "B站"
        assert st.chainage == 1500.0

    def test_missing_id_returns_none(self):
        svc = TrackPathService(default_track())
        assert svc.get_station_by_id("ST99") is None

    def test_all_stations_accessible_by_id(self):
        svc = TrackPathService(default_track())
        for expected_id in ("ST01", "ST02", "ST03"):
            assert svc.get_station_by_id(expected_id) is not None


class TestGetStationChainage:
    def test_returns_correct_chainage(self):
        svc = TrackPathService(default_track())
        assert svc.get_station_chainage("ST01") == 0.0
        assert svc.get_station_chainage("ST02") == 1500.0
        assert svc.get_station_chainage("ST03") == 3200.0

    def test_missing_returns_none(self):
        svc = TrackPathService(default_track())
        assert svc.get_station_chainage("NONEXISTENT") is None


class TestFindStation:
    def test_find_by_name(self):
        svc = TrackPathService(default_track())
        st = svc.find_station("B站")
        assert st is not None
        assert st.id == "ST02"

    def test_find_missing_name_returns_none(self):
        svc = TrackPathService(default_track())
        assert svc.find_station("不存在的站") is None


# ══════════════════════════════════════════════════════════════════════
# TRK-04: 站台范围判断（±15m）
# ══════════════════════════════════════════════════════════════════════


class TestStationAt:
    def test_exact_center(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1500.0).id == "ST02"

    def test_inside_platform_plus_10m(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1510.0).id == "ST02"

    def test_inside_platform_minus_10m(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1490.0).id == "ST02"

    def test_exact_boundary_plus_15m(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1515.0).id == "ST02"

    def test_exact_boundary_minus_15m(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1485.0).id == "ST02"

    def test_outside_platform(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1520.0) is None

    def test_outside_platform_negative(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1480.0) is None

    def test_custom_half_length(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(1530.0, half_length=35.0).id == "ST02"
        assert svc.station_at(1530.0, half_length=15.0) is None

    def test_between_stations(self):
        svc = TrackPathService(default_track())
        assert svc.station_at(700.0) is None


# ══════════════════════════════════════════════════════════════════════
# 辅助查询
# ══════════════════════════════════════════════════════════════════════


class TestNextStationAhead:
    def test_at_start(self):
        svc = TrackPathService(default_track())
        st = svc.next_station_ahead(0.0)
        assert st.id == "ST02"

    def test_just_after_first_station(self):
        svc = TrackPathService(default_track())
        st = svc.next_station_ahead(16.0)
        assert st.id == "ST02"

    def test_approaching_middle_station(self):
        svc = TrackPathService(default_track())
        st = svc.next_station_ahead(1200.0)
        assert st.id == "ST02"

    def test_after_middle_station(self):
        svc = TrackPathService(default_track())
        st = svc.next_station_ahead(1516.0)
        assert st.id == "ST03"

    def test_at_last_station(self):
        svc = TrackPathService(default_track())
        assert svc.next_station_ahead(3200.0) is None

    def test_beyond_last_station(self):
        svc = TrackPathService(default_track())
        assert svc.next_station_ahead(5000.0) is None

    def test_empty_track(self):
        svc = TrackPathService(make_track())
        assert svc.next_station_ahead(0.0) is None


# ══════════════════════════════════════════════════════════════════════
# 配置加载
# ══════════════════════════════════════════════════════════════════════


class TestLoadTrack:
    def test_load_from_yaml(self):
        track = load_track(CONFIG_PATH)
        assert track.name in ("1号线", "Line 1", "")
        assert len(track.stations) == 3
        assert len(track.segments) == 2
        assert track.total_length > 0

    def test_load_then_query(self):
        track = load_track(CONFIG_PATH)
        svc = TrackPathService(track)
        assert svc.get_station_by_id("ST01") is not None
        assert svc.get_station_by_id("ST03") is not None

    def test_tmp_yaml_roundtrip(self, tmp_path):
        """通过临时 YAML 验证完整读写流程。"""
        d = tmp_path / "track.yaml"
        data = {
            "line": {
                "name": "2号线",
                "stations": [
                    {"id": "A1", "name": "东站", "chainage": 0},
                    {"id": "A2", "name": "西站", "chainage": 2000},
                ],
                "segments": [
                    {
                        "id": "K1",
                        "start_chainage": 0,
                        "end_chainage": 2000,
                        "gradient": 10,
                        "curvature": 600,
                        "speed_limit": 100,
                        "is_tunnel": True,
                    },
                ],
            }
        }
        d.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        track = load_track(d)
        assert track.name == "2号线"
        assert len(track.stations) == 2
        assert track.segments[0].is_tunnel is True
        assert track.segments[0].speed_limit == 100.0

    def test_load_flat_yaml(self, tmp_path):
        """无 line 顶层 key 的 YAML。"""
        d = tmp_path / "track.yaml"
        data = {
            "name": "3号线",
            "stations": [{"id": "X1", "name": "南站", "chainage": 0}],
            "segments": [{"id": "K1", "start_chainage": 0, "end_chainage": 500}],
        }
        d.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        track = load_track(d)
        assert track.name == "3号线"
        assert len(track.stations) == 1

    def test_load_empty_yaml(self, tmp_path):
        d = tmp_path / "empty.yaml"
        d.write_text("", encoding="utf-8")
        track = load_track(d)
        assert track.stations == []
        assert track.segments == []

    def test_stations_sorted_by_service(self):
        """服务内部按公里标排序。"""
        track = make_track(stations=[
            Station("S3", "C", 3200.0),
            Station("S1", "A", 0.0),
            Station("S2", "B", 1500.0),
        ])
        svc = TrackPathService(track)
        assert svc.next_station_ahead(-1.0).id == "S1"  # 最前
        assert svc.next_station_ahead(3200.0) is None   # 最后之后无站


class TestSegmentMutation:
    def test_segment_at_and_update(self):
        track = default_track()
        svc = TrackPathService(track)
        seg = svc.segment_at(2000.0)
        assert seg is not None
        assert seg.id == "SEC02"

        updated = svc.update_segment("SEC02", gradient=30.0)
        assert updated is not None
        assert updated.gradient == 30.0
        assert svc.query_at(2000.0).gradient == 30.0

    def test_update_unknown_segment_returns_none(self):
        svc = TrackPathService(default_track())
        assert svc.update_segment("NOPE", gradient=1.0) is None
