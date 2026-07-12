"""SwitchManager 单元测试（TRK-06/TRK-08/TRK-09）。"""

from sim_engine.track.models import Switch
from sim_engine.track.switch import SwitchManager


def make_switches():
    return [
        Switch(id="SW01", chainage=50, switch_type="crossover",
               normal_direction="main", reverse_direction="siding",
               lateral_speed_limit=30, state="normal", transition_time=3.0),
        Switch(id="SW02", chainage=7300, switch_type="single",
               normal_direction="main", reverse_direction="siding",
               lateral_speed_limit=30, state="normal", transition_time=3.0),
    ]


class TestSwitchManagerQuery:
    def test_query_existing_switch(self):
        mgr = SwitchManager(make_switches())
        sw = mgr.query("SW01")
        assert sw is not None
        assert sw.id == "SW01"
        assert sw.state == "normal"

    def test_query_nonexistent_returns_none(self):
        mgr = SwitchManager(make_switches())
        assert mgr.query("SW99") is None

    def test_query_empty_manager(self):
        mgr = SwitchManager([])
        assert mgr.query("SW01") is None


class TestSwitchManagerSetState:
    def test_set_state_normal_to_reverse(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "reverse")
        assert ok is True
        sw = mgr.query("SW01")
        assert sw is not None
        assert sw.state == "transitioning"
        assert sw._target_state == "reverse"
        assert sw.transition_elapsed == 0.0

    def test_set_state_invalid_target(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "invalid")
        assert ok is False
        sw = mgr.query("SW01")
        assert sw.state == "normal"

    def test_set_state_already_transitioning(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        ok = mgr.set_state("SW01", "normal")  # Should reject
        assert ok is False
        sw = mgr.query("SW01")
        assert sw._target_state == "reverse"  # Target unchanged

    def test_set_state_same_as_current(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW01", "normal")
        assert ok is False  # Already in normal, no-op

    def test_set_state_nonexistent_switch(self):
        mgr = SwitchManager(make_switches())
        ok = mgr.set_state("SW99", "reverse")
        assert ok is False


class TestSwitchManagerUpdate:
    def test_update_transitions_after_full_time(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(3.0)
        sw = mgr.query("SW01")
        assert sw.state == "reverse"
        assert sw.transition_elapsed == 3.0
        assert sw._target_state == "reverse"

    def test_update_partial_transition(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(1.5)
        sw = mgr.query("SW01")
        assert sw.state == "transitioning"
        assert sw.transition_elapsed == 1.5

    def test_update_multiple_switches(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.set_state("SW02", "reverse")
        mgr.update(3.0)
        assert mgr.query("SW01").state == "reverse"
        assert mgr.query("SW02").state == "reverse"

    def test_update_no_transitioning_does_nothing(self):
        mgr = SwitchManager(make_switches())
        mgr.update(1.0)
        assert mgr.query("SW01").state == "normal"


class TestSwitchManagerSwitchList:
    def test_switch_list_default_states(self):
        mgr = SwitchManager(make_switches())
        lst = mgr.switch_list()
        assert len(lst) == 2
        assert lst[0]["switchId"] == "SW01"
        assert lst[0]["state"] == "normal"
        assert lst[0]["chainage"] == 50
        assert lst[0]["type"] == "crossover"
        assert lst[0]["normalDirection"] == "main"
        assert lst[0]["reverseDirection"] == "siding"
        assert lst[0]["lateralSpeedLimit"] == 30

    def test_switch_list_reflects_transition(self):
        mgr = SwitchManager(make_switches())
        mgr.set_state("SW01", "reverse")
        mgr.update(1.0)
        lst = mgr.switch_list()
        sw = next(s for s in lst if s["switchId"] == "SW01")
        assert sw["state"] == "transitioning"
        assert sw["transitionElapsed"] == 1.0

    def test_switch_list_empty(self):
        mgr = SwitchManager([])
        assert mgr.switch_list() == []
