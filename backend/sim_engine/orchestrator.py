"""仿真编排器（ENG-01 ~ ENG-06，车辆系统集成）。

协调轨道查询 → 信号控车 → 车辆动力学 → 数据记录 → 快照输出。
WebSocket 推送由上层 app 订阅 ``last_snapshot`` 或注册回调实现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from sim_engine.core.clock import RunState, SimulationClock
from sim_engine.core.config import SimulationParams, load_simulation_params
from sim_engine.data.recorder import DataRecorder, StepRecord
from sim_engine.data.snapshot import build_simulation_snapshot
from sim_engine.power.static_power import get_pantograph_voltage
from sim_engine.signaling.manual_drive import ManualDriveController
from sim_engine.signaling.three_stage import ThreeStageController
from sim_engine.track.config import load_track
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.dynamics import VehicleSystem
from sim_engine.vehicle.models import StepResult, TrainState

CONFIG_DIR = Path(__file__).resolve().parent / "config"


@dataclass
class Orchestrator:
    """单列车 MVP 仿真编排器。"""

    vehicle: VehicleSystem
    track: TrackPathService
    signaling: ThreeStageController
    clock: SimulationClock
    sim_params: SimulationParams
    recorder: DataRecorder = field(default_factory=DataRecorder)
    train_id: str = "TRAIN_01"
    train_state: TrainState | None = None
    run_state: RunState = RunState.IDLE
    manual_driver: ManualDriveController = field(default_factory=ManualDriveController)
    last_snapshot: dict | None = None
    last_step: StepResult | None = None
    _on_snapshot: Callable[[dict], None] | None = None

    @classmethod
    def from_config_dir(cls, config_dir: str | Path | None = None) -> "Orchestrator":
        config_dir = Path(config_dir or CONFIG_DIR)
        sim_params = load_simulation_params(config_dir / "simulation.yaml")
        vehicle = VehicleSystem(load_vehicle_params(config_dir / "vehicle.yaml"))
        track = TrackPathService(load_track(config_dir / "track.yaml"))
        signaling = ThreeStageController(track, vehicle.params, sim_params)
        clock = SimulationClock(
            time_step=sim_params.time_step,
            speed_multiplier=sim_params.speed_multiplier,
        )
        return cls(
            vehicle=vehicle,
            track=track,
            signaling=signaling,
            clock=clock,
            sim_params=sim_params,
        )

    def set_snapshot_callback(self, callback: Callable[[dict], None]) -> None:
        """注册每步快照回调（供 WebSocket 推送层使用）。"""
        self._on_snapshot = callback

    def set_emergency_brake(self, active: bool) -> None:
        """设置/解除手动紧急制动。"""
        self.manual_driver.set_emergency_brake(active)

    def reset(self, passenger_load: float = 0.6) -> None:
        self.clock.reset()
        self.recorder.clear()
        self.signaling.reset()
        self.train_state = self.vehicle.create_initial_state(
            position=0.0, passenger_load=passenger_load
        )
        self.run_state = RunState.IDLE
        self.last_snapshot = None
        self.last_step = None
        self.manual_driver = ManualDriveController()

    def start(self, passenger_load: float = 0.6) -> None:
        if self.train_state is None:
            self.reset(passenger_load)
        self.run_state = RunState.RUNNING

    def pause(self) -> None:
        if self.run_state == RunState.RUNNING:
            self.run_state = RunState.PAUSED

    def resume(self) -> None:
        if self.run_state == RunState.PAUSED:
            self.run_state = RunState.RUNNING

    def stop(self) -> None:
        self.run_state = RunState.STOPPED

    def step_once(self) -> dict | None:
        """推进一个仿真步（ENG-06 单步调试）。暂停/空闲时也可强制调用。"""
        if self.train_state is None:
            self.reset()
        assert self.train_state is not None

        dt = self.clock.time_step
        track_params = self.track.query_at(self.train_state.position)
        cmd = self.signaling.compute_commands(self.train_state, dt)
        cmd = self.manual_driver.get_commands(cmd)  # 手动指令叠加（紧急制动覆盖）
        result = self.vehicle.step(
            self.train_state, cmd, track_params, dt, self.sim_params.pid.max_jerk
        )
        self.train_state = result.state
        self.last_step = result

        # 复制信号系统的距站距离到 TrainState（供 snapshot 输出）
        sig_st = self.signaling.signal_state
        self.train_state.distance_to_station = sig_st.distance_to_station
        self.train_state.target_station_id = sig_st.target_station_id

        self.clock.tick()

        self.recorder.record(
            StepRecord(
                time=self.clock.elapsed,
                position=result.state.position,
                speed=result.state.speed,
                acceleration=result.state.acceleration,
                jerk=result.state.jerk,
                mode=result.state.mode,
                traction_force=result.forces.traction,
                brake_force=result.forces.brake,
                total_resistance=result.forces.resistance_total,
            )
        )

        snapshot = build_simulation_snapshot(
            self.clock,
            self.sim_params,
            self.train_id,
            result.state,
            result.forces,
            pantograph_voltage=get_pantograph_voltage(),
        )
        # 写入本步实际控车指令
        snapshot["data"]["signaling"]["controlCommands"][0] = {
            "trainId": self.train_id,
            "tractionLevel": cmd.traction_level,
            "brakeLevel": cmd.brake_level,
            "emergencyBrake": cmd.emergency_brake,
        }
        self.last_snapshot = snapshot
        if self._on_snapshot:
            self._on_snapshot(snapshot)
        return snapshot

    def run_until(self, max_steps: int | None = None) -> dict:
        """运行仿真直到结束、停止或达到步数上限。"""
        if self.run_state == RunState.IDLE:
            self.start()
        steps = 0
        while self.run_state == RunState.RUNNING:
            if self.clock.elapsed >= self.sim_params.total_time:
                break
            # 到达终点且停稳
            if (
                self.train_state
                and self.train_state.position
                >= self.track.track.total_length - 1.0
                and self.train_state.speed < 0.1
            ):
                break
            self.step_once()
            steps += 1
            if max_steps is not None and steps >= max_steps:
                break
        summary = self.recorder.summary()
        # 自动复位到初始状态（与 SimulationManager._run_loop 行为一致）
        self.reset()
        self.run_state = RunState.STOPPED
        return summary
