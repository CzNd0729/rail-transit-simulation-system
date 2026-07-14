"""网络屏 (HMI) TCP 桥接层 — 发送车辆状态显示数据。

数据流:
  我们 ──TCP 572B──→ 网络屏 (车辆状态显示)
  网络屏 ──TCP 26B──→ 我们 (牵引切除请求)

文档: 外部系统对接方案 4.4 节
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from datetime import datetime
from typing import Optional

from .protocol import (
    NETWORK_SCREEN_DEVICE_IP, NETWORK_SCREEN_DEPLOY_IP, NETWORK_SCREEN_PORT,
    NETWORK_SCREEN_LEN, NETWORK_SCREEN_REQUEST_LEN,
    NETWORK_SCREEN_OFFSET, NETWORK_SCREEN_HEADER_ID,
    LEVEL_POS, RUN_DIR, CAB_STATE,
    RUN_MODE_MANUAL_ATO, DOOR_MODE_MM_AM_AA,
    _CAR_COUNT,
    CONNECT_TIMEOUT, SEND_TIMEOUT, RECV_TIMEOUT,
)

logger = logging.getLogger(__name__)


# ====================================================================
# 辅助函数
# ====================================================================

def _ensure_list(val, count: int, default=0):
    """确保 val 是长度为 count 的列表，不足用 default 填充。"""
    if val is None:
        return [default] * count
    lst = list(val)
    if len(lst) >= count:
        return lst[:count]
    return lst + [default] * (count - len(lst))


def _pack_car_floats(data: bytearray, offset: int, values: list, count: int):
    for i in range(min(len(values), count)):
        struct.pack_into("<f", data, offset + 4 * i, float(values[i]))


def _pack_car_words(data: bytearray, offset: int, values: list, count: int):
    for i in range(min(len(values), count)):
        struct.pack_into("<H", data, offset + 2 * i, values[i] & 0xFFFF)


def _pack_car_dwords(data: bytearray, offset: int, values: list, count: int):
    for i in range(min(len(values), count)):
        struct.pack_into("<I", data, offset + 4 * i, values[i] & 0xFFFFFFFF)


def _pack_car_bytes(data: bytearray, offset: int, values: list, count: int):
    for i in range(min(len(values), count)):
        data[offset + i] = values[i] & 0xFF


# ====================================================================
# 上位机 → 网络屏 (572字节) 打包
# ====================================================================

def pack_network_screen(
    # -- 报文头 --
    timestamp_ms: int = 0,
    verify_type: int = 0, verify_code: int = 0,
    protocol_id: int = 0, msg_id: int = 0,
    # -- 时间 --
    year: int = 2025, month: int = 1, day: int = 1,
    hour: int = 0, minute: int = 0, second: int = 0,
    # -- 基础运行信息 --
    curr_station_id: int = 0,
    next_station_id: int = 0,
    end_station_id: int = 0,
    power_state: int = 0,
    speed: float = 0.0,
    acceleration: float = 0.0,
    power_pull: int = 0,
    net_pressure: int = 1500,
    speed_limit: int = 0,
    level_pos: int = 0,
    run_mode: int = 0,
    master_v: int = 0,
    run_dir: int = 0,
    driver_room_state: int = 0,
    # -- 6节车 数组字段 --
    door_state: list = None,
    stop_pos_state: list = None,
    fire_empty_run: list = None,
    warm_empty_state1: list = None,
    warm_empty_state2: list = None,
    pull_switch: list = None,
    charge: list = None,
    assist_high_switch: list = None,
    breaker_master: list = None,
    elect_stop: list = None,
    wind_press: list = None,
    brake_pressure: list = None,
    usage_rate: list = None,
    line_net: list = None,
    temp: list = None,
    pull_stream: list = None,
    stop_im: list = None,
    side_info: list = None,
    braker_state: list = None,
    line_and_elect_stop: list = None,
    line_v: list = None,
    stop_state: list = None,
    air_stop: list = None,
    empty_press1: list = None,
    empty_press2: list = None,
    b05_and_b19: list = None,
    kma_and_elect_power: list = None,
    ni_bian_input_v: list = None,
    ni_bian_output_v: list = None,
    charge_output_v: list = None,
    ni_bian_input_a: list = None,
    ni_bian_output_a: list = None,
    charge_output_a: list = None,
    # -- 接触器/KM --
    tc1_km1: int = 0, tc1_km3: int = 0, tc1_km5: int = 0,
    tc2_km1: int = 0, tc2_km3: int = 0, tc2_km5: int = 0,
    # -- 蓄电池 TC1 --
    tc1_battle_remain: int = 0,
    tc1_battle_v: int = 0,
    tc1_battle_charge_a: int = 0,
    tc1_battle_output_a: int = 0,
    tc1_battle_temp: int = 0,
    tc1_hi_v: int = 0,
    tc1_li_v: int = 0,
    tc1_hi_pos: int = 0,
    tc1_li_pos: int = 0,
    tc1_temp: int = 0,
    tc2_temp: int = 0,
    tc1_temp_pos: int = 0,
    tc2_temp_pos: int = 0,
    # -- 蓄电池 TC2 --
    tc2_battle_remain: int = 0,
    tc2_battle_v: int = 0,
    tc2_battle_charge_a: int = 0,
    tc2_battle_output_a: int = 0,
    tc2_battle_temp: int = 0,
    tc2_hi_v: int = 0,
    tc2_li_v: int = 0,
    tc2_hi_pos: int = 0,
    tc2_li_pos: int = 0,
    # -- 烟火/空调 --
    smoke_temp: list = None,
    out_temp: list = None,
    inside_temp: list = None,
    air_cond_mode: list = None,
    cold_wind: list = None,
    wind_fan: list = None,
    press_machine: list = None,
    big_wind: list = None,
    machine11: list = None,
    machine12: list = None,
    machine21: list = None,
    machine22: list = None,
    # -- 网络设备 --
    tc1_net: list = None,
    tc2_net: list = None,
    tc3_net: list = None,
    tc4_net: list = None,
    tc5_net: list = None,
    tc6_net: list = None,
    conn_ab: int = 0,
    tc1_devs_state: int = 0,
    tc2_devs_state: int = 0,
    tc3_devs_state: int = 0,
    tc4_devs_state: int = 0,
    tc5_devs_state: int = 0,
    tc6_devs_state: int = 0,
    econn_dev_state: int = 0,
    econn_dev_state2: int = 0,
    fault_code: int = 0,
    train_no: int = 1,
) -> bytes:
    """打包 上位机 → 网络屏 显示数据 (572字节, 小端序)。

    文档: 外部系统对接方案 4.4 节
    """
    off = NETWORK_SCREEN_OFFSET
    data = bytearray(NETWORK_SCREEN_LEN)

    # -- 报文头 (24字节) --
    struct.pack_into("<I", data, off["identify"], NETWORK_SCREEN_HEADER_ID)
    struct.pack_into("<H", data, off["total_len"], NETWORK_SCREEN_LEN)
    struct.pack_into("<H", data, off["data_len"], NETWORK_SCREEN_LEN - 24)
    struct.pack_into("<Q", data, off["timestamp"], timestamp_ms & 0xFFFFFFFFFFFFFFFF)
    struct.pack_into("<H", data, off["verify_type"], verify_type & 0xFFFF)
    struct.pack_into("<H", data, off["verify_code"], verify_code & 0xFFFF)
    struct.pack_into("<H", data, off["protocol_id"], protocol_id & 0xFFFF)
    struct.pack_into("<H", data, off["msg_id"], msg_id & 0xFFFF)

    # -- 时间 --
    struct.pack_into("<H", data, off["year"], year & 0xFFFF)
    struct.pack_into("<H", data, off["month"], month & 0xFFFF)
    struct.pack_into("<H", data, off["day"], day & 0xFFFF)
    struct.pack_into("<H", data, off["hour"], hour & 0xFFFF)
    struct.pack_into("<H", data, off["minute"], minute & 0xFFFF)
    struct.pack_into("<H", data, off["second"], second & 0xFFFF)

    # -- 基础运行信息 --
    data[off["curr_station_id"]] = curr_station_id & 0xFF
    data[off["next_station_id"]] = next_station_id & 0xFF
    data[off["end_station_id"]] = end_station_id & 0xFF
    data[off["power_state"]] = power_state & 0xFF
    struct.pack_into("<f", data, off["speed"], float(speed))
    struct.pack_into("<f", data, off["acceleration"], float(acceleration))
    struct.pack_into("<H", data, off["power_pull"], power_pull & 0xFFFF)
    struct.pack_into("<H", data, off["net_pressure"], net_pressure & 0xFFFF)
    struct.pack_into("<H", data, off["speed_limit"], speed_limit & 0xFFFF)
    data[off["level_pos"]] = level_pos & 0xFF
    data[off["run_mode"]] = run_mode & 0xFF
    struct.pack_into("<H", data, off["master_v"], master_v & 0xFFFF)
    data[off["run_dir"]] = run_dir & 0xFF
    data[off["driver_room_state"]] = driver_room_state & 0xFF

    # -- 6节车 数组 --
    _pack_car_dwords(data, off["door_state"], _ensure_list(door_state, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["stop_pos_state"], _ensure_list(stop_pos_state, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["fire_empty_run"], _ensure_list(fire_empty_run, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["warm_empty_state1"], _ensure_list(warm_empty_state1, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["warm_empty_state2"], _ensure_list(warm_empty_state2, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["pull_switch"], _ensure_list(pull_switch, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["charge"], _ensure_list(charge, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["assist_high_switch"], _ensure_list(assist_high_switch, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["breaker_master"], _ensure_list(breaker_master, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["elect_stop"], _ensure_list(elect_stop, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["wind_press"], _ensure_list(wind_press, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["brake_pressure"], _ensure_list(brake_pressure, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["usage_rate"], _ensure_list(usage_rate, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["line_net"], _ensure_list(line_net, _CAR_COUNT), _CAR_COUNT)
    _pack_car_floats(data, off["temp"], _ensure_list(temp, _CAR_COUNT, 0.0), _CAR_COUNT)
    _pack_car_bytes(data, off["pull_stream"], _ensure_list(pull_stream, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["stop_im"], _ensure_list(stop_im, 10), 10)
    _pack_car_bytes(data, off["side_info"], _ensure_list(side_info, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["braker_state"], _ensure_list(braker_state, 11), 11)
    _pack_car_bytes(data, off["line_and_elect_stop"], _ensure_list(line_and_elect_stop, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["line_v"], _ensure_list(line_v, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["stop_state"], _ensure_list(stop_state, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["air_stop"], _ensure_list(air_stop, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["empty_press1"], _ensure_list(empty_press1, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["empty_press2"], _ensure_list(empty_press2, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["b05_and_b19"], _ensure_list(b05_and_b19, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["kma_and_elect_power"], _ensure_list(kma_and_elect_power, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["ni_bian_input_v"], _ensure_list(ni_bian_input_v, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["ni_bian_output_v"], _ensure_list(ni_bian_output_v, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["charge_output_v"], _ensure_list(charge_output_v, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["ni_bian_input_a"], _ensure_list(ni_bian_input_a, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["ni_bian_output_a"], _ensure_list(ni_bian_output_a, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["charge_output_a"], _ensure_list(charge_output_a, _CAR_COUNT), _CAR_COUNT)

    # -- 接触器/KM --
    data[off["tc1_km1"]] = tc1_km1 & 0xFF
    data[off["tc1_km3"]] = tc1_km3 & 0xFF
    data[off["tc1_km5"]] = tc1_km5 & 0xFF
    data[off["tc2_km1"]] = tc2_km1 & 0xFF
    data[off["tc2_km3"]] = tc2_km3 & 0xFF
    data[off["tc2_km5"]] = tc2_km5 & 0xFF

    # -- 蓄电池 TC1 --
    for name in ("tc1_battle_remain", "tc1_battle_v", "tc1_battle_charge_a",
                 "tc1_battle_output_a", "tc1_battle_temp", "tc1_hi_v", "tc1_li_v"):
        struct.pack_into("<H", data, off[name], locals().get(name, 0) & 0xFFFF)
    for name in ("tc1_hi_pos", "tc1_li_pos", "tc1_temp_pos", "tc2_temp_pos"):
        data[off[name]] = locals().get(name, 0) & 0xFF
    struct.pack_into("<H", data, off["tc1_temp"], tc1_temp & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_temp"], tc2_temp & 0xFFFF)

    # -- 蓄电池 TC2 --
    for name in ("tc2_battle_remain", "tc2_battle_v", "tc2_battle_charge_a",
                 "tc2_battle_output_a", "tc2_battle_temp", "tc2_hi_v", "tc2_li_v"):
        struct.pack_into("<H", data, off[name], locals().get(name, 0) & 0xFFFF)
    for name in ("tc2_hi_pos", "tc2_li_pos",):
        data[off[name]] = locals().get(name, 0) & 0xFF

    # -- 烟火/空调 --
    _pack_car_dwords(data, off["smoke_temp"], _ensure_list(smoke_temp, _CAR_COUNT), _CAR_COUNT)
    _pack_car_floats(data, off["out_temp"], _ensure_list(out_temp, _CAR_COUNT, 0.0), _CAR_COUNT)
    _pack_car_floats(data, off["inside_temp"], _ensure_list(inside_temp, _CAR_COUNT, 0.0), _CAR_COUNT)
    _pack_car_bytes(data, off["air_cond_mode"], _ensure_list(air_cond_mode, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["cold_wind"], _ensure_list(cold_wind, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["wind_fan"], _ensure_list(wind_fan, _CAR_COUNT), _CAR_COUNT)
    _pack_car_words(data, off["press_machine"], _ensure_list(press_machine, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["big_wind"], _ensure_list(big_wind, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["machine11"], _ensure_list(machine11, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["machine12"], _ensure_list(machine12, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["machine21"], _ensure_list(machine21, _CAR_COUNT), _CAR_COUNT)
    _pack_car_bytes(data, off["machine22"], _ensure_list(machine22, _CAR_COUNT), _CAR_COUNT)

    # -- 网络设备 --
    _pack_car_words(data, off["tc1_net"], _ensure_list(tc1_net, 2), 2)
    _pack_car_words(data, off["tc2_net"], _ensure_list(tc2_net, 2), 2)
    _pack_car_bytes(data, off["tc3_net"], _ensure_list(tc3_net, 2), 2)
    _pack_car_bytes(data, off["tc4_net"], _ensure_list(tc4_net, 2), 2)
    _pack_car_bytes(data, off["tc5_net"], _ensure_list(tc5_net, 2), 2)
    _pack_car_bytes(data, off["tc6_net"], _ensure_list(tc6_net, 2), 2)
    data[off["conn_ab"]] = conn_ab & 0xFF
    struct.pack_into("<H", data, off["tc1_devs_state"], tc1_devs_state & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_devs_state"], tc2_devs_state & 0xFFFF)
    data[off["tc3_devs_state"]] = tc3_devs_state & 0xFF
    data[off["tc4_devs_state"]] = tc4_devs_state & 0xFF
    data[off["tc5_devs_state"]] = tc5_devs_state & 0xFF
    data[off["tc6_devs_state"]] = tc6_devs_state & 0xFF
    data[off["econn_dev_state"]] = econn_dev_state & 0xFF
    data[off["econn_dev_state2"]] = econn_dev_state2 & 0xFF
    struct.pack_into("<H", data, off["fault_code"], fault_code & 0xFFFF)
    struct.pack_into("<H", data, off["train_no"], train_no & 0xFFFF)

    return bytes(data)


# ====================================================================
# 网络屏 → 上位机 牵引切除请求解析 (26字节)
# ====================================================================

def parse_network_screen_request(data: bytes) -> dict:
    """解析 网络屏 → 上位机 牵引切除请求报文 (26字节)。

    文档: 外部系统对接方案 4.4.1 节
    """
    if len(data) < NETWORK_SCREEN_REQUEST_LEN:
        raise ValueError(
            f"网络屏请求报文长度不足: {len(data)} < {NETWORK_SCREEN_REQUEST_LEN}"
        )

    identify = struct.unpack_from("<I", data, 0)[0]
    pull_ctrl = data[24] if len(data) > 24 else 0

    pull_cut = {}
    for car in range(6):
        pull_cut[f"car_{car + 1}"] = (pull_ctrl >> car) & 1 == 1

    return {
        "identify": f"0x{identify:08X}",
        "identify_ok": identify == NETWORK_SCREEN_HEADER_ID,
        "total_len": struct.unpack_from("<H", data, 4)[0],
        "data_len": struct.unpack_from("<H", data, 6)[0],
        "timestamp_ms": struct.unpack_from("<Q", data, 8)[0],
        "pull_ctrl": pull_ctrl,
        "pull_cut": pull_cut,
        "raw": data[:NETWORK_SCREEN_REQUEST_LEN],
    }


# ====================================================================
# 网络屏桥接客户端
# ====================================================================

class HmiBridge:
    """网络屏 (HMI) TCP 通信桥接。

    连接到网络屏设备，按需发送572字节车辆状态报文。

    用法:
        bridge = HmiBridge()
        bridge.connect()
        bridge.send(train_state_data)
    """

    def __init__(self, host: str = NETWORK_SCREEN_DEVICE_IP, port: int = NETWORK_SCREEN_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._connected = False

        # 最近一次发送的报文
        self.last_sent_data: Optional[bytes] = None
        self.last_send_time: Optional[float] = None

        # 统计
        self.send_count = 0

    @property
    def connected(self) -> bool:
        return self._connected and self.sock is not None

    def connect(self) -> bool:
        """连接网络屏。"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(CONNECT_TIMEOUT)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(RECV_TIMEOUT)
            self._connected = True
            logger.info(f"网络屏已连接: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"网络屏连接失败 {self.host}:{self.port}: {e}")
            self.sock = None
            self._connected = False
            return False

    def disconnect(self):
        """断开网络屏连接。"""
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("网络屏已断开")

    def send(self, data: bytes) -> bool:
        """发送一帧网络屏数据 (572字节)。

        Args:
            data: 572字节的完整报文。

        Returns:
            True 发送成功, False 失败。
        """
        if not self.sock or not self._connected:
            return False
        try:
            self.sock.sendall(data)
            self.last_sent_data = data
            self.last_send_time = time.time()
            self.send_count += 1
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.error(f"网络屏发送失败: {e}")
            self._connected = False
            return False

    def send_from_state(self, state: dict) -> bool:
        """从仿真状态字典构建并发送网络屏报文。

        Args:
            state: 包含以下键的字典:
                - speed, acceleration, power_pull, net_pressure, speed_limit
                - level_pos, run_mode, master_v, run_dir, driver_room_state
                - curr_station_id, next_station_id, end_station_id
                - train_no, door_state (list), brake_pressure (list), 等

        Returns:
            True 发送成功, False 失败。
        """
        now = datetime.now()
        data = pack_network_screen(
            timestamp_ms=int(time.time() * 1000),
            year=now.year, month=now.month, day=now.day,
            hour=now.hour, minute=now.minute, second=now.second,
            curr_station_id=state.get("curr_station_id", 0),
            next_station_id=state.get("next_station_id", 0),
            end_station_id=state.get("end_station_id", 0),
            power_state=state.get("power_state", 0),
            speed=state.get("speed", 0.0),
            acceleration=state.get("acceleration", 0.0),
            power_pull=state.get("power_pull", 0),
            net_pressure=state.get("net_pressure", 1500),
            speed_limit=state.get("speed_limit", 0),
            level_pos=state.get("level_pos", 0),
            run_mode=state.get("run_mode", 0),
            master_v=state.get("master_v", 0),
            run_dir=state.get("run_dir", 0),
            driver_room_state=state.get("driver_room_state", 0),
            door_state=state.get("door_state"),
            brake_pressure=state.get("brake_pressure"),
            temp=state.get("temp"),
            train_no=state.get("train_no", 1),
            fault_code=state.get("fault_code", 0),
        )
        return self.send(data)

    def is_connected(self) -> bool:
        return self.connected