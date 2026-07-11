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
from sim_engine.power.load_flow import PowerFlowResult, PowerNetwork, calculate
from sim_engine.power.regeneration import calculate_regen_power, calculate_traction_power
from sim_engine.power.substation import Substation
from sim_engine.signaling.atp import ATPController
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.manual_drive import ManualDriveController
from sim_engine.signaling.models import SafetyStatus
from sim_engine.signaling.three_stage import ThreeStageController
from sim_engine.signaling.timetable_loader import load_timetable
from sim_engine.track.config import load_track
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.dynamics import VehicleSystem, effective_speed_limit_kmh
from sim_engine.vehicle.models import ControlCommands, StepResult, TrainState

CONFIG_DIR = Path(__file__).resolve().parent / "config"


@dataclass
class Orchestrator:
    """单列车 MVP 仿真编排器。"""

    vehicle: VehicleSystem
    track: TrackPathService
    signaling: ThreeStageController
    atp: ATPController
    ats: ATSController
    clock: SimulationClock
    sim_params: SimulationParams
    power_network: PowerNetwork = field(default_factory=PowerNetwork)
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
        timetable = load_timetable(config_dir / "timetable.yaml")
        ats = ATSController(sim_params.signal.ats, timetable)
        atp = ATPController(sim_params.signal.atp)
        signaling = ThreeStageController(track, vehicle.params, sim_params, ats=ats)
        clock = SimulationClock(
            time_step=sim_params.time_step,
            speed_multiplier=sim_params.speed_multiplier,
        )

        # 构建供电网络
        power_network = PowerNetwork(
            substations=[
                Substation(
                    id=s.id,
                    name=s.name,
                    chainage=s.chainage,
                    rated_voltage=s.rated_voltage,
                    rated_power=s.rated_power,
                )
                for s in sim_params.power.substations
            ],
            contact_line_resistance=sim_params.power.contact_line_resistance,
            rail_resistance=sim_params.power.rail_resistance,
        )

        return cls(
            vehicle=vehicle,
            track=track,
            signaling=signaling,
            atp=atp,
            ats=ats,
            clock=clock,
            sim_params=sim_params,
            power_network=power_network,
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
        elapsed = self.clock.elapsed
        track_params = self.track.query_at(self.train_state.position)
        speed_limit = effective_speed_limit_kmh(track_params, self.vehicle.params)
        cmd = self.signaling.compute_commands(self.train_state, dt, elapsed=elapsed)
        if self.atp.check_overspeed(self.train_state.speed, speed_limit) == SafetyStatus.EMERGENCY_BRAKE:
            cmd = ControlCommands(
                traction_level=0.0,
                brake_level=0.0,
                emergency_brake=True,
                phase=cmd.phase or self.signaling.signal_state.phase.value,
            )
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

        # ── 供电计算 ──
        v_ms = result.state.speed / 3.6 if result.state.speed > 0 else 0.0
        power_mode = self.sim_params.power.mode

        # 计算列车功率需求
        if result.forces.traction > 0:
            power_demand = calculate_traction_power(result.forces.traction, v_ms)
        elif result.forces.brake > 0:
            # 再生制动功率（负值表示回馈，不模拟吸收）
            power_demand = -calculate_regen_power(
                result.forces.brake, v_ms,
                self.vehicle.params.regeneration_efficiency,
            )
        else:
            power_demand = 0.0

        if power_mode == "simple_ohm":
            power_flow: PowerFlowResult = calculate(
                self.power_network,
                result.state.position,
                power_demand,
            )
            pantograph_voltage = power_flow.pantograph_voltage
            substation_states = power_flow.substation_states
        else:
            # "fixed" 模式：固定网压
            from sim_engine.power.static_power import get_pantograph_voltage

            pantograph_voltage = get_pantograph_voltage()
            substation_states = []

        # 电压曲线采样点（当前时刻列车位置与网压）
        voltage_profile = [
            {
                "chainage": result.state.position,
                "voltage": pantograph_voltage,
            }
        ]

        running_phase = cmd.phase or sig_st.phase.value
        target_chainage = (
            self.track.get_station_chainage(sig_st.target_station_id)
            if sig_st.target_station_id
            else None
        )
        ma = self.atp.build_ma_profile(self.train_id, self.train_state.position, target_chainage)
        timetable_dev: list[dict] = []
        if self.ats.last_deviation is not None:
            d = self.ats.last_deviation
            timetable_dev = [{
                "trainId": d.train_id,
                "stationId": d.station_id,
                "delayArrival": d.delay_arrival,
                "nominalDwell": d.nominal_dwell,
                "adjustedDwell": d.adjusted_dwell,
            }]

        snapshot = build_simulation_snapshot(
            self.clock,
            self.sim_params,
            self.train_id,
            result.state,
            result.forces,
            pantograph_voltage=pantograph_voltage,
            power_demand=power_demand,
            voltage_profile=voltage_profile,
            substation_states=substation_states,
            signaling_extra={
                "runningPhase": running_phase,
                "speedLimits": [{
                    "trainId": self.train_id,
                    "permanentLimit": speed_limit,
                    "atpLimit": self.atp.atp_speed_limit(speed_limit),
                }],
                "maProfile": [{
                    "trainId": ma.train_id,
                    "maEndChainage": ma.ma_end_chainage,
                    "safetyDistance": ma.safety_distance,
                }],
                "timetableDeviation": timetable_dev,
            },
        )
        # 写入本步实际控车指令
        snapshot["data"]["signaling"]["controlCommands"][0].update({
            "trainId": self.train_id,
            "tractionLevel": cmd.traction_level,
            "brakeLevel": cmd.brake_level,
            "emergencyBrake": cmd.emergency_brake,
            "runningPhase": running_phase,
        })
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
