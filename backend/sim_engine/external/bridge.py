"""外部系统桥接层 — 统一管理所有外设通信。

协调 PLC、网络屏、信号屏、总控节点 UDP 的启动/停止/数据流，
将外设输入注入仿真引擎，并将引擎状态输出到外设。

文档: 外部系统对接方案
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from .plc_bridge import PlcBridge
from .hmi_bridge import HmiBridge
from .mmi_bridge import MmiBridge
from .udp_bridge import UdpBridge
from .protocol import (
    USE_REAL_HARDWARE,
    PLC_DEVICE_IP, PLC_PORT,
    NETWORK_SCREEN_DEVICE_IP, NETWORK_SCREEN_PORT,
    SIGNAL_SCREEN_DEVICE_IP, SIGNAL_SCREEN_PORT,
    LEVEL_POS, RUN_DIR, RUN_MODE_MANUAL_ATO, DOOR_MODE_MM_AM_AA,
    SIGNAL_MODE_MAP,
)

logger = logging.getLogger(__name__)


class ExternalBridge:
    """外部系统桥接层。

    统一管理四个外设通道:
    - PLC: 接收手柄/按钮输入，下发指示灯
    - 网络屏 (HMI): 发送车辆状态显示
    - 信号屏 (MMI): 发送信号/速度信息
    - 总控 UDP: 高频数据交换

    用法:
        bridge = ExternalBridge()
        bridge.start_all()
        bridge.update_from_engine(snapshot, params)  # 每仿真步调用
        plc_input = bridge.get_plc_input()

    支持两种模式:
    - 真实硬件模式: 连接真实外设 (USE_REAL_HARDWARE = True)
    - 模拟模式: 不连接外设，仅提供空数据 (默认)
    """

    def __init__(
        self,
        plc_host: str = PLC_DEVICE_IP,
        plc_port: int = PLC_PORT,
        hmi_host: str = NETWORK_SCREEN_DEVICE_IP,
        hmi_port: int = NETWORK_SCREEN_PORT,
        mmi_host: str = SIGNAL_SCREEN_DEVICE_IP,
        mmi_port: int = SIGNAL_SCREEN_PORT,
        use_real_hardware: bool = USE_REAL_HARDWARE,
    ):
        self.use_real_hardware = use_real_hardware
        self.last_engine_update_time: Optional[float] = None

        # 创建各桥接器
        self.plc = PlcBridge(host=plc_host, port=plc_port)
        self.hmi = HmiBridge(host=hmi_host, port=hmi_port)
        self.mmi = MmiBridge(host=mmi_host, port=mmi_port)
        self.udp = UdpBridge()

        # 上次向网络屏/信号屏发送的数据时间
        self._last_hmi_send = 0.0
        self._last_mmi_send = 0.0
        # 网络屏和信号屏的发送间隔 (按需发送，但限制最低间隔)
        self.hmi_send_interval = 0.1   # 100ms
        self.mmi_send_interval = 0.1   # 100ms

        # 模拟模式下的 PLC 模拟输入
        self._sim_plc_input = {
            "connected": False,
            "eb_button": False,
            "key_switch": False,
            "ato_start": False,
            "ato_active": False,
            "dir_handle": 0,
            "main_handle": 0,
            "traction_level_pct": 0.0,
            "brake_level_pct": 0.0,
            "alert_flag": False,
            "open_left_door": False,
            "open_right_door": False,
            "close_left_door": False,
            "close_right_door": False,
        }

        # 运行状态
        self.running = False

        # 简易日志：上次打日志的时间
        self._last_log_time = 0.0
        self.log_interval = 5.0  # 每 5s wall-clock 打印一行状态

    # ── 简易日志 ────────────────────────────────────────

    def log_status_summary(self, snapshot: dict) -> None:
        """每 5s wall-clock 打印一条简易状态日志（连接状态 + 运行数据）。"""
        now = time.time()
        if now - self._last_log_time < self.log_interval:
            return
        self._last_log_time = now

        hw = "硬件" if self.use_real_hardware else "模拟"
        parts = [f"[外部 {hw}]"]

        # 连接状态
        if self.plc:
            parts.append(f"PLC {'✓' if self.plc.connected else '✗'}({self.plc.send_count}/{self.plc.recv_count})")
        if self.hmi:
            parts.append(f"网络屏 {'✓' if self.hmi.connected else '✗'}({self.hmi.send_count})")
        if self.mmi:
            parts.append(f"信号屏 {'✓' if self.mmi.connected else '✗'}({self.mmi.send_count})")
        if self.udp:
            parts.append(f"UDP {'✓' if self.udp.is_connected() else '✗'}(↑{self.udp.send_count} ↓{self.udp.recv_count})")

        # 运行数据（首列车）
        train = self._extract_lead_train(snapshot)
        if train:
            state = train.get("state", {})
            speed_kmh = state.get("speed", 0) * 3.6
            pos = state.get("position", 0)
            mode = state.get("mode", "?")
            parts.append(f" 车速={speed_kmh:.0f}km/h  位置={pos:.0f}m  模式={mode}")

        print("  ".join(parts))

    def log_final_summary(self) -> None:
        """仿真结束时打印最终汇总。"""
        print("-" * 50)
        print("  外部系统通信汇总")
        print("-" * 50)
        if self.plc:
            print(f"  PLC:      连接={self.plc.connected}, 发送={self.plc.send_count}, 接收={self.plc.recv_count}")
        if self.hmi:
            print(f"  网络屏:   连接={self.hmi.connected}, 发送={self.hmi.send_count}")
        if self.mmi:
            print(f"  信号屏:   连接={self.mmi.connected}, 发送={self.mmi.send_count}")
        if self.udp:
            print(f"  UDP:      运行中={self.udp.is_connected()}, 发送={self.udp.send_count}, 接收={self.udp.recv_count}")
        print("-" * 50)

    # ── 启动/停止 ──────────────────────────────────────

    def start_all(self) -> dict:
        """启动所有外设连接。

        Returns:
            dict: 各通道的连接结果 {"plc": bool, "hmi": bool, "mmi": bool, "udp": bool}
        """
        results = {"plc": False, "hmi": False, "mmi": False, "udp": False}

        if not self.use_real_hardware:
            logger.info("外部桥接: 模拟模式 (不连接真实外设)")
            self.running = True
            return results

        # 连接 PLC
        if self.plc.connect():
            self.plc.start()
            results["plc"] = True

        # 连接网络屏
        if self.hmi.connect():
            results["hmi"] = True

        # 连接信号屏
        if self.mmi.connect():
            results["mmi"] = True

        # 启动 UDP
        if self.udp.start():
            results["udp"] = True

        self.running = True
        logger.info(f"外部桥接启动结果: {results}")
        return results

    def stop_all(self):
        """停止所有外设连接。"""
        self.running = False
        self.plc.stop()
        self.hmi.disconnect()
        self.mmi.disconnect()
        self.udp.stop()
        logger.info("外部桥接已全部停止")

    # ── 数据更新 (每仿真步调用) ────────────────────────

    def update_from_engine(self, snapshot: dict, sim_params) -> dict:
        """从仿真快照更新所有外设输出。

        此方法应在每个仿真步后调用，从 snapshot 提取数据并：
        1. 更新 PLC 速度回显
        2. 更新网络屏显示
        3. 更新信号屏显示
        4. 更新 UDP 总控数据

        Args:
            snapshot: orchestrator 的 build_simulation_snapshot() 输出。
            sim_params: SimulationParams 实例。

        Returns:
            dict: 输出结果摘要。
        """
        self.last_engine_update_time = time.time()
        result = {"plc_speed": False, "hmi": False, "mmi": False, "udp": False}

        if not self.running:
            return result

        # 提取首列车数据
        train = self._extract_lead_train(snapshot)
        if not train:
            return result

        current_time = time.time()

        # 1. 更新 PLC 速度回显
        speed_kmh = train.get("speed_kmh", 0)
        self.plc.set_vehicle_speed(int(speed_kmh))
        result["plc_speed"] = True

        # 2. 更新网络屏 (限频)
        if current_time - self._last_hmi_send >= self.hmi_send_interval:
            hmi_state = self._build_hmi_state(snapshot, train, sim_params)
            if self.hmi.send_from_state(hmi_state):
                self._last_hmi_send = current_time
                result["hmi"] = True

        # 3. 更新信号屏 (限频)
        if current_time - self._last_mmi_send >= self.mmi_send_interval:
            mmi_state = self._build_mmi_state(snapshot, train, sim_params)
            if self.mmi.send_from_state(mmi_state):
                self._last_mmi_send = current_time
                result["mmi"] = True

        # 4. 更新 UDP 总控数据
        trains_udp = self._build_udp_trains(snapshot)
        self.udp.update_trains(trains_udp)
        result["udp"] = True

        # 5. 每 5s 打印一条简易状态日志

        return result

    # ── PLC 输入获取 ───────────────────────────────────

    def get_plc_input(self) -> dict:
        """获取当前 PLC 手柄/按钮输入。

        真实硬件模式: 返回最新 PLC 状态解析结果。
        模拟模式: 返回空数据 (可通过 set_sim_plc_input 设置模拟值)。

        Returns:
            dict: 包含方向手柄、主手柄、极位、按钮等关键字段。
        """
        if self.use_real_hardware:
            return self.plc.get_plc_input_summary()
        return self._sim_plc_input

    def set_sim_plc_input(self, **kwargs):
        """设置模拟模式下的 PLC 输入值。

        Args:
            **kwargs: 要设置的字段，如 eb_button=True, dir_handle=1 等。
        """
        self._sim_plc_input.update(kwargs)

    # ── 状态查询 ───────────────────────────────────────

    def get_status_str(self) -> str:
        """获取所有通道的状态摘要。"""
        lines = [
            f"外部桥接: {'硬件模式' if self.use_real_hardware else '模拟模式'}",
            f"PLC: {self.plc.get_status_str()}",
            f"网络屏: {'已连接' if self.hmi.connected else '未连接'} (发送: {self.hmi.send_count})",
            f"信号屏: {'已连接' if self.mmi.connected else '未连接'} (发送: {self.mmi.send_count})",
            f"UDP: {'运行中' if self.udp.is_connected() else '未启动'} "
            f"(发送: {self.udp.send_count}, 接收: {self.udp.recv_count})",
        ]
        return "\n".join(lines)

    # ── 内部辅助 ───────────────────────────────────────

    def _extract_lead_train(self, snapshot: dict) -> Optional[dict]:
        """从 snapshot 中提取首列车数据。"""
        trains = snapshot.get("trains", [])
        if not trains:
            return None
        return trains[0]

    def _build_hmi_state(self, snapshot: dict, train: dict, sim_params) -> dict:
        """从 snapshot 构建网络屏显示状态。"""
        state = train.get("state", {})
        forces = train.get("forces", {})

        speed_ms = state.get("speed", 0.0)
        speed_kmh = speed_ms * 3.6

        acceleration = state.get("acceleration", 0.0)
        traction_force = forces.get("traction", 0)
        brake_force = forces.get("brake", 0)

        # 级位判断
        if state.get("mode") == "emergency_brake":
            level_pos = LEVEL_POS["EMERGENCY"]
        elif brake_force > 0:
            level_pos = LEVEL_POS["BRAKE"]
        elif traction_force > 0:
            level_pos = LEVEL_POS["TRACTION"]
        else:
            level_pos = LEVEL_POS["COAST"]

        # 运行模式
        is_ato = state.get("mode") == "auto"
        run_mode = (0 << 4) | (1 if is_ato else 0)  # 高4位=门模式MM, 低4位=手动/ATO

        # 运行方向
        direction = state.get("direction", "down")
        run_dir = RUN_DIR["RIGHT"] if direction == "down" else RUN_DIR["LEFT"]

        # 司机室状态 (默认 TC1 激活)
        driver_room_state = (1 << 0) | (0 << 4)  # TC1激活, TC2未激活

        # 门状态 (默认全关)
        door_state = [0x00000000] * 6

        # 制动缸压力 (默认值)
        brake_pressure = [0] * 6

        # 站信息
        curr_station = state.get("target_station_id", 0)
        dist_to_station = state.get("distance_to_station", 0.0)

        return {
            "curr_station_id": curr_station,
            "next_station_id": min(curr_station + 1, 16),
            "end_station_id": 16,
            "power_state": 0,
            "speed": speed_kmh,
            "acceleration": acceleration,
            "power_pull": int(traction_force),
            "net_pressure": 1500,
            "speed_limit": int(speed_kmh * 1.3),  # 限速约1.3倍当前速度估算
            "level_pos": level_pos,
            "run_mode": run_mode,
            "master_v": 750,
            "run_dir": run_dir,
            "driver_room_state": driver_room_state,
            "door_state": door_state,
            "brake_pressure": brake_pressure,
            "train_no": 1,
            "fault_code": 0,
        }

    def _build_mmi_state(self, snapshot: dict, train: dict, sim_params) -> dict:
        """从 snapshot 构建信号屏显示状态。"""
        state = train.get("state", {})
        forces = train.get("forces", {})

        speed_ms = state.get("speed", 0.0)
        speed_kmh = speed_ms * 3.6
        acceleration = state.get("acceleration", 0.0)

        direction = state.get("direction", "down")
        run_dir = 1 if direction == "down" else 0  # 1=下行 0=上行

        # 驾驶模式
        if state.get("mode") == "emergency_brake":
            mode = 0  # RM
        elif state.get("mode") == "auto":
            mode = 3  # ATO
        else:
            mode = 0  # RM

        # 牵引/制动/紧急制动状态
        traction_state = 1 if forces.get("traction", 0) > 0 else 0
        brake_state = 1 if forces.get("brake", 0) > 0 else 0
        eb_state = 1 if state.get("mode") == "emergency_brake" else 0

        # 距离下一站
        dist_to_station = state.get("distance_to_station", 0.0)

        return {
            "curr_station_id": state.get("target_station_id", 0),
            "next_station_id": min(state.get("target_station_id", 0) + 1, 16),
            "end_station_id": 16,
            "cm_state": 0,
            "mm_state": 0,
            "ctc_state": 0,
            "run_direction": run_dir,
            "speed": speed_kmh,
            "acceleration": acceleration,
            "traction_cut": 0,
            "speed_limit": int(speed_kmh * 1.3),
            "mode": mode,
            "traction_state": traction_state,
            "brake_state": brake_state,
            "eb_state": eb_state,
            "event_id": 0,
            "signal_state": 0,
            "train_id": 1,
            "dist_to_station": dist_to_station,
        }

    def _build_udp_trains(self, snapshot: dict) -> list[dict]:
        """从 snapshot 构建 UDP 总控节点列车数据。"""
        trains = snapshot.get("trains", [])
        result = []
        for t in trains[:20]:
            state = t.get("state", {})
            speed_ms = state.get("speed", 0.0)
            result.append({
                "acceleration": state.get("acceleration", 0.0),
                "speed": speed_ms,
                "position": state.get("position", 0.0),
            })
        return result