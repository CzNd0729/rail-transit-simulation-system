"""仿真数据记录器（ENG-REC-01 ~ REC-03）。"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class StepRecord:
    time: float
    position: float
    speed: float
    acceleration: float
    mode: str
    traction_force: float
    brake_force: float
    total_resistance: float


@dataclass
class DataRecorder:
    """内存缓冲区 + CSV 导出。"""

    buffer: list[StepRecord] = field(default_factory=list)

    def record(self, row: StepRecord) -> None:
        self.buffer.append(row)

    def clear(self) -> None:
        self.buffer.clear()

    def export_csv(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    "time",
                    "position",
                    "speed",
                    "mode",
                    "acceleration",
                    "traction_force",
                    "brake_force",
                    "total_resistance",
                ]
            )
            for r in self.buffer:
                writer.writerow(
                    [
                        r.time,
                        r.position,
                        r.speed,
                        r.mode,
                        r.acceleration,
                        r.traction_force,
                        r.brake_force,
                        r.total_resistance,
                    ]
                )

    def summary(self) -> dict:
        if not self.buffer:
            return {"steps": 0, "total_time": 0.0, "avg_speed": 0.0, "max_speed": 0.0}
        speeds = [r.speed for r in self.buffer]
        return {
            "steps": len(self.buffer),
            "total_time": self.buffer[-1].time,
            "avg_speed": sum(speeds) / len(speeds),
            "max_speed": max(speeds),
        }
