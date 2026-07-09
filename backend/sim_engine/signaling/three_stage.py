"""三段式运行模式控制器（前馈制动版）。

牵引 → 惰行 → 制动：
- 牵引：开环满牵引，接近巡航速度时切惰行
- 制动：前馈（运动学公式）+ P 微调，精确停靠站台
- 接近站台时切换为蠕行模式，确保柔和停车

到站停车后等待站停时间再发车。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sim_engine.core.config import PidParams, SimulationParams
from sim_engine.signaling.pid_controller import PIDController
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

        # P-only 制动微调控制器
        self._brake_pid = PIDController(kp=sim_params.pid.kp_brake)

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
        self._brake_pid.reset()
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    def compute_commands(self, train: TrainState, dt: float) -> ControlCommands:
        st = self._state
        tol = self.sim_params.station_stop_tolerance

        # ── DWELL 站停倒计时 ──
        if st.phase == Phase.DWELL:
            st.dwell_remaining = max(0.0, st.dwell_remaining - dt)
            if st.dwell_remaining <= 0:
                st.phase = Phase.TRACTION
            return ControlCommands()

        target = self.track.next_station_ahead(train.position)

        # ── 跳站检测 ──
        if st._last_target_station_id and target is not None and target.id != st._last_target_station_id:
            old_station = self.track.get_station_by_id(st._last_target_station_id)
            if old_station is not None and train.position > old_station.chainage:
                if old_station.id != st._dwell_station_id:
                    if train.speed < 0.1 and abs(train.position - old_station.chainage) <= 50.0:
                        st.phase = Phase.DWELL
                        st.dwell_remaining = old_station.dwell_time
                        st._dwell_station_id = old_station.id
                        return ControlCommands()
                    st._dwell_station_id = old_station.id
        if target is not None:
            st._last_target_station_id = target.id

        if target is None:
            if train.speed > 0.1:
                return ControlCommands(brake_level=1.0)
            return ControlCommands()

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
            self._brake_pid.reset()
            return ControlCommands()

        if train.speed < 0.1 and dist_to_station > tol and train.position > tol:
            current_station = self.track.station_at(train.position, half_length=50.0)
            if current_station is not None and current_station.id != st._dwell_station_id:
                st.phase = Phase.DWELL
                st.dwell_remaining = current_station.dwell_time
                st._dwell_station_id = current_station.id
                self._brake_pid.reset()
                return ControlCommands()

        if train.speed < 0.1 and dist_to_station > tol:
            st.phase = Phase.TRACTION

        # ── TRACTION: 开环满牵引 ──
        if st.phase == Phase.TRACTION:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                return self._braking_step(train, target, dt)
            if train.speed >= v_cruise - 2.0:
                st.phase = Phase.COASTING
                return ControlCommands()
            return ControlCommands(traction_level=1.0)

        # ── COASTING: 惰行 + 开环补偿 ──
        if st.phase == Phase.COASTING:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                return self._braking_step(train, target, dt)
            curve_speed = PIDController.braking_curve_speed(
                max(dist_to_station, 1.0), self.sim_params.pid.comfort_decel
            )
            dynamic_min = min(curve_speed * 0.4, self.sim_params.coasting_min_speed)
            dynamic_min = max(dynamic_min, 5.0)
            if train.speed < dynamic_min:
                st.phase = Phase.TRACTION
                return ControlCommands(traction_level=1.0)
            comp = self._coasting_compensation(train, track_params)
            return ControlCommands(traction_level=comp, phase="coasting")

        # ── BRAKING: 前馈 + P 微调 ──
        return self._braking_step(train, target, dt)

    # ── 制动阶段核心 ──

    def _braking_step(
        self, train: TrainState, target: Station, dt: float
    ) -> ControlCommands:
        """前馈制动 + P 微调。

        前馈：根据运动学 a = v²/2d 计算所需减速度，减去阻力贡献后反推制动级位。
        P 微调：以 ATO 制动曲线为目标做归一化误差修正。
        """
        remaining = max(target.chainage - train.position, 0.0)
        pp = self.sim_params.pid

        # 蠕行
        if remaining <= pp.deadband_d and train.speed < 3.0:
            return self._creep_brake(remaining)

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
        v_target_kmh = PIDController.braking_curve_speed(remaining, pp.comfort_decel)
        if v_target_kmh > 1.0:
            error = (train.speed - v_target_kmh) / v_target_kmh
        else:
            error = 0.0
        trim = self._brake_pid.compute(error)

        brake = max(0.0, min(brake_ff + trim, 1.0))
        return ControlCommands(brake_level=brake)

    def _creep_brake(self, remaining_m: float) -> ControlCommands:
        """蠕行模式：制动力与剩余距离成正比。"""
        pp = self.sim_params.pid
        brake = min(remaining_m * pp.creep_gain, 0.5)
        brake = max(brake, 0.02)
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