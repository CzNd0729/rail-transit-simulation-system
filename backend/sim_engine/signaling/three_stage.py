"""三段式运行模式控制器（前馈制动版）。

牵引 → 惰行 → 制动：
- 牵引：开环满牵引，接近巡航速度时切惰行
- 制动：前馈（运动学公式 a = v²/2d）+ P 微调，全程工作到站台停稳
- 前馈在每个时间步根据 v²/2d 自修正，无需蠕行模式

到站停车后等待站停时间再发车。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sim_engine.core.config import PidParams, SimulationParams
from sim_engine.signaling.ato import ATOController
from sim_engine.track.models import Station
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.dynamics import effective_speed_limit_kmh
from sim_engine.vehicle.models import GRAVITY, ControlCommands, TrainState, VehicleParams
from sim_engine.vehicle.traction import interpolate_force_percent


class Phase(str, Enum):
    TRACTION = "traction"
    COASTING = "coasting"
    BRAKING = "braking"
    DWELL = "dwell"


@dataclass
class TrainSignalState:
    phase: Phase = Phase.TRACTION
    dwell_remaining: float = 0.0
    _dwell_station_id: str = ""
    _last_target_station_id: str = ""
    _brake_target_id: str = ""
    """制动阶段的目标站 ID，进入 BRAKING 时锁定。防止越站后 next_station_ahead 切换导致制动目标丢失。"""
    distance_to_station: float = 0.0
    """距当前目标站距离 (m)。"""
    target_station_id: str = ""
    """当前目标站 ID。"""


class ThreeStageController:
    """为单列车生成控车指令。

    牵引阶段：开环满牵引，无 PID。
    制动阶段：前馈（运动学公式）+ P 微调。
    """

    def __init__(
        self,
        track: TrackPathService,
        vehicle_params: VehicleParams,
        sim_params: SimulationParams,
    ):
        self.track = track
        self.vehicle_params = vehicle_params
        self.sim_params = sim_params
        self._state = TrainSignalState()
        self._prev_traction_level = 0.0
        self._prev_brake_level = 0.0

        pp = sim_params.pid
        self._ato = ATOController(kp_brake=pp.kp_brake, comfort_decel=pp.comfort_decel)

        # 标记首站为已停靠，防止兜底检测误判刚离站的列车
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    @property
    def signal_state(self) -> TrainSignalState:
        return self._state

    @property
    def pid_params(self) -> PidParams:
        """制动 PID 参数（测试可通过此属性验证配置）。"""
        return self.sim_params.pid

    def reset(self) -> None:
        self._state = TrainSignalState()
        self._prev_traction_level = 0.0
        self._prev_brake_level = 0.0
        self._ato.reset()
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    def _max_level_delta(self, train: TrainState, dt: float) -> float:
        """由 max_jerk 推导每步允许的最大牵引/制动级位变化量。

        Δlevel ≈ (m · jerk_max · dt) / F_max
        """
        mass = train.mass if train.mass > 0 else self.vehicle_params.mass_at_load(
            train.passenger_load
        )
        p = self.vehicle_params
        max_force = max(p.max_traction_force, p.max_brake_force)
        if max_force <= 0 or dt <= 0:
            return 1.0
        jerk = self.sim_params.pid.max_jerk
        return min(1.0, mass * jerk * dt / max_force)

    @staticmethod
    def _slew(prev: float, target: float, max_delta: float) -> float:
        delta = target - prev
        if delta > max_delta:
            return prev + max_delta
        if delta < -max_delta:
            return prev - max_delta
        return target

    def _finalize_commands(
        self,
        cmd: ControlCommands,
        train: TrainState,
        dt: float,
        *,
        urgent_brake: bool = False,
    ) -> ControlCommands:
        """对目标级位做斜率限制，避免牵引/制动阶跃引发冲击率尖峰。"""
        if cmd.emergency_brake:
            self._prev_traction_level = 0.0
            self._prev_brake_level = 1.0
            return cmd

        max_delta = self._max_level_delta(train, dt)

        # 牵引与制动互斥：先完全释放对立级位，再爬升目标级位（同一步不同时变化）
        if cmd.traction_level > 0 and cmd.brake_level == 0:
            if self._prev_brake_level > 0:
                brake = self._slew(self._prev_brake_level, 0.0, max_delta)
                traction = self._prev_traction_level
            else:
                brake = 0.0
                traction = self._slew(self._prev_traction_level, cmd.traction_level, max_delta)
        elif cmd.brake_level > 0 and cmd.traction_level == 0:
            if self._prev_traction_level > 0:
                traction = self._slew(self._prev_traction_level, 0.0, max_delta)
                brake = self._prev_brake_level
            elif urgent_brake and cmd.brake_level > self._prev_brake_level:
                traction = 0.0
                brake = cmd.brake_level
            else:
                traction = 0.0
                brake = self._slew(self._prev_brake_level, cmd.brake_level, max_delta)
        else:
            traction = self._slew(self._prev_traction_level, cmd.traction_level, max_delta)
            if urgent_brake and cmd.brake_level > self._prev_brake_level:
                brake = cmd.brake_level
            else:
                brake = self._slew(self._prev_brake_level, cmd.brake_level, max_delta)

        self._prev_traction_level = traction
        self._prev_brake_level = brake
        return ControlCommands(
            traction_level=traction,
            brake_level=brake,
            emergency_brake=cmd.emergency_brake,
            phase=cmd.phase,
        )

    def _update_distance(self, train: TrainState, target: Station | None) -> None:
        """更新距当前目标站距离。"""
        st = self._state
        if target is not None:
            st.target_station_id = target.id
            st.distance_to_station = target.chainage - train.position
        else:
            st.target_station_id = ""
            st.distance_to_station = 0.0

    def compute_commands(self, train: TrainState, dt: float) -> ControlCommands:
        st = self._state
        tol = self.sim_params.station_stop_tolerance

        # ── DWELL 站停倒计时 ──
        if st.phase == Phase.DWELL:
            st.dwell_remaining = max(0.0, st.dwell_remaining - dt)
            if st.dwell_remaining <= 0:
                st.phase = Phase.TRACTION
                return self._finalize_commands(ControlCommands(), train, dt)
            return self._finalize_commands(
                ControlCommands(brake_level=0.20, phase="dwell"), train, dt
            )

        target = self.track.next_station_ahead(train.position)

        # 制动阶段锁定目标站：进入 BRAKING 时保存的目标站 ID，
        # 防止越过站台后 next_station_ahead 切换为下一站导致前馈制动归零
        if st.phase == Phase.BRAKING and st._brake_target_id:
            brake_target = self.track.get_station_by_id(st._brake_target_id)
            if brake_target is not None:
                target = brake_target

        # ── 跳站检测 ──
        if st._last_target_station_id and target is not None and target.id != st._last_target_station_id:
            old_station = self.track.get_station_by_id(st._last_target_station_id)
            if old_station is not None and train.position > old_station.chainage:
                if old_station.id != st._dwell_station_id:
                    if train.speed < 0.1 and abs(train.position - old_station.chainage) <= 50.0:
                        st.phase = Phase.DWELL
                        st.dwell_remaining = old_station.dwell_time
                        st._dwell_station_id = old_station.id
                        self._update_distance(train, old_station)
                        return self._finalize_commands(
                            ControlCommands(brake_level=0.20, phase="dwell"), train, dt
                        )
                    # 蠕行模式（≤3 km/h）时不标记已过站，保留兜底检测机会
                    if train.speed > 3.0:
                        st._dwell_station_id = old_station.id
        if target is not None:
            st._last_target_station_id = target.id

        if target is None:
            self._update_distance(train, None)
            if train.speed > 0.1:
                return self._finalize_commands(
                    ControlCommands(brake_level=1.0), train, dt, urgent_brake=True
                )
            return self._finalize_commands(ControlCommands(), train, dt)

        track_params = self.track.query_at(train.position)
        speed_limit = effective_speed_limit_kmh(track_params, self.vehicle_params)
        v_cruise = self.sim_params.target_speed_ratio * speed_limit
        brake_dist = self._brake_trigger_distance(train)
        dist_to_station = target.chainage - train.position

        # ── 到站停稳检测 ──
        if train.speed < 0.1 and abs(dist_to_station) <= tol:
            st.phase = Phase.DWELL
            st.dwell_remaining = target.dwell_time
            st._dwell_station_id = target.id
            self._ato.reset()
            self._update_distance(train, target)
            return self._finalize_commands(
                ControlCommands(brake_level=0.20, phase="dwell"), train, dt
            )

        if train.speed < 0.1 and dist_to_station > tol and train.position > tol:
            current_station = self.track.station_at(train.position, half_length=50.0)
            if current_station is not None and current_station.id != st._dwell_station_id:
                st.phase = Phase.DWELL
                st.dwell_remaining = current_station.dwell_time
                st._dwell_station_id = current_station.id
                self._ato.reset()
                self._update_distance(train, current_station)
                return self._finalize_commands(
                    ControlCommands(brake_level=0.20, phase="dwell"), train, dt
                )

        if train.speed < 0.1 and dist_to_station > tol:
            st.phase = Phase.TRACTION

        # ── TRACTION: 开环满牵引 ──
        if st.phase == Phase.TRACTION:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                st._brake_target_id = target.id
                self._update_distance(train, target)
                return self._braking_output(train, target, dt)
            if train.speed >= v_cruise - 2.0:
                st.phase = Phase.COASTING
                self._update_distance(train, target)
                return self._finalize_commands(ControlCommands(), train, dt)
            self._update_distance(train, target)
            return self._finalize_commands(
                ControlCommands(traction_level=1.0), train, dt
            )

        # ── COASTING: 惰行 + 开环补偿 ──
        if st.phase == Phase.COASTING:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                st._brake_target_id = target.id
                self._update_distance(train, target)
                return self._braking_output(train, target, dt)
            curve_speed = self._ato.target_speed_on_curve(max(dist_to_station, 1.0))
            dynamic_min = min(curve_speed * 0.4, self.sim_params.coasting_min_speed)
            dynamic_min = max(dynamic_min, 5.0)
            if train.speed < dynamic_min:
                st.phase = Phase.TRACTION
                self._update_distance(train, target)
                return self._finalize_commands(
                    ControlCommands(traction_level=1.0), train, dt
                )
            comp = self._coasting_compensation(train, track_params)
            self._update_distance(train, target)
            return self._finalize_commands(
                ControlCommands(traction_level=comp, phase="coasting"), train, dt
            )

        # ── BRAKING: 前馈 + P 微调 ──
        self._update_distance(train, target)
        return self._braking_output(train, target, dt)

    # ── 制动阶段核心 ──

    def _braking_output(
        self, train: TrainState, target: Station, dt: float
    ) -> ControlCommands:
        raw = self._braking_step(train, target, dt)
        remaining = target.chainage - train.position
        urgent = (
            raw.brake_level >= 1.0
            and remaining <= 0
            and train.speed >= 3.0
        )
        return self._finalize_commands(raw, train, dt, urgent_brake=urgent)

    def _braking_step(
        self, train: TrainState, target: Station, dt: float
    ) -> ControlCommands:
        """前馈制动 + P 微调。

        前馈：根据运动学 a = v²/2d 计算所需减速度，减去阻力贡献后反推制动级位。
        P 微调：以 ATO 制动曲线为目标做归一化误差修正。
        全程工作到站台停稳，不使用蠕行模式。
        """
        remaining = target.chainage - train.position

        # 已越过站台：低速时保持制动而非满制动，避免停稳瞬间冲击率尖峰
        if remaining <= 0:
            if train.speed < 3.0:
                return ControlCommands(brake_level=0.20)
            return ControlCommands(brake_level=1.0)

        v_ms = train.speed / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass

        # 前馈：运动学所需减速度
        if remaining > 0.1:
            a_required = (v_ms * v_ms) / (2.0 * remaining)
        else:
            a_required = 0.0

        # 当前阻力也在帮忙减速
        track_params = self.track.query_at(train.position)
        resistance = self._calc_resistance(train, track_params)
        a_from_resistance = resistance / mass

        # 制动力需要提供的减速度
        a_from_brake = max(0.0, a_required - a_from_resistance)
        brake_ff = (mass * a_from_brake) / self.vehicle_params.max_brake_force
        brake_ff = min(brake_ff, 1.0)

        # P 微调：以 ATO 制动曲线为目标
        trim = self._ato.compute_trim(train.speed, remaining)

        brake = max(0.0, min(brake_ff + trim, 1.0))
        return ControlCommands(brake_level=brake)

    # ── 制动触发距离 ──

    def _brake_trigger_distance(self, train: TrainState) -> float:
        v_ms = max(train.speed, 0.0) / 3.6
        decel = self.sim_params.pid.comfort_decel
        if decel <= 0:
            return 0.0
        safety = self.sim_params.pid.brake_safety_factor
        return (v_ms * v_ms) / (2 * decel) * safety

    # ── 阻力计算（前馈用） ──

    def _calc_resistance(self, train: TrainState, track_params) -> float:
        """计算当前总阻力 (N)。"""
        from sim_engine.vehicle import resistance as R

        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params
        r_davis = R.davis_resistance(p, mass, train.speed)
        r_gradient = R.gradient_resistance(mass, track_params.gradient)
        r_curve = R.curve_resistance(mass, track_params.curvature, p.curve_resist_coeff)
        r_tunnel = R.tunnel_resistance(r_davis, track_params.is_tunnel, p.tunnel_resist_factor)
        return r_davis + r_curve + r_tunnel + r_gradient

    # ── 惰行补偿（与原相同） ──

    def _coasting_compensation(
        self, train: TrainState, track_params
    ) -> float:
        v_ms = abs(train.speed) / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params

        rolling = (p.davis_a + p.davis_b * v_ms) * mass * GRAVITY
        gradient_force = mass * GRAVITY * (track_params.gradient / 1000.0)
        f_target = rolling + gradient_force
        if f_target <= 0:
            return 0.0

        percent = interpolate_force_percent(p.traction_curve, train.speed)
        max_available = p.max_traction_force * percent
        if max_available <= 0:
            return 0.0

        level = f_target / max_available
        return min(max(level, 0.0), 1.0)