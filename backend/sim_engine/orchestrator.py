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
from sim_engine.signaling.fleet_scheduler import FleetScheduler
from sim_engine.signaling.models import MaProfile, SafetyStatus, ServiceTimetable, Timetable, TimetableEntry
from sim_engine.signaling.three_stage import ThreeStageController
from sim_engine.signaling.timetable_loader import load_service_timetable, load_timetable, materialize_trip_timetables
from sim_engine.signaling.train_following import is_interval_safe, tracking_gap
from sim_engine.signaling.turnback import TurnbackController
from sim_engine.track.config import load_track
from sim_engine.track.occupancy import OccupancyDetector
from sim_engine.track.switch import SwitchManager
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.dynamics import VehicleSystem, effective_speed_limit_kmh
from sim_engine.vehicle.models import ControlCommands, StepResult, TrainState

# 外部系统桥接 — 已弃用（外部系统接入方案已废弃）
# from sim_engine.external.bridge import ExternalBridge

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def _start_chainage(direction: str, total_length: float) -> float:
    """方向对应的线路起点 chainage。"""
    return total_length if direction == "up" else 0.0


def _fleet_directions(sim_params: SimulationParams, vehicle_direction: str) -> list[tuple[str, str]]:
    """返回 (direction, id_prefix) 列表。prefix 为空时沿用 TRAIN_01 编号。"""
    if sim_params.bidirectional:
        return [("down", "D"), ("up", "U")]
    return [(vehicle_direction, "")]


def _format_train_id(prefix: str, index: int) -> str:
    if prefix:
        return f"TRAIN_{prefix}{index + 1:02d}"
    return f"TRAIN_{index + 1:02d}"


def _leading_chainage(
    sorted_runs: list["TrainRun"], index: int, direction: str
) -> float | None:
    """同向队列中指定列车的前方列车 chainage。"""
    if direction == "down":
        if index + 1 < len(sorted_runs):
            return sorted_runs[index + 1].state.position
        return None
    if index > 0:
        return sorted_runs[index - 1].state.position
    return None


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
    direction: str = "up"
    trip_leg_names: tuple[str, ...] = ()
    last_step: StepResult | None = None
    legs: list[Timetable] = field(default_factory=list)
    leg_index: int = 0
    turnback_state: str | None = None
    vehicle_id: str = ""
    total_trips: int = 0
    total_mileage: float = 0.0


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
    _service_timetable: ServiceTimetable | None = None
    _fleet_scheduler: FleetScheduler | None = None
    _turnback: TurnbackController | None = None
    _passenger_load: float = 0.6
    run_state: RunState = RunState.IDLE
    last_snapshot: dict | None = None
    _on_snapshot: Callable[[dict], None] | None = None

    # 外部系统桥接 — 已弃用（外部系统接入方案已废弃）
    # external_bridge: ExternalBridge | None = None

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

        # 外部系统桥接 — 已弃用（外部系统接入方案已废弃）
        # external_bridge = None
        # if sim_params.external.enabled:
        #     from sim_engine.external.bridge import ExternalBridge
        #     external_bridge = ExternalBridge(
        #         plc_host=sim_params.external.plc_device_ip,
        #         plc_port=sim_params.external.plc_port,
        #         hmi_host=sim_params.external.network_screen_device_ip,
        #         hmi_port=sim_params.external.network_screen_port,
        #         mmi_host=sim_params.external.signal_screen_device_ip,
        #         mmi_port=sim_params.external.signal_screen_port,
        #         use_real_hardware=sim_params.external.use_real_hardware,
        #     )
        #     external_bridge.start_all()

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
            # external_bridge=external_bridge,
        )
        station_chainages = {s.id: s.chainage for s in track.track.stations}
        orch._service_timetable = load_service_timetable(
            orch._timetable_path, station_chainages
        )
        if orch._is_continuous():
            orch._fleet_scheduler = FleetScheduler(
                orch._service_timetable, station_chainages
            )
            orch._turnback = TurnbackController(orch._service_timetable)
        orch._init_trains()
        return orch

    def _is_continuous(self) -> bool:
        return (
            self._service_timetable is not None
            and self._service_timetable.dispatch.mode == "continuous"
        )

    def _init_trains(self, passenger_load: float = 0.6) -> None:
        """continuous 模式空车队；fixed 模式按 train_count 预创建。"""
        self._passenger_load = passenger_load
        if self._is_continuous():
            self.trains = []
            if self._fleet_scheduler is not None:
                self._fleet_scheduler.reset()
            return
        self._init_trains_fixed(passenger_load)

    def _init_trains_fixed(self, passenger_load: float = 0.6) -> None:
        """按 train_count / departure_interval / bidirectional 创建各列车运行单元。"""
        base_tt = load_timetable(self._timetable_path)
        interval = self.sim_params.departure_interval
        total_length = self.track.track.total_length
        self.trains = []

        for direction, id_prefix in _fleet_directions(
            self.sim_params, self.vehicle.params.direction
        ):
            start_pos = _start_chainage(direction, total_length)
            for i in range(self.sim_params.train_count):
                train_id = _format_train_id(id_prefix, i)
                spawn_time = i * interval
                timetable = Timetable(
                    train_id=train_id,
                    entries=[
                        TimetableEntry(
                            station_id=e.station_id,
                            planned_arrival=e.planned_arrival + spawn_time,
                            planned_departure=e.planned_departure + spawn_time,
                        )
                        for e in base_tt.entries
                    ],
                )
                ats = ATSController(self.sim_params.signal.ats, timetable)
                signaling = ThreeStageController(
                    self.track, self.vehicle.params, self.sim_params, ats=ats
                )
                signaling.reset(direction=direction)
                self.trains.append(
                    TrainRun(
                        train_id=train_id,
                        state=self.vehicle.create_initial_state(
                            position=start_pos,
                            passenger_load=passenger_load,
                            direction=direction,
                        ),
                        signaling=signaling,
                        ats=ats,
                        manual_driver=ManualDriveController(),
                        spawn_time=spawn_time,
                        active=(i == 0),
                        direction=direction,
                    )
                )

    def _create_train_run(
        self,
        train_id: str,
        spawn_time: float,
        direction: str,
        trip_leg_names: tuple[str, ...],
        start_pos: float | None = None,
        vehicle_id: str = "",
        total_trips: int = 0,
        passenger_load: float | None = None,
    ) -> TrainRun:
        """continuous 模式动态创建列车（支持 buffer 旧车复用）。"""
        assert self._service_timetable is not None
        legs = materialize_trip_timetables(
            self._service_timetable, train_id, trip_leg_names
        )
        total_length = self.track.track.total_length
        if start_pos is None:
            start_pos = _start_chainage(direction, total_length)
        abs_tt = legs[0].with_absolute_times(spawn_time)
        ats = ATSController(self.sim_params.signal.ats, abs_tt)
        signaling = ThreeStageController(
            self.track, self.vehicle.params, self.sim_params, ats=ats
        )
        signaling.reset(direction=direction)
        pl = passenger_load if passenger_load is not None else self._passenger_load
        return TrainRun(
            train_id=train_id,
            vehicle_id=vehicle_id or self._next_vehicle_id(),
            state=self.vehicle.create_initial_state(
                position=start_pos,
                passenger_load=pl,
                direction=direction,
            ),
            signaling=signaling,
            ats=ats,
            manual_driver=ManualDriveController(),
            spawn_time=spawn_time,
            active=True,
            direction=direction,
            legs=legs,
            leg_index=0,
            trip_leg_names=trip_leg_names,
            total_trips=total_trips,
            total_mileage=0.0,
        )

    def _next_vehicle_id(self) -> str:
        """生成全局唯一 vehicle_id。"""
        if not hasattr(self, '_vehicle_serial'):
            self._vehicle_serial = 0
        self._vehicle_serial += 1
        return f"VEH_{self._vehicle_serial:03d}"

    def _tick_continuous_dispatch(self, elapsed: float) -> None:
        assert self._fleet_scheduler is not None

        def create_run(
            train_id: str,
            spawn_time: float,
            direction: str,
            trip_leg_names: tuple[str, ...],
            start_pos: float,
            vehicle_id: str = "",
            total_trips: int = 0,
            passenger_load: float = 0.6,
        ) -> None:
            self.trains.append(
                self._create_train_run(
                    train_id, spawn_time, direction, trip_leg_names, start_pos,
                    vehicle_id=vehicle_id,
                    total_trips=total_trips,
                    passenger_load=passenger_load,
                )
            )

        active = [r for r in self.trains if r.active]
        self._fleet_scheduler.tick(elapsed, active, create_run)

    def _at_terminal(self, run: TrainRun) -> bool:
        """判断列车是否到达终点站并停稳。"""
        if run.state.speed >= 0.1:
            return False
        total = self.track.track.total_length
        if run.direction == "down":
            return run.state.position >= total - 1.0
        return run.state.position <= 1.0

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
        if not self.trains and not self._is_continuous():
            self.reset(passenger_load)
        elif self._is_continuous() and self.run_state == RunState.IDLE:
            self.reset(passenger_load)
        elif self.train_state is None:
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
        total_length = self.track.track.total_length
        for run in self.trains:
            if run.active or elapsed < run.spawn_time:
                continue
            passenger_load = run.state.passenger_load
            start_pos = _start_chainage(run.direction, total_length)
            run.state = self.vehicle.create_initial_state(
                position=start_pos,
                passenger_load=passenger_load,
                direction=run.direction,
            )
            run.signaling.reset(direction=run.direction)
            run.active = True

    def _step_train(
        self,
        run: TrainRun,
        dt: float,
        elapsed: float,
        leading_pos: float | None = None,
        direction: str = "down",
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
            and not is_interval_safe(
                leading_pos, run.state.position, min_interval, direction=direction
            )
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
        if self._service_timetable is None:
            station_chainages = {
                s.id: s.chainage for s in self.track.track.stations
            }
            self._service_timetable = load_service_timetable(
                self._timetable_path, station_chainages
            )
            if self._is_continuous():
                self._fleet_scheduler = FleetScheduler(
                    self._service_timetable, station_chainages
                )
                self._turnback = TurnbackController(self._service_timetable)

        dt = self.clock.time_step
        elapsed = self.clock.elapsed
        if self._is_continuous():
            self._tick_continuous_dispatch(elapsed)
        else:
            if not self.trains:
                self._init_trains_fixed(self._passenger_load)
            self._spawn_trains(elapsed)

        # ── 列车到达终点→存入存车线 ──
        if self._fleet_scheduler is not None:
            for run in self.trains:
                if not run.active:
                    continue
                if self._at_terminal(run):
                    run.active = False
                    self._fleet_scheduler.receive_train(run)

        active_runs = [r for r in self.trains if r.active]
        if not active_runs:
            self.clock.tick()
            return None

        step_outputs: list[
            tuple[TrainRun, StepResult, ControlCommands, float, MaProfile, list[dict], float]
        ] = []
        min_interval = self.sim_params.signal.following_min_interval
        directions = sorted({r.direction for r in active_runs})
        for direction in directions:
            dir_runs = [r for r in active_runs if r.direction == direction]
            sorted_runs = sorted(dir_runs, key=lambda r: r.state.position)
            for i, run in enumerate(sorted_runs):
                leading_pos = _leading_chainage(sorted_runs, i, direction)
                if (
                    self._turnback is not None
                    and run.turnback_state is not None
                    and self._turnback.step(run, elapsed, self.switch_manager, dt)
                ):
                    continue
                if self._turnback is not None and self._turnback.at_terminal_dwell(run):
                    if run.leg_index + 1 < len(run.legs) and run.turnback_state is None:
                        self._turnback.step(run, elapsed, self.switch_manager, dt)
                        continue
                result, cmd, speed_limit, ma, timetable_dev, power_demand = self._step_train(
                    run, dt, elapsed, leading_pos=leading_pos, direction=direction
                )
                step_outputs.append(
                    (run, result, cmd, speed_limit, ma, timetable_dev, power_demand)
                )

        self.clock.tick()

        leading = max(
            (r for r in active_runs if r.last_step is not None),
            key=lambda r: r.state.position,
            default=None,
        )
        if leading is None:
            return None
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

        self.occupancy.update({r.train_id: (r.state.position, r.state.direction) for r in active_runs})
        self.switch_manager.update(dt)

        # ── 多列车独立变电所分配 ──
        train_demands = [
            {"position": item[0].state.position, "power": item[6]}
            for item in step_outputs
        ]
        power_mode = self.sim_params.power.mode

        if power_mode == "simple_ohm":
            power_flow: PowerFlowResult = calculate(
                self.power_network,
                train_demands,
            )
            pantograph_voltage = power_flow.pantograph_voltage
            substation_states = power_flow.substation_states
        else:
            from sim_engine.power.static_power import get_pantograph_voltage

            pantograph_voltage = get_pantograph_voltage()
            substation_states = []

        # 每列车独立计算受电弓端电压
        def _per_train_voltage(pos: float, power_w: float) -> float:
            if power_w <= 0 or not self.power_network.substations:
                return 1500.0
            nearest = min(self.power_network.substations, key=lambda s: abs(s.chainage - pos))
            dist_km = abs(pos - nearest.chainage) / 1000.0
            r_total = self.power_network.contact_line_resistance + self.power_network.rail_resistance
            current = power_w / 1500.0
            drop = current * r_total * dist_km
            return max(1500.0 - drop, 1000.0)

        voltage_profile = [
            {"chainage": item[0].state.position, "voltage": _per_train_voltage(item[0].state.position, item[6])}
            for item in step_outputs
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
                    pantograph_voltage=_per_train_voltage(run.state.position, train_power),
                    power_demand=train_power,
                    direction=run.state.direction,
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
        for direction in directions:
            dir_runs = [r for r in active_runs if r.direction == direction]
            if len(dir_runs) < 2:
                continue
            post_sorted = sorted(dir_runs, key=lambda r: r.state.position)
            if direction == "down":
                pairs = [
                    (post_sorted[i], post_sorted[i + 1])
                    for i in range(len(post_sorted) - 1)
                ]
            else:
                pairs = [
                    (post_sorted[i + 1], post_sorted[i])
                    for i in range(len(post_sorted) - 1)
                ]
            for rear, front in pairs:
                interval_m = tracking_gap(front.state.position, rear.state.position, direction)
                train_intervals.append({
                    "trainId": rear.train_id,
                    "leadingTrainId": front.train_id,
                    "intervalM": interval_m,
                    "minIntervalM": min_interval,
                    "safe": is_interval_safe(
                        front.state.position,
                        rear.state.position,
                        min_interval,
                        direction=direction,
                    ),
                })

        buffer_state = {}
        if self._fleet_scheduler is not None:
            buffer_state = self._fleet_scheduler.buffer_state()

        snapshot = build_simulation_snapshot(
            self.clock,
            self.sim_params,
            train_entries,
            voltage_profile=voltage_profile,
            buffer_state=buffer_state,
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

        # 外部系统输出 — 已弃用（外部系统接入方案已废弃）
        # if self.external_bridge is not None:
        #     self.external_bridge.update_from_engine(snapshot, self.sim_params)

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
            if self.train_state:
                if self.train_state.direction == "up":
                    if self.train_state.position <= 1.0 and self.train_state.speed < 0.1:
                        break
                else:
                    if self.train_state.position >= self.track.track.total_length - 1.0 and self.train_state.speed < 0.1:
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
