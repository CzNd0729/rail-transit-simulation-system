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
from sim_engine.data.snapshot import TrainSnapshotEntry, build_simulation_snapshot
from sim_engine.power.load_flow import PowerFlowResult, PowerNetwork, calculate
from sim_engine.power.regeneration import calculate_regen_power, calculate_traction_power
from sim_engine.power.substation import Substation
from sim_engine.signaling.atp import ATPController
from sim_engine.signaling.ats import ATSController
from sim_engine.signaling.manual_drive import ManualDriveController
from sim_engine.signaling.models import MaProfile, SafetyStatus, Timetable
from sim_engine.signaling.three_stage import ThreeStageController
from sim_engine.signaling.timetable_loader import load_timetable
from sim_engine.signaling.train_following import is_interval_safe
from sim_engine.track.config import load_track
from sim_engine.track.occupancy import OccupancyDetector
from sim_engine.track.switch import SwitchManager
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.dynamics import VehicleSystem, effective_speed_limit_kmh
from sim_engine.vehicle.models import ControlCommands, StepResult, TrainState

CONFIG_DIR = Path(__file__).resolve().parent / "config"


@dataclass
class TrainRun:
    """单列车运行单元（独立信号链与状态）。"""

    train_id: str
    state: TrainState
    signaling: ThreeStageController
    ats: ATSController
    manual_driver: ManualDriveController
    spawn_time: float = 0.0
    active: bool = False
    last_step: StepResult | None = None


@dataclass
class Orchestrator:
    """仿真编排器（同向多列车步进与 snapshot）。"""

    vehicle: VehicleSystem
    track: TrackPathService
    atp: ATPController
    clock: SimulationClock
    sim_params: SimulationParams
    power_network: PowerNetwork = field(default_factory=PowerNetwork)
    occupancy: OccupancyDetector = field(default_factory=lambda: OccupancyDetector([]))
    switch_manager: SwitchManager = field(default_factory=lambda: SwitchManager([]))
    recorder: DataRecorder = field(default_factory=DataRecorder)
    trains: list[TrainRun] = field(default_factory=list)
    _timetable_path: Path = field(default_factory=lambda: CONFIG_DIR / "timetable.yaml")
    run_state: RunState = RunState.IDLE
    last_snapshot: dict | None = None
    _on_snapshot: Callable[[dict], None] | None = None

    @property
    def train_state(self) -> TrainState | None:
        return self.trains[0].state if self.trains else None

    @train_state.setter
    def train_state(self, value: TrainState | None) -> None:
        if self.trains and value is not None:
            self.trains[0].state = value

    @property
    def train_id(self) -> str:
        return self.trains[0].train_id if self.trains else "TRAIN_01"

    @property
    def signaling(self) -> ThreeStageController:
        return self.trains[0].signaling

    @property
    def ats(self) -> ATSController:
        return self.trains[0].ats

    @property
    def manual_driver(self) -> ManualDriveController:
        return self.trains[0].manual_driver

    @property
    def last_step(self) -> StepResult | None:
        return self.trains[0].last_step if self.trains else None

    @last_step.setter
    def last_step(self, value: StepResult | None) -> None:
        if self.trains:
            self.trains[0].last_step = value

    @classmethod
    def from_config_dir(cls, config_dir: str | Path | None = None) -> "Orchestrator":
        config_dir = Path(config_dir or CONFIG_DIR)
        sim_params = load_simulation_params(config_dir / "simulation.yaml")
        vehicle = VehicleSystem(load_vehicle_params(config_dir / "vehicle.yaml"))
        track = TrackPathService(load_track(config_dir / "track.yaml"))
        occupancy = OccupancyDetector(track.track.circuits)
        switch_manager = SwitchManager(track.track.switches)
        atp = ATPController(sim_params.signal.atp)
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

        orch = cls(
            vehicle=vehicle,
            track=track,
            atp=atp,
            clock=clock,
            sim_params=sim_params,
            power_network=power_network,
            occupancy=occupancy,
            switch_manager=switch_manager,
            _timetable_path=config_dir / "timetable.yaml",
        )
        orch._init_trains()
        return orch

    def _init_trains(self, passenger_load: float = 0.6) -> None:
        """按 train_count / departure_interval 创建各列车运行单元。"""
        base_tt = load_timetable(self._timetable_path)
        interval = self.sim_params.departure_interval
        self.trains = []
        for i in range(self.sim_params.train_count):
            train_id = f"TRAIN_{i + 1:02d}"
            timetable = Timetable(train_id=train_id, entries=list(base_tt.entries))
            ats = ATSController(self.sim_params.signal.ats, timetable)
            signaling = ThreeStageController(
                self.track, self.vehicle.params, self.sim_params, ats=ats
            )
            self.trains.append(
                TrainRun(
                    train_id=train_id,
                    state=self.vehicle.create_initial_state(
                        position=0.0, passenger_load=passenger_load
                    ),
                    signaling=signaling,
                    ats=ats,
                    manual_driver=ManualDriveController(),
                    spawn_time=i * interval,
                    active=(i == 0),
                )
            )

    def set_snapshot_callback(self, callback: Callable[[dict], None]) -> None:
        """注册每步快照回调（供 WebSocket 推送层使用）。"""
        self._on_snapshot = callback

    def set_emergency_brake(self, active: bool) -> None:
        """设置/解除手动紧急制动（作用于所有列车）。"""
        for run in self.trains:
            run.manual_driver.set_emergency_brake(active)

    def reset(self, passenger_load: float = 0.6) -> None:
        self.clock.reset()
        self.recorder.clear()
        self.occupancy.update({})  # 清空所有区段占用
        # Reset all switches to normal
        for sw in self.switch_manager._switches.values():
            sw.state = "normal"
            sw.transition_elapsed = 0.0
            sw._target_state = "normal"
        self._init_trains(passenger_load=passenger_load)
        self.run_state = RunState.IDLE
        self.last_snapshot = None

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

    def _spawn_trains(self, elapsed: float) -> None:
        """按发车间隔激活尚未发车的列车。"""
        for run in self.trains:
            if run.active or elapsed < run.spawn_time:
                continue
            passenger_load = run.state.passenger_load
            run.state = self.vehicle.create_initial_state(
                position=0.0, passenger_load=passenger_load
            )
            run.signaling.reset()
            run.active = True

    def _step_train(
        self,
        run: TrainRun,
        dt: float,
        elapsed: float,
        leading_pos: float | None = None,
    ) -> tuple[StepResult, ControlCommands, float, MaProfile, list[dict], float]:
        """步进单列车，返回动力学结果与 signaling 快照片段。"""
        track_params = self.track.query_at(run.state.position)
        speed_limit = effective_speed_limit_kmh(track_params, self.vehicle.params)
        cmd = run.signaling.compute_commands(run.state, dt, elapsed=elapsed)
        if self.atp.check_overspeed(run.state.speed, speed_limit) == SafetyStatus.EMERGENCY_BRAKE:
            cmd = ControlCommands(
                traction_level=0.0,
                brake_level=0.0,
                emergency_brake=True,
                phase=cmd.phase or run.signaling.signal_state.phase.value,
            )
        min_interval = self.sim_params.signal.following_min_interval
        if (
            leading_pos is not None
            and not is_interval_safe(leading_pos, run.state.position, min_interval)
        ):
            cmd = ControlCommands(
                traction_level=0.0,
                brake_level=0.0,
                emergency_brake=True,
                phase=cmd.phase or run.signaling.signal_state.phase.value,
            )
        cmd = run.manual_driver.get_commands(cmd)
        result = self.vehicle.step(
            run.state, cmd, track_params, dt, self.sim_params.pid.max_jerk
        )
        run.state = result.state
        run.last_step = result

        sig_st = run.signaling.signal_state
        run.state.distance_to_station = sig_st.distance_to_station
        run.state.target_station_id = sig_st.target_station_id

        target_chainage = (
            self.track.get_station_chainage(sig_st.target_station_id)
            if sig_st.target_station_id
            else None
        )
        ma = self.atp.build_ma_profile(
            run.train_id,
            run.state.position,
            target_chainage,
            leading_chainage=leading_pos,
        )

        timetable_dev: list[dict] = []
        if run.ats.last_deviation is not None:
            d = run.ats.last_deviation
            timetable_dev = [{
                "trainId": d.train_id,
                "stationId": d.station_id,
                "delayArrival": d.delay_arrival,
                "nominalDwell": d.nominal_dwell,
                "adjustedDwell": d.adjusted_dwell,
            }]

        v_ms = result.state.speed / 3.6 if result.state.speed > 0 else 0.0
        if result.forces.traction > 0:
            power_demand = calculate_traction_power(result.forces.traction, v_ms)
        elif result.forces.brake > 0:
            power_demand = -calculate_regen_power(
                result.forces.brake,
                v_ms,
                self.vehicle.params.regeneration_efficiency,
            )
        else:
            power_demand = 0.0

        return result, cmd, speed_limit, ma, timetable_dev, power_demand

    def step_once(self) -> dict | None:
        """推进一个仿真步（ENG-06 单步调试）。暂停/空闲时也可强制调用。"""
        if not self.trains:
            self.reset()
        assert self.trains

        dt = self.clock.time_step
        elapsed = self.clock.elapsed
        self._spawn_trains(elapsed)

        active_runs = [r for r in self.trains if r.active]
        if not active_runs:
            return None

        step_outputs: list[
            tuple[TrainRun, StepResult, ControlCommands, float, MaProfile, list[dict], float]
        ] = []
        sorted_runs = sorted(active_runs, key=lambda r: r.state.position)
        min_interval = self.sim_params.signal.following_min_interval
        for i, run in enumerate(sorted_runs):
            leading_pos = (
                sorted_runs[i + 1].state.position if i + 1 < len(sorted_runs) else None
            )
            result, cmd, speed_limit, ma, timetable_dev, power_demand = self._step_train(
                run, dt, elapsed, leading_pos=leading_pos
            )
            step_outputs.append(
                (run, result, cmd, speed_limit, ma, timetable_dev, power_demand)
            )

        self.clock.tick()

        leading = max(active_runs, key=lambda r: r.state.position)
        lead_result = leading.last_step
        assert lead_result is not None
        self.recorder.record(
            StepRecord(
                time=self.clock.elapsed,
                position=lead_result.state.position,
                speed=lead_result.state.speed,
                acceleration=lead_result.state.acceleration,
                jerk=lead_result.state.jerk,
                mode=lead_result.state.mode,
                traction_force=lead_result.forces.traction,
                brake_force=lead_result.forces.brake,
                total_resistance=lead_result.forces.resistance_total,
            )
        )

        self.occupancy.update({r.train_id: r.state.position for r in active_runs})
        self.switch_manager.update(dt)

        total_power_demand = sum(item[6] for item in step_outputs)
        power_mode = self.sim_params.power.mode
        sample_position = leading.state.position

        if power_mode == "simple_ohm":
            power_flow: PowerFlowResult = calculate(
                self.power_network,
                sample_position,
                total_power_demand,
            )
            pantograph_voltage = power_flow.pantograph_voltage
            substation_states = power_flow.substation_states
        else:
            from sim_engine.power.static_power import get_pantograph_voltage

            pantograph_voltage = get_pantograph_voltage()
            substation_states = []

        voltage_profile = [
            {"chainage": sample_position, "voltage": pantograph_voltage}
        ]

        train_entries: list[TrainSnapshotEntry] = []
        control_commands: list[dict] = []
        speed_limits: list[dict] = []
        ma_profiles: list[dict] = []
        timetable_deviations: list[dict] = []

        for run, result, cmd, speed_limit, ma, timetable_dev, train_power in step_outputs:
            sig_st = run.signaling.signal_state
            running_phase = cmd.phase or sig_st.phase.value
            train_entries.append(
                TrainSnapshotEntry(
                    train_id=run.train_id,
                    state=result.state,
                    forces=result.forces,
                    pantograph_voltage=pantograph_voltage,
                    power_demand=train_power,
                )
            )
            control_commands.append({
                "trainId": run.train_id,
                "tractionLevel": cmd.traction_level,
                "brakeLevel": cmd.brake_level,
                "emergencyBrake": cmd.emergency_brake,
                "runningPhase": running_phase,
            })
            speed_limits.append({
                "trainId": run.train_id,
                "permanentLimit": speed_limit,
                "atpLimit": self.atp.atp_speed_limit(speed_limit),
            })
            ma_profiles.append({
                "trainId": ma.train_id,
                "maEndChainage": ma.ma_end_chainage,
                "safetyDistance": ma.safety_distance,
            })
            timetable_deviations.extend(timetable_dev)

        train_intervals: list[dict] = []
        if len(sorted_runs) >= 2:
            post_sorted = sorted(active_runs, key=lambda r: r.state.position)
            for i in range(len(post_sorted) - 1):
                rear = post_sorted[i]
                front = post_sorted[i + 1]
                interval_m = front.state.position - rear.state.position
                train_intervals.append({
                    "trainId": rear.train_id,
                    "leadingTrainId": front.train_id,
                    "intervalM": interval_m,
                    "minIntervalM": min_interval,
                    "safe": is_interval_safe(
                        front.state.position, rear.state.position, min_interval
                    ),
                })

        snapshot = build_simulation_snapshot(
            self.clock,
            self.sim_params,
            train_entries,
            voltage_profile=voltage_profile,
            substation_states=substation_states,
            occupancy=self.occupancy.occupancy_list(),
            switch_states=self.switch_manager.switch_list(),
            signaling_extra={
                "controlCommands": control_commands,
                "speedLimits": speed_limits,
                "maProfile": ma_profiles,
                "timetableDeviation": timetable_deviations,
                "trainIntervals": train_intervals,
            },
        )
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
