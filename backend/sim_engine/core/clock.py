"""仿真时钟与运行状态（ENG-01 / ENG-03 / ENG-04）。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RunState(str, Enum):
    """仿真运行状态。"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class SimulationClock:
    """固定步长仿真时钟。"""

    time_step: float = 0.1
    """步长 (s)。"""

    elapsed: float = 0.0
    """已仿真时间 (s)。"""

    speed_multiplier: float = 1.0
    """仿真速度倍率（仅影响实时等待，不影响物理步进）。"""

    def tick(self) -> float:
        """推进一个步长，返回新的 elapsed。"""
        self.elapsed += self.time_step
        return self.elapsed

    def reset(self) -> None:
        self.elapsed = 0.0
