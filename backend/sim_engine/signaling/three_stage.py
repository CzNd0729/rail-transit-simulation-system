"""三段式运行模式控制器（PID 闭环版）。

牵引 → 惰行 → 制动，牵引与制动阶段由 PID 闭环调节：
- 牵引：PID 平滑逼近目标巡航速度
- 制动：PID 跟踪 ATO 制动曲线 v=√(2a·d)，精确停靠站台
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


class ThreeStageController:
    """为单列车生成 PID 闭环控车指令。

    牵引阶段使用 PID 平滑逼近目标速度，避免满牵引-切断-再满牵引
    的锯齿；制动阶段使用 ATO 制动曲线 v=√(2a·d) 作为 setpoint，
    PID 实时调节制动力以实现精确停车。

    注意：惰行阶段仍使用开环补偿，不做 PID 调节；惰行本身已是
    "收油门"的过渡态，PID 调节价值有限。
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

        # --- PID 控制器 ---
        pid = sim_params.pid
        # 牵引 PID：输出限制为 [0, 1]（仅牵引）
        self._traction_pid = PIDController(PidParams(
            kp=pid.kp,
            ki=pid.ki,
            kd=pid.kd * 0.5,           # 牵引对微分需求低，减半
            integral_max=pid.integral_max,
            output_min=0.0,
            output_max=1.0,
            comfort_decel=pid.comfort_decel,
            deadband_v=pid.deadband_v,
        ))
        # 制动 PID：输出限制为 [0, 1]（仅制动）
        self._brake_pid = PIDController(PidParams(
            kp=pid.kp,
            ki=pid.ki,
            kd=pid.kd,
            integral_max=pid.integral_max,
            output_min=0.0,
            output_max=1.0,
            comfort_decel=pid.comfort_decel,
            deadband_v=pid.deadband_v,
        ))

        # 标记首站为已停靠，防止兜底检测误判刚离站的列车
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    @property
    def signal_state(self) -> TrainSignalState:
        return self._state

    @property
    def pid_params(self) -> PidParams:
        """制动 PID 参数（测试可通过此属性验证配置）。"""
        return self._brake_pid._p

    def reset(self) -> None:
        self._state = TrainSignalState()
        self._traction_pid.reset()
        self._brake_pid.reset()
        if self.track._stations:
            self._state._dwell_station_id = self.track._stations[0].id

    # ── 主入口 ───────────────────────────────────────────────────────

    def compute_commands(self, train: TrainState, dt: float) -> ControlCommands:
        st = self._state
        tol = self.sim_params.station_stop_tolerance

        # ============================================================
        # DWELL：站停倒计时
        # ============================================================
        if st.phase == Phase.DWELL:
            st.dwell_remaining = max(0.0, st.dwell_remaining - dt)
            if st.dwell_remaining <= 0:
                st.phase = Phase.TRACTION
                self._traction_pid.reset()
            return ControlCommands()

        target = self.track.next_station_ahead(train.position)
        if target is None:
            if train.speed > 0.1:
                return ControlCommands(brake_level=1.0)
            return ControlCommands()

        track_params = self.track.query_at(train.position)
        speed_limit = effective_speed_limit_kmh(track_params, self.vehicle_params)
        v_cruise = self.sim_params.target_speed_ratio * speed_limit
        brake_dist = self._brake_trigger_distance(train)
        dist_to_station = target.chainage - train.position

        # ============================================================
        # 到站停稳检测（两阶段，同上一版）
        # ============================================================

        # 主检测：next_station_ahead 仍指向当前站
        if train.speed < 0.1 and abs(dist_to_station) <= tol:
            st.phase = Phase.DWELL
            st.dwell_remaining = target.dwell_time
            st._dwell_station_id = target.id
            self._traction_pid.reset()
            self._brake_pid.reset()
            return ControlCommands()

        # 兜底检测：制动偏差超出 tol，但确实停在站台附近
        if train.speed < 0.1 and dist_to_station > tol and train.position > tol:
            current_station = self.track.station_at(train.position, half_length=50.0)
            if current_station is not None and current_station.id != st._dwell_station_id:
                st.phase = Phase.DWELL
                st.dwell_remaining = current_station.dwell_time
                st._dwell_station_id = current_station.id
                self._traction_pid.reset()
                self._brake_pid.reset()
                return ControlCommands()

        # 中途停住 → 重新牵引
        if train.speed < 0.1 and dist_to_station > tol:
            st.phase = Phase.TRACTION
            self._traction_pid.reset()

        # ============================================================
        # TRACTION：PID 平滑加速到巡航速度
        # ============================================================
        if st.phase == Phase.TRACTION:
            # 达到巡航速度 → 惰行；+0.5 防止频繁抖动
            if train.speed >= v_cruise - 0.5:
                st.phase = Phase.COASTING
                self._traction_pid.reset()
                return ControlCommands()
            traction = self._traction_pid.compute(v_cruise, train.speed, dt)
            return ControlCommands(traction_level=traction)

        # ============================================================
        # COASTING：惰行 + 开环补偿（不变）
        # ============================================================
        if st.phase == Phase.COASTING:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                self._brake_pid.reset()
                return self._braking_step(train, target, dt)
            if train.speed < self.sim_params.coasting_min_speed:
                st.phase = Phase.TRACTION
                self._traction_pid.reset()
                return ControlCommands(traction_level=1.0)
            comp = self._coasting_compensation(train, track_params)
            return ControlCommands(traction_level=comp, phase="coasting")

        # ============================================================
        # BRAKING：PID 跟踪 ATO 制动曲线
        # ============================================================
        return self._braking_step(train, target, dt)

    # ── 制动阶段逻辑 ──────────────────────────────────────────────────

    def _braking_step(
        self, train: TrainState, target: Station, dt: float
    ) -> ControlCommands:
        """PID 闭环制动：跟踪制动曲线，接近站台时切换蠕行。

        制动 PID 的误差约定：
            setpoint = 实际速度, pv = 目标速度
            → error = actual - target
            → 超速时 error > 0 → PID 输出正 → brake_level ↑
            → 偏慢时 error < 0 → PID 输出负 → 钳位为 0 → coast/微牵引
        """
        remaining = max(target.chainage - train.position, 0.0)
        pid = self._brake_pid
        pp = pid._p

        # 距站台 ≤ deadband_d 且低速 → 蠕行模式（避免 Zeno 振荡）
        if remaining <= pp.deadband_d and train.speed < 3.0:
            return self._creep_brake(remaining)

        # PID 跟踪制动曲线（swap setpoint/pv 使超速→正输出→制动）
        v_target_kmh = PIDController.braking_curve_speed(remaining, pp.comfort_decel)
        brake = pid.compute(train.speed, v_target_kmh, dt)
        return ControlCommands(brake_level=brake)

    def _creep_brake(self, remaining_m: float) -> ControlCommands:
        """蠕行模式：制动力与剩余距离成正比，距离越小越柔和。"""
        pp = self._brake_pid._p
        brake = min(remaining_m * pp.creep_gain, 0.5)
        brake = max(brake, 0.02)  # 至少保留微弱制动，确保最终停下
        return ControlCommands(brake_level=brake)

    # ── 制动触发距离（惰行→制动切换判定，保留原公式）────────────────

    def _brake_trigger_distance(self, train: TrainState) -> float:
        """制动触发距离，基于 PID 实际跟踪的 comfort_decel 计算。

        与 _braking_step 中的 ATO 制动曲线保持一致：
        v_target = sqrt(2 * comfort_decel * d)，因此制动距离
        d = v² / (2 * comfort_decel)，乘以安全系数留出余量。
        """
        v_ms = max(train.speed, 0.0) / 3.6
        decel = self._brake_pid._p.comfort_decel
        if decel <= 0:
            return 0.0
        safety = self._brake_pid._p.brake_safety_factor
        return (v_ms * v_ms) / (2 * decel) * safety

    # ── 惰行补偿（不变）───────────────────────────────────────────────

    def _coasting_compensation(
        self, train: TrainState, track_params
    ) -> float:
        """计算惰行补偿牵引级位。

        惰行时施加少量牵引力，抵消滚动摩擦 + 坡度阻力。
        - 平坡：仅补偿滚动摩擦
        - 上坡（正梯度）：补偿滚动摩擦 + 上坡额外阻力
        - 下坡（负梯度）：下坡助力自动减少补偿，坡度足够大时级位为 0
        空气阻力与弯道阻力忽略不计。

        返回牵引级位 [0, 1]。
        """
        v_ms = abs(train.speed) / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params

        rolling = (p.davis_a + p.davis_b * v_ms) * mass * GRAVITY

        # 坡度阻力：上坡为正（需补偿），下坡为负（减少补偿）
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
