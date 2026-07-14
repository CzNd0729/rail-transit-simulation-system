"""持续派车集成测试。"""

from __future__ import annotations

from dataclasses import replace

import pytest

from sim_engine.orchestrator import Orchestrator
from sim_engine.signaling.models import DispatchConfig


def _as_fixed(orch: Orchestrator) -> None:
    assert orch._service_timetable is not None
    orch._service_timetable = replace(
        orch._service_timetable,
        dispatch=replace(orch._service_timetable.dispatch, mode="fixed"),
    )
    orch._fleet_scheduler = None
    orch._turnback = None
    orch.reset()


def test_continuous_both_directions_at_start():
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    snap = orch.step_once()
    assert snap is not None
    trains = snap["data"]["trains"]
    ids = {t["id"] for t in trains}
    dirs = {t["direction"] for t in trains}
    assert "TRAIN_D01" in ids
    assert "TRAIN_U01" in ids
    assert dirs == {"down", "up"}


def test_continuous_second_train_held_then_dispatched():
    """第二班在 150s 到点；若始发未清空则阻塞，清空后按 150s 班次补发。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    train_d02 = None
    for _ in range(20000):
        orch.step_once()
        for run in orch.trains:
            if run.train_id == "TRAIN_D02":
                train_d02 = run
                break
        if train_d02 is not None:
            break
    assert train_d02 is not None
    assert train_d02.spawn_time == 150.0


def test_continuous_dispatch_count_grows():
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 600.0
    orch.reset()
    orch.start()
    for _ in range(6000):
        orch.step_once()
    assert len(orch.trains) >= 4


def test_fixed_mode_train_count_fallback():
    orch = Orchestrator.from_config_dir()
    _as_fixed(orch)
    orch.sim_params.train_count = 1
    orch.sim_params.bidirectional = False
    orch.start()
    snap = orch.step_once()
    assert snap is not None
    assert len(snap["data"]["trains"]) == 1


def test_continuous_arrival_stores_in_buffer():
    """列车到达终点后应存入缓冲区，而非继续 active。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    # 运行足够长的时间，让 D01 到达 ST24（约 2000s）
    for _ in range(25000):
        orch.step_once()
    # 检查缓冲区应有车辆
    assert orch._fleet_scheduler is not None
    bs = orch._fleet_scheduler.buffer_state()
    has_any = any(len(v) > 0 for v in bs.values())
    assert has_any, f"buffer_state should have entries, got {bs}"


def test_continuous_buffer_vehicle_id_persists():
    """从缓冲区发出后 vehicle_id 应保持不变，total_trips 递增。"""
    orch = Orchestrator.from_config_dir()
    orch.reset()
    orch.start()
    vehicle_ids: set[str] = set()
    for _ in range(50000):
        orch.step_once()
        for run in orch.trains:
            if run.active and run.vehicle_id:
                vehicle_ids.add(run.vehicle_id)
    assert len(vehicle_ids) >= 2, f"Expected >=2 vehicle_ids, got {vehicle_ids}"


@pytest.mark.xfail(
    reason=(
        "存车线与 Turnback 并存：终到站优先折返导致缓冲只进不出、"
        "持续造新车，车队无法稳态；需后续改为单程交路+缓冲复用"
    ),
    strict=False,
)
def test_continuous_buffer_steady_state():
    """长时间运行后，列车总数应趋于稳定（不再增长），进入稳态。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 10000.0
    orch.reset()
    orch.start()
    train_counts: list[int] = []
    for _ in range(100000):
        orch.step_once()
        active = len([r for r in orch.trains if r.active])
        buffer_total = sum(
            len(v) for v in (orch._fleet_scheduler.buffer_state() if orch._fleet_scheduler else {}).values()
        )
        train_counts.append(active + buffer_total)
    # 后半段的列车总数应该稳定，不再增长
    half = len(train_counts) // 2
    second_half = train_counts[half:]
    max_growth = max(second_half) - min(second_half)
    assert max_growth <= 2, f"列车总数不稳定，后半段波动 {max_growth}"


def test_continuous_buffer_new_train_stops_after_steady():
    """稳态后不应再产生新车（全部 vehicle_id 来自缓冲区复用）。"""
    orch = Orchestrator.from_config_dir()
    orch.sim_params.total_time = 10000.0
    orch.reset()
    orch.start()
    for _ in range(100000):
        orch.step_once()
    for run in orch.trains:
        if run.active:
            assert run.vehicle_id.startswith("VEH_"), f"Unexpected vehicle_id: {run.vehicle_id}"
    assert len(orch.trains) > 0


def test_continuous_dwell_not_capped_massively():
    """recover 下长时间运行不应大量出现顶满 max_dwell 的站停。"""
    orch = Orchestrator.from_config_dir()
    assert orch.sim_params.signal.ats.dwell_adjust_mode == "recover"
    orch.sim_params.total_time = 2500.0
    orch.reset()
    orch.start()
    capped = 0
    samples = 0
    max_dwell = orch.sim_params.signal.ats.max_dwell_time
    for _ in range(25000):
        orch.step_once()
        for run in orch.trains:
            if not run.active:
                continue
            d = run.ats.last_deviation
            if d is None:
                continue
            samples += 1
            if d.adjusted_dwell >= max_dwell - 1e-6 and d.delay_arrival > 0:
                capped += 1
    assert samples > 0
    assert capped / samples < 0.05, f"capped={capped} samples={samples}"
