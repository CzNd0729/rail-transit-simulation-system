"""终点站折返状态机（道岔联动 + 换向）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sim_engine.signaling.models import ServiceTimetable
from sim_engine.track.switch import SwitchManager

if TYPE_CHECKING:
    from sim_engine.orchestrator import TrainRun


@dataclass
class TurnbackController:
    service: ServiceTimetable

    def terminal_station(self, run: TrainRun) -> str | None:
        if not run.legs or run.leg_index >= len(run.legs):
            return None
        leg_name = self.service.trip_leg_names[run.leg_index]
        template = self.service.leg_templates.get(leg_name)
        return template.terminal_station if template else None

    def switch_for_leg(self, run: TrainRun) -> str:
        leg_name = self.service.trip_leg_names[run.leg_index]
        template = self.service.leg_templates[leg_name]
        if template.direction == "down":
            return self.service.turnback_switch_down
        return self.service.turnback_switch_up

    def at_terminal_dwell(self, run: TrainRun) -> bool:
        terminal = self.terminal_station(run)
        if terminal is None:
            return False
        sig = run.signaling.signal_state
        if run.state.speed >= 0.1:
            return False
        return sig._dwell_station_id == terminal

    def step(
        self,
        run: TrainRun,
        elapsed: float,
        switch_manager: SwitchManager,
        dt: float,
    ) -> bool:
        """推进折返；返回本步是否处于折返占用（不应步进动力学）。"""
        if run.leg_index + 1 >= len(run.legs):
            return run.turnback_state is not None

        if run.turnback_state is None:
            if not self.at_terminal_dwell(run):
                return False
            run.turnback_state = "switching"
            switch_id = self.switch_for_leg(run)
            switch_manager.set_state(switch_id, "reverse")
            run._turnback_elapsed = 0.0
            return True

        run._turnback_elapsed = getattr(run, "_turnback_elapsed", 0.0) + dt
        switch_id = self.switch_for_leg(run)
        sw = switch_manager.query(switch_id)
        turnback_time = self.service.turnback_time_s
        switch_ready = sw is not None and sw.state == "reverse"
        if run.turnback_state == "switching" and switch_ready:
            run.turnback_state = "dwelling"
        if run.turnback_state == "dwelling" and run._turnback_elapsed >= turnback_time:
            run.turnback_state = "reversing"
        if run.turnback_state == "reversing":
            self._complete_turnback(run, elapsed, switch_manager, switch_id)
            return False
        return True

    def _complete_turnback(
        self,
        run: TrainRun,
        elapsed: float,
        switch_manager: SwitchManager,
        switch_id: str,
    ) -> None:
        from sim_engine.signaling.ats import ATSController

        run.leg_index += 1
        new_dir = "up" if run.direction == "down" else "down"
        run.direction = new_dir
        run.state.direction = new_dir
        abs_tt = run.legs[run.leg_index].with_absolute_times(elapsed)
        run.ats = ATSController(run.signaling.sim_params.signal.ats, abs_tt)
        run.signaling.reset(direction=new_dir)
        run.turnback_state = None
        run._turnback_elapsed = 0.0
        switch_manager.set_state(switch_id, "normal")
