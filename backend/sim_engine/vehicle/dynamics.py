"""车辆动力学解算引擎（VHC-01 / 07 / 08 / 10）。

``VehicleSystem.step`` 为单步解算入口：接收当前状态、控车指令与线路参数，
返回更新后的状态与受力分解。积分采用显式（半隐式）欧拉法：先由合力更新
速度，再用新速度更新位置。
"""

from __future__ import annotations

from . import resistance as R
from .models import (
    ControlCommands,
    ForceBreakdown,
    StepResult,
    TrackPointParams,
    TrainState,
    VehicleParams,
)
from .traction import traction_force

KMH_TO_MS = 1.0 / 3.6
MS_TO_KMH = 3.6

MODE_TRACTION = "traction"
MODE_COASTING = "coasting"
MODE_BRAKING = "braking"
MODE_DWELL = "dwell"


def effective_speed_limit_kmh(track: TrackPointParams, params: VehicleParams) -> float:
    """VHC-07：有效限速 = min(区段限速, 车辆构造速度)。"""
    track_limit = max(track.speed_limit, 0.0)
    vehicle_limit = max(params.max_speed, 0.0)
    if vehicle_limit <= 0:
        return track_limit
    return min(track_limit, vehicle_limit)


class VehicleSystem:
    """单质点列车动力学模型。"""

    def __init__(self, params: VehicleParams):
        self.params = params

    @classmethod
    def from_config(cls, path: str) -> "VehicleSystem":
        """从 YAML 配置文件构造车辆系统。"""
        from .config import load_vehicle_params

        return cls(load_vehicle_params(path))

    def create_initial_state(
        self, position: float = 0.0, passenger_load: float = 0.0,
        direction: str = "down",
    ) -> TrainState:
        """构造一个初始（静止）列车状态，质量按载客率折算。"""
        return TrainState(
            position=position,
            speed=0.0,
            acceleration=0.0,
            mode=MODE_COASTING,
            mass=self.params.mass_at_load(passenger_load),
            passenger_load=passenger_load,
            direction=direction,
        )

    def step(
        self,
        state: TrainState,
        cmd: ControlCommands,
        track: TrackPointParams,
        dt: float,
        max_jerk: float = 0.75,
    ) -> StepResult:
        """推进一个仿真步长 ``dt`` 秒，返回新状态与受力分解。"""
        params = self.params
        mass = state.mass if state.mass > 0 else params.mass_at_load(state.passenger_load)

        # --- 受力计算 ---
        f_traction = traction_force(
            params.traction_curve,
            params.max_traction_force,
            state.speed,
            cmd.traction_level,
        )
        if cmd.emergency_brake:
            f_brake = params.max_brake_force
        else:
            f_brake = params.max_brake_force * min(max(cmd.brake_level, 0.0), 1.0)

        r_davis = R.davis_resistance(params, mass, state.speed)
        r_gradient = R.gradient_resistance(mass, track.gradient)
        r_curve = R.curve_resistance(mass, track.curvature, params.curve_resist_coeff)
        r_tunnel = R.tunnel_resistance(r_davis, track.is_tunnel, params.tunnel_resist_factor)

        # 阻力仅在列车运动（或有牵引力试图启动）时阻碍前进方向。静止且无牵引
        # 时，不让阻力把速度推成负值。
        v_ms = state.speed * KMH_TO_MS
        resistance_total = r_davis + r_curve + r_tunnel + r_gradient
        net = f_traction - f_brake - resistance_total

        # --- 显式欧拉积分 ---
        prev_accel = state.acceleration
        accel = net / mass
        new_v_ms = v_ms + accel * dt

        # VHC-08：近静止且合力向后时保持零速；否则制动过零则钳位
        creep_stop_kmh = 0.05
        if state.speed <= creep_stop_kmh and net <= 0:
            new_v_ms = 0.0
            if prev_accel < -1e-6:
                # 停车后渐近归零加速度，避免速度钳位引发冲击率尖峰
                accel = min(0.0, prev_accel + max_jerk * dt)
            else:
                accel = 0.0
        elif new_v_ms < 0:
            new_v_ms = 0.0
            accel = (new_v_ms - v_ms) / dt if dt > 0 else 0.0

        # VHC-07：限速约束（区段限速与车辆最大速度取较低者）
        speed_limit_kmh = effective_speed_limit_kmh(track, params)
        speed_limit_ms = speed_limit_kmh * KMH_TO_MS
        if new_v_ms > speed_limit_ms:
            new_v_ms = speed_limit_ms
            accel = (new_v_ms - v_ms) / dt if dt > 0 else 0.0

        # 上行方向公里标递减，下行方向公里标递增
        dir_sign = -1.0 if state.direction == "up" else 1.0
        new_position = state.position + dir_sign * new_v_ms * dt

        jerk = (accel - prev_accel) / dt if dt > 0 else 0.0

        # ── VHC-09: 能耗累计 ──
        traction_energy = state.traction_energy
        regen_energy = state.regen_energy

        # 使用积分步起点速度（与受力计算一致）
        if f_traction > 0 and v_ms > 0:
            traction_energy += f_traction * v_ms * dt
        if f_brake > 0 and v_ms > 0:
            regen_energy += (
                f_brake * v_ms * self.params.regeneration_efficiency * dt
            )

        new_state = TrainState(
            position=new_position,
            speed=new_v_ms * MS_TO_KMH,
            acceleration=accel,
            jerk=jerk,
            mode=self._determine_mode(cmd),
            mass=mass,
            passenger_load=state.passenger_load,
            traction_energy=traction_energy,
            regen_energy=regen_energy,
            direction=state.direction,
        )

        forces = ForceBreakdown(
            traction=f_traction,
            brake=f_brake,
            davis=r_davis,
            gradient=r_gradient,
            curve=r_curve,
            tunnel=r_tunnel,
            resistance_total=resistance_total,
            net=net,
        )
        return StepResult(state=new_state, forces=forces)

    @staticmethod
    def _determine_mode(cmd: ControlCommands) -> str:
        """由控车指令派生工况。信号 phase 提示优先于牵引/制动判断。"""
        if cmd.phase == "dwell":
            return MODE_DWELL
        if cmd.phase == "coasting":
            return MODE_COASTING
        if cmd.emergency_brake or cmd.brake_level > 0:
            return MODE_BRAKING
        if cmd.traction_level > 0:
            return MODE_TRACTION
        return MODE_COASTING
