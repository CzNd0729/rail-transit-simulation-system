"""ATS 运行图调度（SIG-06：recover 赶点 / extend 兼容）。"""

from __future__ import annotations

from sim_engine.core.config import AtsConfig
from sim_engine.signaling.models import Timetable, TimetableDeviation


class ATSController:
    def __init__(self, config: AtsConfig, timetable: Timetable):
        self._config = config
        self._timetable = timetable
        self.last_deviation: TimetableDeviation | None = None

    def adjust_dwell(
        self,
        station_id: str,
        nominal_dwell: float,
        actual_arrival: float,
    ) -> tuple[float, TimetableDeviation | None]:
        planned = self._timetable.planned_arrival(station_id)
        if planned is None:
            return nominal_dwell, None

        delay = actual_arrival - planned
        mode = self._config.dwell_adjust_mode
        if mode == "recover":
            if delay > 0:
                adjusted = nominal_dwell - delay
            else:
                planned_dep = self._timetable.planned_departure(station_id)
                if planned_dep is not None:
                    adjusted = max(nominal_dwell, planned_dep - actual_arrival)
                else:
                    adjusted = nominal_dwell - delay
        elif mode == "extend":
            adjusted = nominal_dwell + max(0.0, delay)
        else:
            adjusted = nominal_dwell

        adjusted = max(self._config.min_dwell_time, min(self._config.max_dwell_time, adjusted))
        dev = TimetableDeviation(
            train_id=self._timetable.train_id,
            station_id=station_id,
            delay_arrival=delay,
            nominal_dwell=nominal_dwell,
            adjusted_dwell=adjusted,
        )
        self.last_deviation = dev
        return adjusted, dev
