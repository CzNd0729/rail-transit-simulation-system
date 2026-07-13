"""PLC TCP 通信桥接层 — 接收司机台手柄/按钮输入，下发指示灯状态。

数据流:
  PLC ──TCP 100ms(46B)──→ 我们 (手柄/按钮/开关)
  我们 ──TCP 按需(28B)──→ PLC (指示灯/速度回显)

文档: 外部系统对接方案 4.3 节
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from .protocol import (
    PLC_DEVICE_IP, PLC_PORT, PLC_PORT_B, PLC_PORT_C,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    PLC_HEADER_ID,
    CONNECT_TIMEOUT, SEND_TIMEOUT, RECV_TIMEOUT, PLC_RECV_TIMEOUT,
)

logger = logging.getLogger(__name__)


# ====================================================================
# 位映射定义 (文档 4.3 — 基于文档外部系统对接方案)
# ====================================================================

# 字节 24 位定义 (PLC → 上位机, 指示灯)
PLC_BIT_24 = {
    "reserved_0":      0x01,
    "hscb":           0x02,  # 高断合指示灯状态
    "brake_fault":    0x04,  # 制动缓解不良指示灯
    "reserved_3":     0x08,
    "reserved_4":     0x10,
    "door_closed":    0x20,  # 门关好指示灯
    "net_fault":      0x40,  # 网络故障指示灯
    "ar_available":   0x80,  # 具备自动折返模式标志
}

# 字节 25 位定义 (模式标志)
PLC_BIT_25 = {
    "ato_available":   0x01,  # 具备ATO模式标志
    "reserved_1":      0x02,
    "ato_active":      0x04,  # 激活ATO模式标志
    "reserved_3":      0x08,
    "reserved_4":      0x10,
    "reserved_5":      0x20,
    "reserved_6":      0x40,
    "reserved_7":      0x80,
}

# 字节 28 位定义 (按钮/标志)
PLC_BIT_28 = {
    "eb_button":         0x01,  # 紧急制动按钮状态
    "bus_ctrl":          0x02,  # 母线控制按钮状态
    "forced_release":    0x04,  # 强迫缓解标志
    "forced_pump":       0x08,  # 强迫泵风标志
    "emergency_cmd":     0x10,  # 应急指挥按钮状态
    "parking_apply":     0x20,  # 停放制动施加标志
    "parking_release":   0x40,  # 停放制动缓解标志
    "horn":              0x80,  # 电笛标志
}

# 字节 29 位定义 (门控标志)
PLC_BIT_29 = {
    "open_left_door":   0x01,  # 开左门标志
    "open_right_door":  0x02,  # 开右门标志
    "close_left_door":  0x04,  # 关左门标志
    "close_right_door": 0x08,  # 关右门标志
}

# 字节 34 位定义 (按钮/开关)
PLC_BIT_34 = {
    "high_accel":       0x01,  # 高加速按钮状态
    "cab_light":        0x02,  # 司机室照明开关
    "mode_up_confirm":  0x04,  # 模式升级确认标志
    "mode_down_confirm":0x08,  # 模式降级确认标志
    "confirm_flag":     0x10,  # 确认标志
    "ar_flag":          0x20,  # 自动折返标志
    "traction_reset":   0x40,  # 牵引辅助复位标志
    "ato_start":        0x80,  # ATO启动标志
}

# 字节 35 位定义 (开关/标志)
PLC_BIT_35 = {
    "wash_switch":      0x01,  # 洗车模式开关
    "key_switch":       0x02,  # 钥匙开关状态
    "alert_flag":       0x04,  # 警惕标志
    "alert_release":    0x08,  # 警惕允许解除标志
}

# 所有位定义按字节分组
PLC_BIT_GROUPS = {
    24: PLC_BIT_24,
    25: PLC_BIT_25,
    28: PLC_BIT_28,
    29: PLC_BIT_29,
    34: PLC_BIT_34,
    35: PLC_BIT_35,
}

# 方向手柄状态枚举
DIR_HANDLE_MAP = {
    0: "0位",
    1: "向前",
    2: "向后",
}

# 主手柄状态枚举
MAIN_HANDLE_MAP = {
    0: "0位",
    1: "牵引",
    2: "制动",
    4: "快制",
}


# ====================================================================
# 编解码辅助函数
# ====================================================================

def _decode_bits_byte(byte_val: int, bit_map: dict) -> dict:
    """将单字节按位图解码为布尔值字典。"""
    return {name: (byte_val & mask) != 0 for name, mask in bit_map.items()}


def _encode_bits_byte(bits: dict, bit_map: dict) -> int:
    """将布尔值字典按位图编码为单字节。"""
    val = 0
    for name, mask in bit_map.items():
        if bits.get(name, False):
            val |= mask
    return val


# ====================================================================
# PLC → 上位机 报文解析 (46字节, 小端序)
# ====================================================================

def parse_plc_to_upper(data: bytes) -> dict:
    """解析 PLC → 上位机 报文 (46字节, 小端序)

    文档: 外部系统对接方案 4.3.1 节
    """
    if len(data) < PLC_TO_UPPER_LEN:
        raise ValueError(f"PLC报文长度不足: {len(data)} < {PLC_TO_UPPER_LEN}")

    identify = struct.unpack_from("<I", data, 0)[0]
    total_len = struct.unpack_from("<H", data, 4)[0]
    data_len = struct.unpack_from("<H", data, 6)[0]

    # 时间
    year = struct.unpack_from("<H", data, 8)[0]
    month = struct.unpack_from("<H", data, 10)[0]
    day = struct.unpack_from("<H", data, 12)[0]
    hour = struct.unpack_from("<H", data, 14)[0]
    minute = struct.unpack_from("<H", data, 16)[0]
    second = struct.unpack_from("<H", data, 18)[0]

    # 校验
    verify_type = struct.unpack_from("<H", data, 20)[0]
    verify_code = struct.unpack_from("<H", data, 22)[0]

    # BOOL 标志字节
    flags_24 = _decode_bits_byte(data[24], PLC_BIT_24) if len(data) > 24 else {}
    flags_25 = _decode_bits_byte(data[25], PLC_BIT_25) if len(data) > 25 else {}

    # 车辆速度 (WORD, 小端)
    vehicle_speed = struct.unpack_from("<H", data, 26)[0] if len(data) > 26 else 0

    flags_28 = _decode_bits_byte(data[28], PLC_BIT_28) if len(data) > 28 else {}
    flags_29 = _decode_bits_byte(data[29], PLC_BIT_29) if len(data) > 29 else {}

    # 外部照明 / 门模式
    light_switch = struct.unpack_from("<H", data, 30)[0] if len(data) > 30 else 0
    door_mode_switch = struct.unpack_from("<H", data, 32)[0] if len(data) > 32 else 0

    flags_34 = _decode_bits_byte(data[34], PLC_BIT_34) if len(data) > 34 else {}
    flags_35 = _decode_bits_byte(data[35], PLC_BIT_35) if len(data) > 35 else {}

    # 方向手柄 / 主手柄 / 极位
    dir_handle = struct.unpack_from("<H", data, 36)[0] if len(data) > 36 else 0
    main_handle = struct.unpack_from("<H", data, 38)[0] if len(data) > 38 else 0
    traction_level = struct.unpack_from("<H", data, 40)[0] if len(data) > 40 else 0
    brake_level = struct.unpack_from("<H", data, 42)[0] if len(data) > 42 else 0
    traction_level_pct = traction_level / 256.0
    brake_level_pct = brake_level / 256.0

    return {
        "identify": hex(identify),
        "identify_ok": identify == PLC_HEADER_ID,
        "total_len": total_len,
        "data_len": data_len,
        # 时间
        "year": year, "month": month, "day": day,
        "hour": hour, "minute": minute, "second": second,
        "timestamp_str": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}",
        "verify_type": verify_type,
        "verify_code": verify_code,
        # 指示灯标志 (字节24)
        "hscb": flags_24.get("hscb", False),
        "brake_fault_indicator": flags_24.get("brake_fault", False),
        "door_closed_indicator": flags_24.get("door_closed", False),
        "net_fault_indicator": flags_24.get("net_fault", False),
        "ar_available": flags_24.get("ar_available", False),
        # 模式标志 (字节25)
        "ato_available": flags_25.get("ato_available", False),
        "ato_active": flags_25.get("ato_active", False),
        # 车辆速度 (PLC 回显的速度)
        "vehicle_speed": vehicle_speed,
        # 按钮标志 (字节28)
        "eb_button_locked": flags_28.get("eb_button", False),
        "bus_ctrl_locked": flags_28.get("bus_ctrl", False),
        "forced_release": flags_28.get("forced_release", False),
        "forced_pump": flags_28.get("forced_pump", False),
        "emergency_cmd_locked": flags_28.get("emergency_cmd", False),
        "parking_apply": flags_28.get("parking_apply", False),
        "parking_release": flags_28.get("parking_release", False),
        "horn": flags_28.get("horn", False),
        # 门控标志 (字节29)
        "open_left_door": flags_29.get("open_left_door", False),
        "open_right_door": flags_29.get("open_right_door", False),
        "close_left_door": flags_29.get("close_left_door", False),
        "close_right_door": flags_29.get("close_right_door", False),
        # 照明 / 门模式
        "light_switch": light_switch,
        "door_mode_switch": door_mode_switch,
        # 按钮 (字节34)
        "high_accel": flags_34.get("high_accel", False),
        "cab_light": flags_34.get("cab_light", False),
        "mode_up_confirm": flags_34.get("mode_up_confirm", False),
        "mode_down_confirm": flags_34.get("mode_down_confirm", False),
        "confirm_flag": flags_34.get("confirm_flag", False),
        "ar_flag": flags_34.get("ar_flag", False),
        "traction_reset": flags_34.get("traction_reset", False),
        "ato_start_flag": flags_34.get("ato_start", False),
        # 开关 (字节35)
        "wash_switch": flags_35.get("wash_switch", False),
        "key_switch": flags_35.get("key_switch", False),
        "alert_flag": flags_35.get("alert_flag", False),
        "alert_release": flags_35.get("alert_release", False),
        # 手柄
        "dir_handle": dir_handle,
        "dir_handle_str": DIR_HANDLE_MAP.get(dir_handle, f"未知({dir_handle})"),
        "main_handle": main_handle,
        "main_handle_str": MAIN_HANDLE_MAP.get(main_handle, f"未知({main_handle})"),
        "traction_level": traction_level,
        "traction_level_pct": round(traction_level_pct, 1),
        "brake_level": brake_level,
        "brake_level_pct": round(brake_level_pct, 1),
        "raw": data[:PLC_TO_UPPER_LEN],
    }


# ====================================================================
# PLC → 上位机 报文打包 (46字节, 小端序) — 供模拟器使用
# ====================================================================

def pack_plc_to_upper(
    year: int = 2025, month: int = 7, day: int = 13,
    hour: int = 0, minute: int = 0, second: int = 0,
    verify_type: int = 0, verify_code: int = 0,
    # 字节 24 标志 (指示灯)
    hscb: int = 0, brake_fault: int = 0,
    door_closed: int = 0, net_fault: int = 0, ar_available: int = 0,
    # 字节 25 标志 (模式)
    ato_available: int = 0, wash_mode: int = 0,
    ato_active: int = 0, ar_active: int = 0,
    # 车辆速度
    vehicle_speed: int = 0,
    # 字节 28 标志 (按钮)
    eb_button: int = 0, bus_ctrl: int = 0,
    forced_release: int = 0, forced_pump: int = 0,
    emergency_cmd: int = 0, parking_apply: int = 0,
    parking_release: int = 0, horn: int = 0,
    # 字节 29 标志 (门控)
    open_left_door: int = 0, open_right_door: int = 0,
    close_left_door: int = 0, close_right_door: int = 0,
    # 外部照明 / 门模式
    light_switch: int = 0, door_mode_switch: int = 0,
    # 字节 34 标志
    high_accel: int = 0, cab_light: int = 0,
    mode_up_confirm: int = 0, mode_down_confirm: int = 0,
    confirm_flag: int = 0, ar_flag: int = 0,
    traction_reset: int = 0, ato_start: int = 0,
    # 字节 35 标志
    wash_switch: int = 0, key_switch: int = 0,
    alert_flag: int = 0, alert_release: int = 0,
    # 手柄
    dir_handle: int = 0, main_handle: int = 0,
    traction_level: int = 0, brake_level: int = 0,
) -> bytes:
    """打包 PLC → 上位机 报文 (46字节, 小端序)。

    供 PLC 模拟器和测试使用。
    文档: 外部系统对接方案 4.3.1 节
    """
    data = bytearray(PLC_TO_UPPER_LEN)

    # 固定头 (小端序)
    struct.pack_into("<I", data, 0, PLC_HEADER_ID)
    struct.pack_into("<H", data, 4, PLC_TO_UPPER_LEN)
    struct.pack_into("<H", data, 6, 22)

    # 时间
    struct.pack_into("<H", data, 8, year & 0xFFFF)
    struct.pack_into("<H", data, 10, month & 0xFFFF)
    struct.pack_into("<H", data, 12, day & 0xFFFF)
    struct.pack_into("<H", data, 14, hour & 0xFFFF)
    struct.pack_into("<H", data, 16, minute & 0xFFFF)
    struct.pack_into("<H", data, 18, second & 0xFFFF)

    # 校验
    struct.pack_into("<H", data, 20, verify_type & 0xFFFF)
    struct.pack_into("<H", data, 22, verify_code & 0xFFFF)

    # 字节 24-25 BOOL 标志
    data[24] = _encode_bits_byte(
        {"hscb": hscb, "brake_fault": brake_fault,
         "door_closed": door_closed, "net_fault": net_fault,
         "ar_available": ar_available},
        PLC_BIT_24,
    )
    data[25] = _encode_bits_byte(
        {"ato_available": ato_available, "reserved_1": wash_mode,
         "ato_active": ato_active},
        PLC_BIT_25,
    )

    # 车辆速度
    struct.pack_into("<H", data, 26, vehicle_speed & 0xFFFF)

    # 字节 28-29 BOOL 标志
    data[28] = _encode_bits_byte(
        {"eb_button": eb_button, "bus_ctrl": bus_ctrl,
         "forced_release": forced_release, "forced_pump": forced_pump,
         "emergency_cmd": emergency_cmd, "parking_apply": parking_apply,
         "parking_release": parking_release, "horn": horn},
        PLC_BIT_28,
    )
    data[29] = _encode_bits_byte(
        {"open_left_door": open_left_door, "open_right_door": open_right_door,
         "close_left_door": close_left_door, "close_right_door": close_right_door},
        PLC_BIT_29,
    )

    # 外部照明 / 门模式
    struct.pack_into("<H", data, 30, light_switch & 0xFFFF)
    struct.pack_into("<H", data, 32, door_mode_switch & 0xFFFF)

    # 字节 34-35 BOOL 标志
    data[34] = _encode_bits_byte(
        {"high_accel": high_accel, "cab_light": cab_light,
         "mode_up_confirm": mode_up_confirm, "mode_down_confirm": mode_down_confirm,
         "confirm_flag": confirm_flag, "ar_flag": ar_flag,
         "traction_reset": traction_reset, "ato_start": ato_start},
        PLC_BIT_34,
    )
    data[35] = _encode_bits_byte(
        {"wash_switch": wash_switch, "key_switch": key_switch,
         "alert_flag": alert_flag, "alert_release": alert_release},
        PLC_BIT_35,
    )

    # 手柄
    struct.pack_into("<H", data, 36, dir_handle & 0xFFFF)
    struct.pack_into("<H", data, 38, main_handle & 0xFFFF)
    struct.pack_into("<H", data, 40, traction_level & 0xFFFF)
    struct.pack_into("<H", data, 42, brake_level & 0xFFFF)

    return bytes(data)


def parse_upper_to_plc(data: bytes) -> dict:
    """解析 上位机 → PLC 报文 (28字节, 小端序)。

    供模拟器和测试使用。
    文档: 外部系统对接方案 4.3.2 节
    """
    if len(data) < UPPER_TO_PLC_LEN:
        raise ValueError(f"上位机报文长度不足: {len(data)} < {UPPER_TO_PLC_LEN}")

    identify = struct.unpack_from("<I", data, 0)[0]
    total_len = struct.unpack_from("<H", data, 4)[0]
    data_len = struct.unpack_from("<H", data, 6)[0]

    result = {
        "identify": hex(identify),
        "identify_ok": identify == PLC_HEADER_ID,
        "total_len": total_len,
        "data_len": data_len,
        # 时间
        "year": struct.unpack_from("<H", data, 8)[0],
        "month": struct.unpack_from("<H", data, 10)[0],
        "day": struct.unpack_from("<H", data, 12)[0],
        "hour": struct.unpack_from("<H", data, 14)[0],
        "minute": struct.unpack_from("<H", data, 16)[0],
        "second": struct.unpack_from("<H", data, 18)[0],
        "verify_type": struct.unpack_from("<H", data, 20)[0],
        "verify_code": struct.unpack_from("<H", data, 22)[0],
        # 字节24: 指示灯
        "hscb": bool(data[24] & 0x02),
        "brake_fault_indicator": bool(data[24] & 0x04),
        "door_open_light": bool(data[24] & 0x10),
        "door_closed_indicator": bool(data[24] & 0x20),
        "net_fault_indicator": bool(data[24] & 0x40),
        "ar_available": bool(data[24] & 0x80),
        # 字节25: 模式
        "ato_available": bool(data[25] & 0x01),
        "wash_mode": bool(data[25] & 0x02),
        "ato_active": bool(data[25] & 0x04),
        "ar_active": bool(data[25] & 0x08),
        # 车辆速度
        "vehicle_speed": struct.unpack_from("<H", data, 26)[0] if len(data) > 26 else 0,
        "raw": bytes(data[:UPPER_TO_PLC_LEN]),
    }
    return result


# ====================================================================
# 上位机 → PLC 报文打包 (28字节, 小端序)
# ====================================================================

def pack_upper_to_plc(
    year: int = 2025, month: int = 7, day: int = 13,
    hour: int = 0, minute: int = 0, second: int = 0,
    verify_type: int = 0, verify_code: int = 0,
    # 字节 24 标志 (指示灯)
    hscb: int = 0, brake_fault: int = 0,
    door_open_light: int = 0, door_closed: int = 0,
    net_fault: int = 0, ar_available: int = 0,
    # 字节 25 标志 (模式)
    ato_available: int = 0, wash_mode: int = 0,
    ato_active: int = 0, ar_active: int = 0,
    # 车辆速度
    vehicle_speed: int = 0,
) -> bytes:
    """打包 上位机 → PLC 报文 (28字节, 小端序)

    文档: 外部系统对接方案 4.3.2 节
    """
    data = bytearray(UPPER_TO_PLC_LEN)

    # 固定头 (小端序)
    struct.pack_into("<I", data, 0, PLC_HEADER_ID)
    struct.pack_into("<H", data, 4, UPPER_TO_PLC_LEN)
    struct.pack_into("<H", data, 6, 4)  # data_len = 4 (2字节数据区 + 2字节速度)

    # 时间
    struct.pack_into("<H", data, 8, year & 0xFFFF)
    struct.pack_into("<H", data, 10, month & 0xFFFF)
    struct.pack_into("<H", data, 12, day & 0xFFFF)
    struct.pack_into("<H", data, 14, hour & 0xFFFF)
    struct.pack_into("<H", data, 16, minute & 0xFFFF)
    struct.pack_into("<H", data, 18, second & 0xFFFF)

    # 校验
    struct.pack_into("<H", data, 20, verify_type & 0xFFFF)
    struct.pack_into("<H", data, 22, verify_code & 0xFFFF)

    # 字节 24: 指示灯标志 (使用 7.2 方向位定义, bit4=开门灯)
    data[24] = _encode_bits_byte({
        "hscb": hscb, "brake_fault": brake_fault,
        "door_open_light": door_open_light,
        "door_closed": door_closed,
        "net_fault": net_fault, "ar_available": ar_available,
    }, {
        "reserved_0": 0x01,
        "hscb": 0x02,
        "brake_fault": 0x04,
        "reserved_3": 0x08,
        "door_open_light": 0x10,
        "door_closed": 0x20,
        "net_fault": 0x40,
        "ar_available": 0x80,
    })

    # 字节 25: 模式标志
    data[25] = _encode_bits_byte({
        "ato_available": ato_available, "wash_mode": wash_mode,
        "ato_active": ato_active, "ar_active": ar_active,
    }, PLC_BIT_25)

    # 车辆速度 (WORD, 小端)
    struct.pack_into("<H", data, 26, vehicle_speed & 0xFFFF)

    return bytes(data)


# ====================================================================
# PLC 桥接客户端
# ====================================================================

class PlcBridge:
    """PLC TCP 通信桥接。

    管理三路 TCP 连接 (8001/8002/8003)，接收 PLC 手柄/按钮数据，
    下发指示灯和速度回显。

    用法:
        bridge = PlcBridge()
        bridge.connect()
        bridge.start()
        state = bridge.get_plc_state()  # 获取最新 PLC 输入
        bridge.set_vehicle_speed(60)    # 设置下发速度
    """

    def __init__(self, host: str = PLC_DEVICE_IP, port: int = PLC_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.running = False

        # 最新 PLC 状态
        self.last_plc_state: Optional[dict] = None
        self.last_recv_time: Optional[float] = None

        # 待发送的 7.2 控制值
        self.send_vehicle_speed = 0
        self.send_hscb = 0
        self.send_brake_fault = 0
        self.send_door_open_light = 0
        self.send_door_closed = 0
        self.send_net_fault = 0
        self.send_ar_available = 0
        self.send_ato_available = 0
        self.send_wash_mode = 0
        self.send_ato_active = 0
        self.send_ar_active = 0

        # 发送周期 (与 PLC 100ms 周期一致)
        self.send_interval = 0.1

        # 回调: 收到新 PLC 数据时触发
        self.on_plc_data: Optional[Callable[[dict], None]] = None

        # 统计
        self.pkt_count = 0
        self.send_count = 0
        self._connected = False

    # ── 连接管理 ──────────────────────────────────────

    @property
    def connected(self) -> bool:
        return self._connected and self.sock is not None

    def connect(self) -> bool:
        """连接 PLC 服务器。"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(CONNECT_TIMEOUT)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(RECV_TIMEOUT)
            self._connected = True
            logger.info(f"PLC 已连接: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"PLC 连接失败 {self.host}:{self.port}: {e}")
            self.sock = None
            self._connected = False
            return False

    def disconnect(self):
        """断开 PLC 连接。"""
        self.running = False
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("PLC 已断开")

    def start(self):
        """启动收发线程。"""
        if not self.sock:
            raise RuntimeError("请先调用 connect()")
        self.running = True

        recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        send_thread = threading.Thread(target=self._send_loop, daemon=True)
        recv_thread.start()
        send_thread.start()
        logger.info("PLC 收发线程已启动")

    def stop(self):
        """停止并断开。"""
        self.disconnect()

    # ── 接收线程 ──────────────────────────────────────

    def _recv_loop(self):
        """接收 PLC 7.1 报文循环。"""
        buffer = b""
        while self.running:
            try:
                if len(buffer) < PLC_TO_UPPER_LEN:
                    chunk = self.sock.recv(1024)
                    if not chunk:
                        logger.warning("PLC 连接断开")
                        self._connected = False
                        break
                    buffer += chunk

                while len(buffer) >= PLC_TO_UPPER_LEN:
                    pkt = buffer[:PLC_TO_UPPER_LEN]
                    buffer = buffer[PLC_TO_UPPER_LEN:]
                    try:
                        parsed = parse_plc_to_upper(pkt)
                        self.last_plc_state = parsed
                        self.last_recv_time = time.time()
                        self.pkt_count += 1
                        if self.on_plc_data:
                            self.on_plc_data(parsed)
                    except Exception as e:
                        logger.warning(f"解析 PLC 报文失败: {e}")
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                logger.error(f"PLC 接收异常: {e}")
                self._connected = False
                break

    # ── 发送线程 ──────────────────────────────────────

    def _send_loop(self):
        """周期发送上位机 7.2 报文。"""
        while self.running:
            if self.sock and self._connected:
                try:
                    data = self._build_packet()
                    self.sock.sendall(data)
                    self.send_count += 1
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    logger.error(f"PLC 发送失败: {e}")
                    self._connected = False
                    break
            time.sleep(self.send_interval)

    def _build_packet(self) -> bytes:
        """构建当前 7.2 报文，时间自动取系统时钟。"""
        now = datetime.now()
        return pack_upper_to_plc(
            year=now.year, month=now.month, day=now.day,
            hour=now.hour, minute=now.minute, second=now.second,
            hscb=self.send_hscb,
            brake_fault=self.send_brake_fault,
            door_open_light=self.send_door_open_light,
            door_closed=self.send_door_closed,
            net_fault=self.send_net_fault,
            ar_available=self.send_ar_available,
            ato_available=self.send_ato_available,
            wash_mode=self.send_wash_mode,
            ato_active=self.send_ato_active,
            ar_active=self.send_ar_active,
            vehicle_speed=self.send_vehicle_speed,
        )

    # ── 公开 API ──────────────────────────────────────

    def set_vehicle_speed(self, speed: int):
        """设置下发给 PLC 的车辆速度 (0-65535)。"""
        self.send_vehicle_speed = max(0, min(65535, int(speed)))

    def set_indicator(self, name: str, value: bool):
        """设置指示灯/模式标志。

        name 取值: hscb, brake_fault, door_open_light, door_closed,
                   net_fault, ar_available, ato_available,
                   wash_mode, ato_active, ar_active
        """
        v = 1 if value else 0
        attr_map = {
            "hscb": "send_hscb",
            "brake_fault": "send_brake_fault",
            "door_open_light": "send_door_open_light",
            "door_closed": "send_door_closed",
            "net_fault": "send_net_fault",
            "ar_available": "send_ar_available",
            "ato_available": "send_ato_available",
            "wash_mode": "send_wash_mode",
            "ato_active": "send_ato_active",
            "ar_active": "send_ar_active",
        }
        attr = attr_map.get(name)
        if attr is None:
            raise ValueError(f"未知标志名: {name}")
        setattr(self, attr, v)

    def get_plc_state(self) -> Optional[dict]:
        """获取最近一次 PLC 状态。"""
        return self.last_plc_state

    def get_plc_input_summary(self) -> dict:
        """提取 PLC 输入中与仿真决策相关的关键字段。"""
        if self.last_plc_state is None:
            return {
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

        s = self.last_plc_state
        return {
            "connected": True,
            "eb_button": s.get("eb_button_locked", False),
            "key_switch": s.get("key_switch", False),
            "ato_start": s.get("ato_start_flag", False),
            "ato_active": s.get("ato_active", False),
            "dir_handle": s.get("dir_handle", 0),
            "dir_handle_str": s.get("dir_handle_str", "0位"),
            "main_handle": s.get("main_handle", 0),
            "main_handle_str": s.get("main_handle_str", "0位"),
            "traction_level_pct": s.get("traction_level_pct", 0.0),
            "brake_level_pct": s.get("brake_level_pct", 0.0),
            "alert_flag": s.get("alert_flag", False),
            "open_left_door": s.get("open_left_door", False),
            "open_right_door": s.get("open_right_door", False),
            "close_left_door": s.get("close_left_door", False),
            "close_right_door": s.get("close_right_door", False),
            "light_switch": s.get("light_switch", 0),
            "door_mode_switch": s.get("door_mode_switch", 0),
        }

    def is_connected(self) -> bool:
        """检查 PLC 是否在线（距上次接收不超过超时时间）。"""
        if self.last_recv_time is None:
            return False
        return (time.time() - self.last_recv_time) < PLC_RECV_TIMEOUT

    def get_status_str(self) -> str:
        """获取当前状态摘要。"""
        lines = [
            f"连接: {'✓' if self.connected else '✗'}",
            f"接收: {self.pkt_count} 包  发送: {self.send_count} 包",
        ]
        if self.last_recv_time:
            elapsed = time.time() - self.last_recv_time
            lines.append(f"距上次接收: {elapsed:.1f}s")
        if self.last_plc_state:
            s = self.last_plc_state
            lines.extend([
                f"时间: {s.get('timestamp_str', 'N/A')}",
                f"速度: {s.get('vehicle_speed', 'N/A')}",
                f"手柄: 方向={s.get('dir_handle_str', 'N/A')}  "
                f"主手柄={s.get('main_handle_str', 'N/A')}  "
                f"牵引={s.get('traction_level_pct', 'N/A')}%  "
                f"制动={s.get('brake_level_pct', 'N/A')}%",
                f"EB={_bs(s.get('eb_button_locked'))}  "
                f"钥匙={_bs(s.get('key_switch'))}  "
                f"ATO启动={_bs(s.get('ato_start_flag'))}  "
                f"门关好={_bs(s.get('door_closed_indicator'))}",
            ])
        return "\n".join(lines)


def _bs(val) -> str:
    return "●" if val else "○"