"""仿真生命周期管理：封装 Orchestrator + 后台异步仿真循环。
供 REST API 路由和 WebSocket 端点调用，是 Web 服务层与仿真引擎之间的桥梁。"""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from sim_engine.core.clock import RunState
from sim_engine.core.config import SimulationParams, load_simulation_params
from sim_engine.data.recorder import DataRecorder
from sim_engine.orchestrator import Orchestrator, CONFIG_DIR
from sim_engine.track.config import load_track
from sim_engine.track.models import Track
from sim_engine.track.path_service import TrackPathService
from sim_engine.vehicle.config import load_vehicle_params
from sim_engine.vehicle.models import TractionCurvePoint

from sim_engine.ws.manager import WebSocketConnectionManager


class SimulationManager:
    """管理 Orchestrator 生命周期 + 后台异步仿真循环。"""

    def __init__(self, ws_manager: WebSocketConnectionManager) -> None:
        self.ws_manager = ws_manager
        self.orchestrator = Orchestrator.from_config_dir()
        self._loop_task: asyncio.Task | None = None
        # 追踪最近一次仿真的聚合数据（供方案保存 API 使用）
        self._last_snapshot: dict | None = None
        self._last_summary: dict | None = None
        self._min_voltage: float = 1500.0
        self._peak_power: float = 0.0  # kW

    # ==================== 仿真控制 ====================

    def _reset_tracking(self) -> None:
        """每次新仿真前重置聚合追踪器。"""
        self._last_snapshot = None
        self._last_summary = None
        self._min_voltage = 1500.0
        self._peak_power = 0.0

    def _update_tracking(self, snapshot: dict) -> None:
        """从单步 snapshot 更新 min_voltage / peak_power / last_snapshot。"""
        self._last_snapshot = snapshot
        power_data = snapshot.get("data", {}).get("power", {})
        # 网压最低值
        vp = power_data.get("voltageProfile", [])
        for item in vp:
            v = item.get("voltage", 1500.0)
            if v < self._min_voltage:
                self._min_voltage = v
        # 变电所峰值功率 (W → kW)
        subs = power_data.get("substations", [])
        for s in subs:
            p_kw = s.get("outputPower", 0) / 1000.0
            if p_kw > self._peak_power:
                self._peak_power = p_kw

    def start(self, passenger_load: float = 0.6) -> dict:
        if self.orchestrator.run_state not in (RunState.IDLE, RunState.STOPPED):
            return {"code": 40002, "message": "操作冲突", "detail": "仿真已在运行中"}
        self._reset_tracking()
        self.orchestrator.start(passenger_load=passenger_load)
        self.start_loop()
        return {
            "runId": 1,
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    async def pause(self) -> dict:
        if self.orchestrator.run_state != RunState.RUNNING:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真未在运行中"}
        self.orchestrator.pause()
        # 广播权威状态，覆盖 _run_loop 可能已发出的陈旧 running 消息
        await self.ws_manager.broadcast({
            "type": "simulation_status",
            "data": {
                "runState": "paused",
                "simulationTime": self.orchestrator.clock.elapsed,
                "reason": "user_paused",
            },
        })
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def resume(self) -> dict:
        if self.orchestrator.run_state != RunState.PAUSED:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真未在暂停状态"}
        self.orchestrator.resume()
        self.start_loop()
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    async def stop(self) -> dict:
        """停止仿真：结束本轮运行、保留摘要，并将引擎重置到初始状态。

        与 pause 不同——pause 冻结当前进度；stop 结束后时钟/位置回到起点，
        便于用户查看运行摘要后再次从 A 站启动。
        """
        self.stop_loop()
        orch = self.orchestrator
        summary = orch.recorder.summary()
        self._last_summary = summary
        ended_time = orch.clock.elapsed
        passenger_load = orch.train_state.passenger_load if orch.train_state else 0.6

        orch.reset(passenger_load=passenger_load)
        orch.run_state = RunState.STOPPED

        await self.ws_manager.broadcast({
            "type": "simulation_complete",
            "data": {
                "runId": 1,
                "simulationTime": ended_time,
                "summary": summary,
            },
        })
        await self.ws_manager.broadcast({
            "type": "simulation_status",
            "data": {
                "runState": "stopped",
                "simulationTime": 0.0,
                "reason": "user_stopped",
            },
        })
        return {
            "runState": orch.run_state.value,
            "runId": 1,
            "summary": summary,
        }

    def reset(self) -> dict:
        self.stop_loop()
        self.orchestrator = Orchestrator.from_config_dir()
        self.orchestrator.reset()
        self._reset_tracking()
        return {
            "runState": self.orchestrator.run_state.value,
            "simulationTime": self.orchestrator.clock.elapsed,
        }

    def step(self) -> dict | None:
        snapshot = self.orchestrator.step_once()
        if snapshot:
            self._update_tracking(snapshot)
        return snapshot

    def set_speed(self, multiplier: float) -> dict:
        self.orchestrator.clock.speed_multiplier = multiplier
        self.orchestrator.sim_params.speed_multiplier = multiplier
        return {"speedMultiplier": multiplier}

    def set_emergency_brake(self, active: bool) -> dict:
        self.orchestrator.set_emergency_brake(active)
        return {"emergencyBrake": active}

    # ==================== 状态查询 ====================

    @staticmethod
    def _is_continuous_dispatch(orch: Orchestrator) -> bool:
        st = orch._service_timetable
        return st is not None and st.dispatch.mode == "continuous"

    def get_status(self) -> dict:
        orch = self.orchestrator
        if self._is_continuous_dispatch(orch):
            train_count = len(orch.trains)
        else:
            train_count = orch.sim_params.total_train_count()
        return {
            "runState": orch.run_state.value,
            "simulationTime": orch.clock.elapsed,
            "totalTime": orch.sim_params.total_time,
            "speedMultiplier": orch.clock.speed_multiplier,
            "trainCount": train_count,
        }

    def get_last_snapshot(self) -> dict | None:
        """返回最近一次仿真的最终 snapshot（供方案保存 API 调用）。"""
        return self._last_snapshot

    def get_run_stats(self) -> dict:
        """返回本次仿真运行的聚合统计数据。

        返回值包含 min_voltage / peak_power 等跨步追踪值，
        供方案保存 API 拼装 result 字段。
        """
        return {
            "minVoltage": self._min_voltage,
            "peakPower": self._peak_power,
        }

    # ==================== 配置读取 ====================

    def _load_yaml(self, filename: str) -> dict:
        path = CONFIG_DIR / filename
        with path.open("r", encoding="utf-8") as fp:
            return yaml.safe_load(fp) or {}

    def _to_camel(self, d: dict) -> dict:
        """将 snake_case 字典键转换为 camelCase。"""
        result = {}
        for k, v in d.items():
            parts = k.split("_")
            camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
            if isinstance(v, dict):
                v = self._to_camel(v)
            elif isinstance(v, list):
                v = [self._to_camel(item) if isinstance(item, dict) else item for item in v]
            result[camel] = v
        return result

    def get_config(self) -> dict:
        raw_vehicle = self._load_yaml("vehicle.yaml")
        raw_track = self._load_yaml("track.yaml")
        raw_sim = self._load_yaml("simulation.yaml")

        vehicle = self._to_camel(raw_vehicle.get("vehicle", raw_vehicle))
        track = self._to_camel(raw_track.get("line", raw_track))
        sim = self._to_camel(raw_sim.get("simulation", raw_sim))

        # 补充 API 文档需要的字段
        if "totalLength" not in track:
            segments = track.get("segments", [])
            track["totalLength"] = max((s.get("endChainage", 0) for s in segments), default=0)
        if "direction" not in track:
            track["direction"] = "up"

        return {"line": track, "vehicle": vehicle, "simulation": sim}

    def get_line_config(self) -> dict:
        return self.get_config()["line"]

    def get_vehicle_config(self) -> dict:
        return self.get_config()["vehicle"]

    # ==================== 配置更新 ====================

    def update_config(self, updates: dict) -> dict:
        if self.orchestrator.run_state == RunState.RUNNING:
            return {"code": 40002, "message": "操作冲突", "detail": "仿真运行中无法修改配置"}
        # 更新 simulation 参数
        sim_updates = updates.get("simulation", {})
        updated_keys: list[str] = []
        if sim_updates:
            sim_path = CONFIG_DIR / "simulation.yaml"
            with sim_path.open("r", encoding="utf-8") as fp:
                sim_data = yaml.safe_load(fp) or {}
            sim_section = sim_data.setdefault("simulation", sim_data)
            field_map = {
                "timeStep": "time_step",
                "totalTime": "total_time",
                "speedMultiplier": "speed_multiplier",
                "targetSpeedRatio": "target_speed_ratio",
                "stationStopTolerance": "station_stop_tolerance",
                "trainCount": "train_count",
                "bidirectional": "bidirectional",
                "departureInterval": "departure_interval",
            }
            for camel_key, snake_key in field_map.items():
                if camel_key in sim_updates:
                    sim_section[snake_key] = sim_updates[camel_key]
                    updated_keys.append(f"simulation.{snake_key}")
            if updated_keys:
                with sim_path.open("w", encoding="utf-8") as fp:
                    yaml.dump(sim_data, fp, allow_unicode=True, default_flow_style=False)
                # 重新加载编排器
                self.orchestrator = Orchestrator.from_config_dir()
        return {"updated": updated_keys if sim_updates else [], "config": self.get_config()}

    # ==================== 运行时参数 ====================

    @staticmethod
    def _traction_curve_to_api(curve: list[TractionCurvePoint]) -> list[dict]:
        return [{"speed": p.speed, "forcePercent": p.force_percent} for p in curve]

    @staticmethod
    def _traction_curve_from_api(raw: list[dict]) -> list[TractionCurvePoint]:
        return [
            TractionCurvePoint(
                speed=float(point["speed"]),
                force_percent=float(point.get("forcePercent", point.get("force_percent", 0.0))),
            )
            for point in raw
        ]

    def _current_chainage(self) -> float:
        state = self.orchestrator.train_state
        return state.position if state is not None else 0.0

    def get_params(self) -> dict:
        orch = self.orchestrator
        vp = orch.vehicle.params
        chainage = self._current_chainage()
        seg = orch.track.segment_at(chainage)
        tp = orch.track.query_at(chainage)
        return {
            "vehicle": {
                "emptyMass": vp.empty_mass,
                "passengerCapacity": vp.passenger_capacity,
                "maxSpeed": vp.max_speed,
                "maxTractionForce": vp.max_traction_force,
                "maxBrakeForce": vp.max_brake_force,
                "davisA": vp.davis_a,
                "davisB": vp.davis_b,
                "davisCFrontArea": vp.davis_c_front_area,
                "davisCDragCoeff": vp.davis_c_drag_coeff,
                "curveResistCoeff": vp.curve_resist_coeff,
                "tunnelResistFactor": vp.tunnel_resist_factor,
                "tractionCurve": self._traction_curve_to_api(vp.traction_curve),
            },
            "track": {
                "segmentId": seg.id if seg else None,
                "gradient": tp.gradient,
                "curvature": tp.curvature,
                "speedLimit": tp.speed_limit,
            },
            "power": {
                "pantographVoltage": 1500,
                "substationCapacity": 5000,
            },
            "signal": {
                "dwellTime": 30,
                "departureInterval": orch.sim_params.departure_interval,
                "targetSpeedRatio": orch.sim_params.target_speed_ratio,
            },
        }

    def update_params(self, updates: dict) -> dict:
        """更新运行时参数（部分更新，仅内存）。

        迭代一：空闲/暂停时可改车辆、当前区段线路、目标速度比；
        运行中拒绝修改（对齐验收场景 4）。
        """
        orch = self.orchestrator
        if orch.run_state == RunState.RUNNING:
            return {
                "code": 40002,
                "message": "操作冲突",
                "detail": "仿真运行中无法修改参数",
            }

        updated: list[str] = []

        vehicle_updates = updates.get("vehicle", {})
        if vehicle_updates:
            vp = orch.vehicle.params
            field_map = {
                "emptyMass": "empty_mass",
                "passengerCapacity": "passenger_capacity",
                "maxSpeed": "max_speed",
                "maxTractionForce": "max_traction_force",
                "maxBrakeForce": "max_brake_force",
                "davisA": "davis_a",
                "davisB": "davis_b",
                "davisCFrontArea": "davis_c_front_area",
                "davisCDragCoeff": "davis_c_drag_coeff",
                "curveResistCoeff": "curve_resist_coeff",
                "tunnelResistFactor": "tunnel_resist_factor",
            }
            for camel_key, snake_key in field_map.items():
                if camel_key in vehicle_updates:
                    setattr(vp, snake_key, vehicle_updates[camel_key])
                    updated.append(f"vehicle.{camel_key}")
            if "tractionCurve" in vehicle_updates:
                vp.traction_curve = self._traction_curve_from_api(vehicle_updates["tractionCurve"])
                updated.append("vehicle.tractionCurve")

        track_updates = updates.get("track", {})
        if track_updates:
            segment_id = track_updates.get("segmentId")
            if not segment_id:
                seg = orch.track.segment_at(self._current_chainage())
                segment_id = seg.id if seg else None
            if segment_id:
                seg = orch.track.update_segment(
                    segment_id,
                    gradient=track_updates.get("gradient"),
                    curvature=track_updates.get("curvature"),
                    speed_limit=track_updates.get("speedLimit"),
                )
                if seg is not None:
                    for key in ("gradient", "curvature", "speedLimit"):
                        if key in track_updates:
                            updated.append(f"track.{key}")

        signal_updates = updates.get("signal", {})
        if "targetSpeedRatio" in signal_updates:
            orch.sim_params.target_speed_ratio = signal_updates["targetSpeedRatio"]
            updated.append("signal.targetSpeedRatio")

        return {"updated": updated, "params": self.get_params()}

    # ==================== CSV 导出 ====================

    def get_csv_export(self) -> str:
        """从 recorder 缓冲区生成 CSV 文本。"""
        import csv
        import io

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["time", "position", "speed", "mode", "acceleration", "jerk",
             "traction_force", "brake_force", "total_resistance"]
        )
        for r in self.orchestrator.recorder.buffer:
            writer.writerow(
                [r.time, r.position, r.speed, r.mode, r.acceleration, r.jerk,
                 r.traction_force, r.brake_force, r.total_resistance]
            )
        return buf.getvalue()

    # ==================== WebSocket 初始化消息 ====================

    def build_init_message(self) -> dict:
        config = self.get_config()
        return {
            "type": "init_state",
            "config": config,
            "state": {
                "runState": self.orchestrator.run_state.value,
                "simulationTime": self.orchestrator.clock.elapsed,
            },
        }

    # ==================== 后台循环 ====================

    @staticmethod
    def _all_trains_finished(orch: Orchestrator) -> bool:
        """全部列车已 spawn 且均到终点停稳（按各车 direction 判断）。"""
        active = [t for t in orch.trains if t.active]
        if len(active) < orch.sim_params.total_train_count():
            return False
        total = orch.track.track.total_length
        for run in active:
            st = run.state
            if st.speed >= 0.1:
                return False
            if st.direction == "up":
                if st.position > 1.0:
                    return False
            elif st.position < total - 1.0:
                return False
        return True

    async def _run_loop(self) -> None:
        """后台仿真主循环：每步 step_once → broadcast → sleep(dt/multiplier)。"""
        orch = self.orchestrator
        while orch.run_state == RunState.RUNNING:
            snapshot = orch.step_once()
            if snapshot:
                self._update_tracking(snapshot)
                # 广播快照
                await self.ws_manager.broadcast(snapshot)
                # 广播状态变更
                await self.ws_manager.broadcast({
                    "type": "simulation_status",
                    "data": {
                        "runState": "running",
                        "simulationTime": orch.clock.elapsed,
                        "reason": "running",
                    },
                })
            # 终点停稳判断
            line_end = (
                not self._is_continuous_dispatch(orch)
                and orch.train_state is not None
                and orch.train_state.speed < 0.1
                and (
                    (orch.train_state.direction == "up" and orch.train_state.position <= 1.0)
                    or (orch.train_state.direction != "up" and orch.train_state.position >= orch.track.track.total_length - 1.0)
                )
            )
            if orch.clock.elapsed >= orch.sim_params.total_time:
                should_complete = True
            elif self._is_continuous_dispatch(orch):
                should_complete = False
            else:
                should_complete = self._all_trains_finished(orch) or line_end
            if should_complete:
                # 先记录结束时刻的摘要，保存最终 snapshot/summary
                self._last_summary = orch.recorder.summary()
                if snapshot:
                    self._last_snapshot = snapshot
                ended_time = orch.clock.elapsed
                passenger_load = orch.train_state.passenger_load if orch.train_state else 0.6

                # 自动复位到初始状态（与手动 stop 行为一致）
                orch.reset(passenger_load=passenger_load)
                orch.run_state = RunState.STOPPED

                await self.ws_manager.broadcast({
                    "type": "simulation_complete",
                    "data": {
                        "runId": 1,
                        "simulationTime": ended_time,
                        "summary": self._last_summary,
                    },
                })
                await self.ws_manager.broadcast({
                    "type": "simulation_status",
                    "data": {
                        "runState": "stopped",
                        "simulationTime": 0.0,
                        "reason": "completed",
                    },
                })
                break
            # 速度倍率等待
            dt = orch.clock.time_step
            mult = orch.sim_params.speed_multiplier
            await asyncio.sleep(dt / mult)
        self._loop_task = None

    def start_loop(self) -> None:
        """启动后台循环 asyncio.Task。"""
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._run_loop())

    def stop_loop(self) -> None:
        """取消后台循环。"""
        if self._loop_task is not None and not self._loop_task.done():
            self._loop_task.cancel()
            self._loop_task = None