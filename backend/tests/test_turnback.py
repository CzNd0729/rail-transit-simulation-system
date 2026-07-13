"""折返状态机测试。"""

from __future__ import annotations

from sim_engine.signaling.turnback import TurnbackController
from sim_engine.track.models import Switch
from sim_engine.track.switch import SwitchManager


def test_turnback_triggers_switch_at_terminal():
    switches = [
        Switch(
            id="SW04",
            chainage=18550,
            switch_type="crossover",
            normal_direction="main",
            reverse_direction="siding",
            lateral_speed_limit=30,
        )
    ]
    mgr = SwitchManager(switches)
    from pathlib import Path
    from sim_engine.signaling.timetable_loader import load_service_timetable

    svc = load_service_timetable(
        Path(__file__).resolve().parents[1] / "sim_engine" / "config" / "timetable.yaml"
    )
    ctrl = TurnbackController(svc)

    class _Run:
        leg_index = 0
        legs = [object(), object()]
        direction = "down"
        turnback_state = None
        state = type("S", (), {"speed": 0.0})()
        signaling = type(
            "Sig",
            (),
            {"signal_state": type("SS", (), {"_dwell_station_id": "ST24"})()},
        )()

    run = _Run()
    assert ctrl.at_terminal_dwell(run)
    busy = ctrl.step(run, 100.0, mgr, 0.1)
    assert busy is True
    assert mgr.query("SW04").state in ("transitioning", "reverse")
