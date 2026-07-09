"""三段式运行模式控制器。

牵引 → 惰行 → 制动，按位置与速度切换；到站停车后等待站停时间再发车。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sim_engine.core.config import SimulationParams
from sim_engine.track.models import Station
from sim_engine.track.path_service import TrackPathService
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


class ThreeStageController:
    """为单列车生成控车指令。"""

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

    @property
    def signal_state(self) -> TrainSignalState:
        return self._state

    def reset(self) -> None:
        self._state = TrainSignalState()

    def compute_commands(self, train: TrainState, dt: float) -> ControlCommands:
        st = self._state
        tol = self.sim_params.station_stop_tolerance

        if st.phase == Phase.DWELL:
            st.dwell_remaining = max(0.0, st.dwell_remaining - dt)
            if st.dwell_remaining <= 0:
                st.phase = Phase.TRACTION
            return ControlCommands()

        target = self.track.next_station_ahead(train.position)
        if target is None:
            if train.speed > 0.1:
                return ControlCommands(brake_level=1.0)
            return ControlCommands()

        track_params = self.track.query_at(train.position)
        v_target = self.sim_params.target_speed_ratio * track_params.speed_limit
        brake_dist = self._brake_trigger_distance(train)
        dist_to_station = target.chainage - train.position

        # 到站停稳 → 站停
        if train.speed < 0.1 and abs(dist_to_station) <= tol:
            st.phase = Phase.DWELL
            st.dwell_remaining = target.dwell_time
            return ControlCommands()

        # 中途停住（制动不足等）→ 重新牵引
        if train.speed < 0.1 and dist_to_station > tol:
            st.phase = Phase.TRACTION

        if st.phase == Phase.TRACTION:
            if train.speed >= v_target - 0.5:
                st.phase = Phase.COASTING
                return ControlCommands()
            return ControlCommands(traction_level=1.0)

        if st.phase == Phase.COASTING:
            if train.position + brake_dist >= target.chainage - tol:
                st.phase = Phase.BRAKING
                return ControlCommands(brake_level=1.0)
            comp = self._coasting_compensation(train, track_params)
            return ControlCommands(traction_level=comp)

        # BRAKING
        return ControlCommands(brake_level=1.0)

    def _brake_trigger_distance(self, train: TrainState) -> float:
        v_ms = max(train.speed, 0.0) / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        max_decel = self.vehicle_params.max_brake_force / mass
        if max_decel <= 0:
            return 0.0
        return (v_ms * v_ms) / (2 * max_decel) * 1.1

    def _coasting_compensation(
        self, train: TrainState, track_params
    ) -> float:
        """计算惰行补偿牵引级位。

        惰行时施加少量牵引力，抵消滚动摩擦与上坡坡度阻力，
        避免速度过快衰减。空气阻力与弯道阻力忽略不计。

        返回牵引级位 [0, 1]。
        """
        v_ms = abs(train.speed) / 3.6
        mass = train.mass if train.mass > 0 else self.vehicle_params.empty_mass
        p = self.vehicle_params

        # 滚动摩擦阻力 (Davis A + B·v 部分，不含空气项)
        rolling = (p.davis_a + p.davis_b * v_ms) * mass * GRAVITY

        # 坡度阻力：仅补偿上坡（正值），下坡不补偿
        grad = max(track_params.gradient, 0.0)
        gradient_force = mass * GRAVITY * (grad / 1000.0)

        f_target = rolling + gradient_force
        if f_target <= 0:
            return 0.0

        # 当前速度下最大可用牵引力
        percent = interpolate_force_percent(p.traction_curve, train.speed)
        max_available = p.max_traction_force * percent
        if max_available <= 0:
            return 0.0

        level = f_target / max_available
        return min(max(level, 0.0), 1.0)
