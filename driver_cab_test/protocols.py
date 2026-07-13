"""
司机台联动测试 -- 协议编解码核心库
=====================================
实现 PLC 协议、网络屏协议、信号屏协议、信号系统 UDP 协议的
报文打包（编码）与解析（解码）功能。
"""

import struct
import logging
from typing import Optional

from .config import (
    PLC_OFFSET, UPPER_OFFSET,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    NETWORK_SCREEN_LEN, NETWORK_SCREEN_REQUEST_LEN,
    NETWORK_SCREEN_OFFSET, NETWORK_SCREEN_REQUEST_OFFSET,
    SIGNAL_SCREEN_LEN,
    ATP_SAFE_INPUT, ATP_NONSAFE_INPUT, ATO_NONSAFE_INPUT,
    ATP_SAFE_OUTPUT, ATP_NONSAFE_OUTPUT, ATO_NONSAFE_OUTPUT,
    TRACTION_BRAKE, TRAIN_DIRECTION,
    LEVEL_POS, RUN_DIR, CAB_STATE, DOOR_STATE, BRAKE_PARKING_STATE,
    FIRE_STATE, SLIP_STATE, PASSENGER_ALARM_STATE,
    RUN_MODE_MANUAL_ATO, DOOR_MODE_MM_AM_AA,
    BREAKER_STATE, DEVICE_WORK_STATE,
    AIR_COND_CTRL_MODE, AIR_COND_MODE,
)

logger = logging.getLogger(__name__)


# ====================================================================
# PLC 协议编解码（文档 7.1 / 7.2 节，PLC 使用大端序）
# ====================================================================

# ---- PLC -> 上位机 (46字节, 大端序) ----

# 字节 24 位定义 — 7.1 方向 (PLC -> 上位机, 位4=预留)
PLC_BIT_24_7_1 = {
    "reserved_24_0":   0x01,  # 预留
    "hscb":           0x02,  # 高断合指示灯状态 1=亮 0=灭
    "brake_fault":    0x04,  # 制动缓解不良指示灯状态 1=亮 0=灭
    "reserved_24_3":  0x08,  # 预留
    "reserved_24_4":  0x10,  # 预留（7.1方向无开门灯）
    "door_closed":    0x20,  # 门关好指示灯状态 1=亮 0=灭
    "net_fault":      0x40,  # 网络故障指示灯状态 1=亮 0=灭
    "ar_available":   0x80,  # 具备自动折返模式标志 1=具备
}

# 字节 24 位定义 — 7.2 方向 (上位机 -> PLC, 位4=开门灯)
PLC_BIT_24_7_2 = {
    "reserved_24_0":   0x01,  # 预留
    "hscb":           0x02,  # 高断合指示灯状态 1=亮 0=灭
    "brake_fault":    0x04,  # 制动缓解不良指示灯状态 1=亮 0=灭
    "reserved_24_3":  0x08,  # 预留
    "door_open_light":0x10,  # 开门灯状态 1=亮 0=灭
    "door_closed":    0x20,  # 门关好指示灯状态 1=亮 0=灭
    "net_fault":      0x40,  # 网络故障指示灯状态 1=亮 0=灭
    "ar_available":   0x80,  # 具备自动折返模式标志 1=具备
}

# 字节 25 位定义 (模式标志)
PLC_BIT_25 = {
    "ato_available":   0x01,  # 具备ATO模式标志 1=具备
    "wash_mode":       0x02,  # 进入洗车模式标志 1=进入
    "ato_active":      0x04,  # 激活ATO模式标志 1=激活
    "ar_active":       0x08,  # 激活自动折返模式标志 1=激活
    "reserved_25_4":   0x10,  # 预留
    "reserved_25_5":   0x20,  # 预留
    "reserved_25_6":   0x40,  # 预留
    "reserved_25_7":   0x80,  # 预留
}

# 字节 28 位定义 (按钮/标志)
PLC_BIT_28 = {
    "eb_button":         0x01,  # 紧急制动按钮状态 1=锁定 0=解除
    "bus_ctrl":          0x02,  # 母线控制按钮状态 1=锁定 0=解除
    "forced_release":    0x04,  # 强迫缓解标志 1=触发 0=复位
    "forced_pump":       0x08,  # 强迫泵风标志 1=触发 0=复位
    "emergency_cmd":     0x10,  # 应急指挥按钮状态 1=锁定 0=解除
    "parking_apply":     0x20,  # 停放制动施加标志 1=触发 0=复位
    "parking_release":   0x40,  # 停放制动缓解标志 1=触发 0=复位
    "horn":              0x80,  # 电笛标志 1=触发 0=复位
}

# 字节 29 位定义 (门控标志)
PLC_BIT_29 = {
    "open_left_door":   0x01,  # 开左门标志 1=触发 0=复位
    "open_right_door":  0x02,  # 开右门标志 1=触发 0=复位
    "close_left_door":  0x04,  # 关左门标志 1=触发 0=复位
    "close_right_door": 0x08,  # 关右门标志 1=触发 0=复位
    "reserved_29_4":    0x10,  # 预留
    "reserved_29_5":    0x20,  # 预留
    "reserved_29_6":    0x40,  # 预留
    "reserved_29_7":    0x80,  # 预留
}

# 字节 34 位定义 (按钮/开关)
PLC_BIT_34 = {
    "high_accel":       0x01,  # 高加速按钮状态 1=锁定 0=解除
    "cab_light":        0x02,  # 司机室照明开关状态 1=锁定 0=解除
    "mode_up_confirm":  0x04,  # 模式升级确认标志 1=触发 0=复位
    "mode_down_confirm":0x08,  # 模式降级确认标志 1=触发 0=复位
    "confirm_flag":     0x10,  # 确认标志 1=触发 0=复位
    "ar_flag":          0x20,  # 自动折返标志 1=触发 0=复位
    "traction_reset":   0x40,  # 牵引辅助复位标志 1=触发 0=复位
    "ato_start":        0x80,  # ATO启动标志 1=触发 0=复位
}

# 字节 35 位定义 (开关/标志)
PLC_BIT_35 = {
    "wash_switch":      0x01,  # 洗车模式开关状态 1=锁定 0=解除
    "key_switch":       0x02,  # 钥匙开关状态 1=锁定 0=解除
    "alert_flag":       0x04,  # 警惕标志 1=触发 0=复位
    "alert_release":    0x08,  # 警惕允许解除标志 1=允许 0=不允许
    "reserved_35_4":    0x10,  # 预留
    "reserved_35_5":    0x20,  # 预留
    "reserved_35_6":    0x40,  # 预留
    "reserved_35_7":    0x80,  # 预留
}

# 所有位定义按字节分组
PLC_BIT_GROUPS = {
    24: PLC_BIT_24_7_1,
    25: PLC_BIT_25,
    28: PLC_BIT_28,
    29: PLC_BIT_29,
    34: PLC_BIT_34,
    35: PLC_BIT_35,
}

# 外部照明开关状态枚举
LIGHT_SWITCH_MAP = {
    0: "停止",
    1: "自动",
    2: "近光",
    4: "远光",
}

# 门模式开关状态枚举
DOOR_MODE_MAP = {
    0: "半自动",
    1: "手动",
    2: "自动",
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


def _decode_bits_byte(byte_val: int, bit_map: dict) -> dict:
    """将单字节按位图解码为布尔值字典"""
    return {name: (byte_val & mask) != 0 for name, mask in bit_map.items()}


def _encode_bits_byte(bits: dict, bit_map: dict) -> int:
    """将布尔值字典按位图编码为单字节"""
    val = 0
    for name, mask in bit_map.items():
        if bits.get(name, False):
            val |= mask
    return val


def pack_plc_to_upper(
    # 时间
    year: int = 2025,
    month: int = 7,
    day: int = 16,
    hour: int = 15,
    minute: int = 11,
    second: int = 3,
    # 校验
    verify_type: int = 0,
    verify_code: int = 0,
    # 字节 24 标志 (指示灯)
    hscb: int = 0,
    brake_fault: int = 0,
    door_closed: int = 0,
    net_fault: int = 0,
    ar_available: int = 0,
    # 字节 25 标志 (模式)
    ato_available: int = 0,
    wash_mode: int = 0,
    ato_active: int = 0,
    ar_active: int = 0,
    # 车辆速度
    vehicle_speed: int = 0,
    # 字节 28 标志 (按钮)
    eb_button: int = 0,
    bus_ctrl: int = 0,
    forced_release: int = 0,
    forced_pump: int = 0,
    emergency_cmd: int = 0,
    parking_apply: int = 0,
    parking_release: int = 0,
    horn: int = 0,
    # 字节 29 标志 (门控)
    open_left_door: int = 0,
    open_right_door: int = 0,
    close_left_door: int = 0,
    close_right_door: int = 0,
    # 外部照明开关
    light_switch: int = 0,
    # 门模式开关
    door_mode_switch: int = 0,
    # 字节 34 标志
    high_accel: int = 0,
    cab_light: int = 0,
    mode_up_confirm: int = 0,
    mode_down_confirm: int = 0,
    confirm_flag: int = 0,
    ar_flag: int = 0,
    traction_reset: int = 0,
    ato_start: int = 0,
    # 字节 35 标志
    wash_switch: int = 0,
    key_switch: int = 0,
    alert_flag: int = 0,
    alert_release: int = 0,
    # 方向手柄 / 主手柄 / 极位
    dir_handle: int = 0,
    main_handle: int = 0,
    traction_level: int = 0,
    brake_level: int = 0,
) -> bytes:
    """
    打包 PLC -> 上位机 报文（46字节，大端序）

    协议定义见文档 7.1 节
    """
    data = bytearray(PLC_TO_UPPER_LEN)

    # 固定头（PLC 使用大端序）
    struct.pack_into(">I", data, 0, 0xAA55AA55)  # identify
    struct.pack_into(">H", data, 4, PLC_TO_UPPER_LEN)  # total_len
    struct.pack_into(">H", data, 6, 22)  # data_len

    # 时间
    struct.pack_into(">H", data, 8, year & 0xFFFF)
    struct.pack_into(">H", data, 10, month & 0xFFFF)
    struct.pack_into(">H", data, 12, day & 0xFFFF)
    struct.pack_into(">H", data, 14, hour & 0xFFFF)
    struct.pack_into(">H", data, 16, minute & 0xFFFF)
    struct.pack_into(">H", data, 18, second & 0xFFFF)

    # 校验
    struct.pack_into(">H", data, 20, verify_type & 0xFFFF)
    struct.pack_into(">H", data, 22, verify_code & 0xFFFF)

    # 字节 24-25 BOOL 标志（单字节，字节序无关）
    data[24] = _encode_bits_byte(
        {"hscb": hscb, "brake_fault": brake_fault, "door_closed": door_closed,
         "net_fault": net_fault, "ar_available": ar_available},
        PLC_BIT_24_7_1,
    )
    data[25] = _encode_bits_byte(
        {"ato_available": ato_available, "wash_mode": wash_mode,
         "ato_active": ato_active, "ar_active": ar_active},
        PLC_BIT_25,
    )

    # 车辆速度
    struct.pack_into(">H", data, 26, vehicle_speed & 0xFFFF)

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

    # 外部照明开关 / 门模式开关
    struct.pack_into(">H", data, 30, light_switch & 0xFFFF)
    struct.pack_into(">H", data, 32, door_mode_switch & 0xFFFF)

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

    # 方向手柄 / 主手柄 / 极位
    struct.pack_into(">H", data, 36, dir_handle & 0xFFFF)
    struct.pack_into(">H", data, 38, main_handle & 0xFFFF)
    struct.pack_into(">H", data, 40, traction_level & 0xFFFF)
    struct.pack_into(">H", data, 42, brake_level & 0xFFFF)

    # 字节 44-45: 预留
    return bytes(data)


def parse_plc_to_upper(data: bytes) -> dict:
    """
    解析 PLC -> 上位机 报文（46字节，大端序）

    协议定义见文档 7.1 节
    """
    if len(data) < PLC_TO_UPPER_LEN:
        raise ValueError(f"PLC报文长度不足: {len(data)} < {PLC_TO_UPPER_LEN}")

    identify = struct.unpack_from(">I", data, 0)[0]
    total_len = struct.unpack_from(">H", data, 4)[0]
    data_len = struct.unpack_from(">H", data, 6)[0]

    # 时间
    year = struct.unpack_from(">H", data, 8)[0]
    month = struct.unpack_from(">H", data, 10)[0]
    day = struct.unpack_from(">H", data, 12)[0]
    hour = struct.unpack_from(">H", data, 14)[0]
    minute = struct.unpack_from(">H", data, 16)[0]
    second = struct.unpack_from(">H", data, 18)[0]

    # 校验
    verify_type = struct.unpack_from(">H", data, 20)[0]
    verify_code = struct.unpack_from(">H", data, 22)[0]

    # BOOL 标志字节
    flags_24 = _decode_bits_byte(data[24], PLC_BIT_24_7_1)
    flags_25 = _decode_bits_byte(data[25], PLC_BIT_25)

    # 车辆速度 (WORD, 大端)
    vehicle_speed = struct.unpack_from(">H", data, 26)[0]

    flags_28 = _decode_bits_byte(data[28], PLC_BIT_28)
    flags_29 = _decode_bits_byte(data[29], PLC_BIT_29)

    # 外部照明开关 / 门模式开关
    light_switch = struct.unpack_from(">H", data, 30)[0]
    door_mode_switch = struct.unpack_from(">H", data, 32)[0]

    flags_34 = _decode_bits_byte(data[34], PLC_BIT_34)
    flags_35 = _decode_bits_byte(data[35], PLC_BIT_35)

    # 方向手柄 / 主手柄 / 极位
    dir_handle = struct.unpack_from(">H", data, 36)[0]
    main_handle = struct.unpack_from(">H", data, 38)[0]
    traction_level = struct.unpack_from(">H", data, 40)[0]
    brake_level = struct.unpack_from(">H", data, 42)[0]
    # 极位换算：1% = 256 (100% -> 25600)
    traction_level_pct = traction_level / 256.0
    brake_level_pct = brake_level / 256.0

    # 预留字节 44-45
    reserved = struct.unpack_from(">H", data, 44)[0]

    # 枚举映射
    light_str = LIGHT_SWITCH_MAP.get(light_switch, f"未知({light_switch})")
    door_mode_str = DOOR_MODE_MAP.get(door_mode_switch, f"未知({door_mode_switch})")
    dir_str = DIR_HANDLE_MAP.get(dir_handle, f"未知({dir_handle})")
    main_handle_str = MAIN_HANDLE_MAP.get(main_handle, f"未知({main_handle})")

    result = {
        # 固定头
        "identify": hex(identify),
        "identify_ok": identify == 0xAA55AA55,
        "total_len": total_len,
        "data_len": data_len,
        # 时间
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
        "timestamp_str": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}",
        # 校验
        "verify_type": verify_type,
        "verify_code": verify_code,
        # 指示灯标志 (字节24)
        "hscb": flags_24.get("hscb", False),           # 高断合指示灯
        "brake_fault_indicator": flags_24.get("brake_fault", False),
        "door_closed_indicator": flags_24.get("door_closed", False),
        "net_fault_indicator": flags_24.get("net_fault", False),
        "ar_available": flags_24.get("ar_available", False),
        # 模式标志 (字节25)
        "ato_available": flags_25.get("ato_available", False),
        "wash_mode": flags_25.get("wash_mode", False),
        "ato_active": flags_25.get("ato_active", False),
        "ar_active": flags_25.get("ar_active", False),
        # 车辆速度
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
        "light_switch_str": light_str,
        "door_mode_switch": door_mode_switch,
        "door_mode_switch_str": door_mode_str,
        # 按钮标志 (字节34)
        "high_accel": flags_34.get("high_accel", False),
        "cab_light": flags_34.get("cab_light", False),
        "mode_up_confirm": flags_34.get("mode_up_confirm", False),
        "mode_down_confirm": flags_34.get("mode_down_confirm", False),
        "confirm_flag": flags_34.get("confirm_flag", False),
        "ar_flag": flags_34.get("ar_flag", False),
        "traction_reset": flags_34.get("traction_reset", False),
        "ato_start_flag": flags_34.get("ato_start", False),
        # 开关标志 (字节35)
        "wash_switch": flags_35.get("wash_switch", False),
        "key_switch": flags_35.get("key_switch", False),
        "alert_flag": flags_35.get("alert_flag", False),
        "alert_release": flags_35.get("alert_release", False),
        # 手柄
        "dir_handle": dir_handle,
        "dir_handle_str": dir_str,
        "main_handle": main_handle,
        "main_handle_str": main_handle_str,
        # 极位
        "traction_level": traction_level,
        "traction_level_pct": round(traction_level_pct, 1),
        "brake_level": brake_level,
        "brake_level_pct": round(brake_level_pct, 1),
        # 预留
        "reserved": reserved,
        # 原始字节
        "raw": data[:PLC_TO_UPPER_LEN],
    }
    return result


def pack_upper_to_plc(
    # 时间
    year: int = 2025,
    month: int = 7,
    day: int = 16,
    hour: int = 15,
    minute: int = 11,
    second: int = 3,
    # 校验
    verify_type: int = 0,
    verify_code: int = 0,
    # 字节 24 标志 (指示灯，位4=开门灯)
    hscb: int = 0,
    brake_fault: int = 0,
    door_open_light: int = 0,
    door_closed: int = 0,
    net_fault: int = 0,
    ar_available: int = 0,
    # 字节 25 标志 (模式)
    ato_available: int = 0,
    wash_mode: int = 0,
    ato_active: int = 0,
    ar_active: int = 0,
    # 车辆速度
    vehicle_speed: int = 0,
) -> bytes:
    """
    打包 上位机 -> PLC 报文（28字节，小端序）

    协议定义见文档 7.2 节（PLC 使用小端序）
    """
    data = bytearray(UPPER_TO_PLC_LEN)

    # 固定头（PLC 使用小端序，见文档第4节）
    # 文档要求字节序列 55 AA 55 AA，小端下对应 uint32 = 0xAA55AA55
    struct.pack_into("<I", data, 0, 0xAA55AA55)  # identify (DWORD)
    struct.pack_into("<H", data, 4, UPPER_TO_PLC_LEN)  # total_len
    struct.pack_into("<H", data, 6, 2)  # data_len = 2（文档定义数据区=2字节）

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
    # 字节24: 使用7.2特定位定义（bit4=开门灯，不同于7.1的预留）
    data[24] = _encode_bits_byte(
        {"hscb": hscb, "brake_fault": brake_fault,
         "door_open_light": door_open_light,
         "door_closed": door_closed,
         "net_fault": net_fault, "ar_available": ar_available},
        PLC_BIT_24_7_2,
    )
    data[25] = _encode_bits_byte(
        {"ato_available": ato_available, "wash_mode": wash_mode,
         "ato_active": ato_active, "ar_active": ar_active},
        PLC_BIT_25,
    )

    # 车辆速度 (WORD, 小端)
    struct.pack_into("<H", data, 26, vehicle_speed & 0xFFFF)

    return bytes(data)


def parse_upper_to_plc(data: bytes) -> dict:
    """
    解析 上位机 -> PLC 报文（28字节，小端序）

    协议定义见文档 7.2 节（PLC 使用小端序）
    """
    if len(data) < UPPER_TO_PLC_LEN:
        raise ValueError(f"上位机报文长度不足: {len(data)} < {UPPER_TO_PLC_LEN}")

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
    flags_24 = _decode_bits_byte(data[24], PLC_BIT_24_7_2)
    flags_25 = _decode_bits_byte(data[25], PLC_BIT_25)

    # 车辆速度 (WORD, 小端)
    vehicle_speed = struct.unpack_from("<H", data, 26)[0]

    result = {
        # 固定头
        "identify": hex(identify),
        "identify_ok": identify == 0xAA55AA55,
        "total_len": total_len,
        "data_len": data_len,
        # 时间
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
        "second": second,
        "timestamp_str": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}",
        # 校验
        "verify_type": verify_type,
        "verify_code": verify_code,
        # 指示灯标志 (字节24)
        "hscb": flags_24.get("hscb", False),
        "brake_fault_indicator": flags_24.get("brake_fault", False),
        "door_open_light": flags_24.get("door_open_light", False),
        "door_closed_indicator": flags_24.get("door_closed", False),
        "net_fault_indicator": flags_24.get("net_fault", False),
        "ar_available": flags_24.get("ar_available", False),
        # 模式标志 (字节25)
        "ato_available": flags_25.get("ato_available", False),
        "wash_mode": flags_25.get("wash_mode", False),
        "ato_active": flags_25.get("ato_active", False),
        "ar_active": flags_25.get("ar_active", False),
        # 车辆速度
        "vehicle_speed": vehicle_speed,
        # 原始字节
        "raw": data[:UPPER_TO_PLC_LEN],
    }
    return result


# ====================================================================
# 网络屏协议编解码
# ====================================================================
# 文档定义：
#   - 上位机→网络屏：572字节（本文档 1.1 节）
#   - 网络屏→上位机：26字节（本文档"牵引切换请求"节）
# 字节序：文档未显式声明，采用小端序（与系统其他协议保持一致）

# ------------------- 内部辅助：6车数组读写 -------------------

_CAR_COUNT = 6  # 6节编组


def _pack_car_bytes(data: bytearray, offset: int, values: list, count: int):
    """将 count 个 BYTE 值写入 data[offset:offset+count]"""
    for i in range(min(len(values), count)):
        data[offset + i] = values[i] & 0xFF


def _pack_car_words(data: bytearray, offset: int, values: list, count: int):
    """将 count 个 WORD 值（小端）写入 data"""
    for i in range(min(len(values), count)):
        struct.pack_into("<H", data, offset + 2 * i, values[i] & 0xFFFF)


def _pack_car_dwords(data: bytearray, offset: int, values: list, count: int):
    """将 count 个 DWORD 值（小端）写入 data"""
    for i in range(min(len(values), count)):
        struct.pack_into("<I", data, offset + 4 * i, values[i] & 0xFFFFFFFF)


def _pack_car_floats(data: bytearray, offset: int, values: list, count: int):
    """将 count 个 FLOAT 值（小端）写入 data"""
    for i in range(min(len(values), count)):
        struct.pack_into("<f", data, offset + 4 * i, float(values[i]))


def _parse_car_bytes(data: bytes, offset: int, count: int) -> list:
    return [data[offset + i] for i in range(count)]


def _parse_car_words(data: bytes, offset: int, count: int) -> list:
    return [struct.unpack_from("<H", data, offset + 2 * i)[0] for i in range(count)]


def _parse_car_dwords(data: bytes, offset: int, count: int) -> list:
    return [struct.unpack_from("<I", data, offset + 4 * i)[0] for i in range(count)]


def _parse_car_floats(data: bytes, offset: int, count: int) -> list:
    return [struct.unpack_from("<f", data, offset + 4 * i)[0] for i in range(count)]


def _ensure_list(val, count: int, default=0):
    """确保 val 是长度为 count 的列表，不足用 default 填充"""
    if val is None:
        return [default] * count
    if len(val) >= count:
        return list(val)[:count]
    return list(val) + [default] * (count - len(val))


# ------------------- 上位机 → 网络屏 (572字节) -------------------

def pack_network_screen(
    # -- 报文头 --
    timestamp_ms: int = 0,
    verify_type: int = 0,
    verify_code: int = 0,
    protocol_id: int = 0,
    msg_id: int = 0,
    # -- 时间 --
    year: int = 2025,
    month: int = 1,
    day: int = 1,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    # -- 基础运行信息 --
    curr_station_id: int = 0,
    next_station_id: int = 0,
    end_station_id: int = 0,
    power_state: int = 0,       # 车间电源供电: 有(1)/无(0)
    speed: float = 0.0,         # FLOAT 速度
    acceleration: float = 0.0,  # FLOAT 加速度
    power_pull: int = 0,        # WORD 总牵引力
    net_pressure: int = 1500,   # WORD 网压（默认1500V）
    speed_limit: int = 0,       # WORD 限速
    level_pos: int = 0,         # BYTE 级位: 惰行(0)/牵引(1)/制动(2)/紧急(3)
    run_mode: int = 0,          # BYTE 低4位=手动/ATO, 高4位=门模式
    master_v: int = 0,          # WORD 母线电压
    run_dir: int = 0,           # BYTE 运行方向
    driver_room_state: int = 0, # BYTE 司机室状态 低4=tc1+高4=tc2
    # -- 6节车 数组字段 --
    door_state: list = None,           # DWORD[6]
    stop_pos_state: list = None,       # BYTE[6]
    fire_empty_run: list = None,       # BYTE[6]
    warm_empty_state1: list = None,    # BYTE[6]
    warm_empty_state2: list = None,    # BYTE[6]
    pull_switch: list = None,          # BYTE[6]
    charge: list = None,               # BYTE[6]
    assist_high_switch: list = None,   # BYTE[6]
    breaker_master: list = None,       # BYTE[6]
    elect_stop: list = None,           # WORD[6]
    wind_press: list = None,           # WORD[6]
    brake_pressure: list = None,       # WORD[6]
    usage_rate: list = None,           # BYTE[6]
    line_net: list = None,             # BYTE[6]
    temp: list = None,                 # FLOAT[6]
    pull_stream: list = None,          # BYTE[6]
    stop_im: list = None,              # BYTE[10]
    side_info: list = None,            # BYTE[6]
    braker_state: list = None,         # BYTE[11]
    line_and_elect_stop: list = None,  # BYTE[6]
    line_v: list = None,               # WORD[6]
    stop_state: list = None,           # BYTE[6]
    air_stop: list = None,             # WORD[6]
    empty_press1: list = None,         # WORD[6]
    empty_press2: list = None,         # WORD[6]
    b05_and_b19: list = None,          # BYTE[6]
    kma_and_elect_power: list = None,  # BYTE[6]
    ni_bian_input_v: list = None,      # WORD[6]
    ni_bian_output_v: list = None,     # WORD[6]
    charge_output_v: list = None,      # WORD[6]
    ni_bian_input_a: list = None,      # BYTE[6]
    ni_bian_output_a: list = None,     # BYTE[6]
    charge_output_a: list = None,      # BYTE[6]
    # -- 接触器/KM --
    tc1_km1: int = 0,       # BYTE
    tc1_km3: int = 0,
    tc1_km5: int = 0,
    tc2_km1: int = 0,
    tc2_km3: int = 0,
    tc2_km5: int = 0,
    # -- 蓄电池 TC1 --
    tc1_battle_remain: int = 0,     # WORD
    tc1_battle_v: int = 0,
    tc1_battle_charge_a: int = 0,
    tc1_battle_output_a: int = 0,
    tc1_battle_temp: int = 0,
    tc1_hi_v: int = 0,
    tc1_li_v: int = 0,
    tc1_hi_pos: int = 0,            # BYTE
    tc1_li_pos: int = 0,
    tc1_temp: int = 0,              # WORD
    tc2_temp: int = 0,
    tc1_temp_pos: int = 0,          # BYTE
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
    smoke_temp: list = None,         # DWORD[6]
    out_temp: list = None,           # FLOAT[6]
    inside_temp: list = None,        # FLOAT[6]
    air_cond_mode: list = None,      # BYTE[6]
    cold_wind: list = None,          # BYTE[6]
    wind_fan: list = None,           # BYTE[6]
    press_machine: list = None,      # WORD[6]
    big_wind: list = None,           # BYTE[6]
    machine11: list = None,          # BYTE[6]
    machine12: list = None,          # BYTE[6]
    machine21: list = None,          # BYTE[6]
    machine22: list = None,          # BYTE[6]
    # -- 网络设备 --
    tc1_net: list = None,            # WORD[2]
    tc2_net: list = None,            # WORD[2]
    tc3_net: list = None,            # BYTE[2]
    tc4_net: list = None,            # BYTE[2]
    tc5_net: list = None,            # BYTE[2]
    tc6_net: list = None,            # BYTE[2]
    conn_ab: int = 0,                # BYTE
    tc1_devs_state: int = 0,         # WORD
    tc2_devs_state: int = 0,
    tc3_devs_state: int = 0,         # BYTE
    tc4_devs_state: int = 0,
    tc5_devs_state: int = 0,
    tc6_devs_state: int = 0,
    econn_dev_state: int = 0,        # BYTE
    econn_dev_state2: int = 0,
    fault_code: int = 0,             # WORD
    train_no: int = 1,               # WORD 列车号
) -> bytes:
    """
    打包 上位机 → 网络屏 显示数据（572字节）

    协议定义见文档「司机驾驶模拟台网络屏协议」1.1 节
    所有字段采用小端字节序
    """
    off = NETWORK_SCREEN_OFFSET
    data = bytearray(NETWORK_SCREEN_LEN)

    # -- 报文头 (24字节) --
    struct.pack_into("<I", data, off["identify"], 0x55AA55AA)
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

    # -- 6节车 BYTE[6] 数组 --
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
    struct.pack_into("<H", data, off["tc1_battle_remain"], tc1_battle_remain & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_battle_v"], tc1_battle_v & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_battle_charge_a"], tc1_battle_charge_a & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_battle_output_a"], tc1_battle_output_a & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_battle_temp"], tc1_battle_temp & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_hi_v"], tc1_hi_v & 0xFFFF)
    struct.pack_into("<H", data, off["tc1_li_v"], tc1_li_v & 0xFFFF)
    data[off["tc1_hi_pos"]] = tc1_hi_pos & 0xFF
    data[off["tc1_li_pos"]] = tc1_li_pos & 0xFF
    struct.pack_into("<H", data, off["tc1_temp"], tc1_temp & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_temp"], tc2_temp & 0xFFFF)
    data[off["tc1_temp_pos"]] = tc1_temp_pos & 0xFF
    data[off["tc2_temp_pos"]] = tc2_temp_pos & 0xFF

    # -- 蓄电池 TC2 --
    struct.pack_into("<H", data, off["tc2_battle_remain"], tc2_battle_remain & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_battle_v"], tc2_battle_v & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_battle_charge_a"], tc2_battle_charge_a & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_battle_output_a"], tc2_battle_output_a & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_battle_temp"], tc2_battle_temp & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_hi_v"], tc2_hi_v & 0xFFFF)
    struct.pack_into("<H", data, off["tc2_li_v"], tc2_li_v & 0xFFFF)
    data[off["tc2_hi_pos"]] = tc2_hi_pos & 0xFF
    data[off["tc2_li_pos"]] = tc2_li_pos & 0xFF

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


def parse_network_screen(data: bytes) -> dict:
    """
    解析 上位机 → 网络屏 显示数据（572字节）

    协议定义见文档「司机驾驶模拟台网络屏协议」1.1 节
    """
    if len(data) < NETWORK_SCREEN_LEN:
        raise ValueError(f"网络屏报文长度不足: {len(data)} < {NETWORK_SCREEN_LEN}")

    off = NETWORK_SCREEN_OFFSET

    identify = struct.unpack_from("<I", data, off["identify"])[0]
    total_len = struct.unpack_from("<H", data, off["total_len"])[0]
    data_len = struct.unpack_from("<H", data, off["data_len"])[0]

    result = {
        # 报文头
        "identify": f"0x{identify:08X}",
        "identify_ok": identify == 0x55AA55AA,
        "total_len": total_len,
        "data_len": data_len,
        "timestamp_ms": struct.unpack_from("<Q", data, off["timestamp"])[0],
        "verify_type": struct.unpack_from("<H", data, off["verify_type"])[0],
        "verify_code": struct.unpack_from("<H", data, off["verify_code"])[0],
        "protocol_id": struct.unpack_from("<H", data, off["protocol_id"])[0],
        "msg_id": struct.unpack_from("<H", data, off["msg_id"])[0],
        # 时间
        "year": struct.unpack_from("<H", data, off["year"])[0],
        "month": struct.unpack_from("<H", data, off["month"])[0],
        "day": struct.unpack_from("<H", data, off["day"])[0],
        "hour": struct.unpack_from("<H", data, off["hour"])[0],
        "minute": struct.unpack_from("<H", data, off["minute"])[0],
        "second": struct.unpack_from("<H", data, off["second"])[0],
        "timestamp_str": (
            f"{struct.unpack_from('<H', data, off['year'])[0]:04d}-"
            f"{struct.unpack_from('<H', data, off['month'])[0]:02d}-"
            f"{struct.unpack_from('<H', data, off['day'])[0]:02d} "
            f"{struct.unpack_from('<H', data, off['hour'])[0]:02d}:"
            f"{struct.unpack_from('<H', data, off['minute'])[0]:02d}:"
            f"{struct.unpack_from('<H', data, off['second'])[0]:02d}"
        ),
        # 基础运行信息
        "curr_station_id": data[off["curr_station_id"]],
        "next_station_id": data[off["next_station_id"]],
        "end_station_id": data[off["end_station_id"]],
        "power_state": data[off["power_state"]],
        "speed": struct.unpack_from("<f", data, off["speed"])[0],
        "acceleration": struct.unpack_from("<f", data, off["acceleration"])[0],
        "power_pull": struct.unpack_from("<H", data, off["power_pull"])[0],
        "net_pressure": struct.unpack_from("<H", data, off["net_pressure"])[0],
        "speed_limit": struct.unpack_from("<H", data, off["speed_limit"])[0],
        "level_pos": data[off["level_pos"]],
        "level_pos_str": {0: "惰行", 1: "牵引", 2: "制动", 3: "紧急制动"}.get(
            data[off["level_pos"]], f"未知({data[off['level_pos']]})"),
        "run_mode": data[off["run_mode"]],
        "run_mode_manual_ato": "ATO" if (data[off["run_mode"]] & 0x0F) == 1 else "手动",
        "run_mode_door": {0: "MM", 1: "AM", 2: "AA"}.get(
            (data[off["run_mode"]] >> 4) & 0x0F, "未知"),
        "master_v": struct.unpack_from("<H", data, off["master_v"])[0],
        "run_dir": data[off["run_dir"]],
        "run_dir_str": {0: "无", 1: "左", 2: "右", 0xff: "未知"}.get(
            data[off["run_dir"]], f"未知({data[off['run_dir']]})"),
        "driver_room_state": data[off["driver_room_state"]],
        "driver_room_tc1": "激活" if (data[off["driver_room_state"]] & 0x0F) == 1 else "未激活",
        "driver_room_tc2": "激活" if ((data[off["driver_room_state"]] >> 4) & 0x0F) == 1 else "未激活",
        # 6节车数据
        "door_state": _parse_car_dwords(data, off["door_state"], _CAR_COUNT),
        "stop_pos_state": _parse_car_bytes(data, off["stop_pos_state"], _CAR_COUNT),
        "fire_empty_run": _parse_car_bytes(data, off["fire_empty_run"], _CAR_COUNT),
        "warm_empty_state1": _parse_car_bytes(data, off["warm_empty_state1"], _CAR_COUNT),
        "warm_empty_state2": _parse_car_bytes(data, off["warm_empty_state2"], _CAR_COUNT),
        "pull_switch": _parse_car_bytes(data, off["pull_switch"], _CAR_COUNT),
        "charge": _parse_car_bytes(data, off["charge"], _CAR_COUNT),
        "assist_high_switch": _parse_car_bytes(data, off["assist_high_switch"], _CAR_COUNT),
        "breaker_master": _parse_car_bytes(data, off["breaker_master"], _CAR_COUNT),
        "elect_stop": _parse_car_words(data, off["elect_stop"], _CAR_COUNT),
        "wind_press": _parse_car_words(data, off["wind_press"], _CAR_COUNT),
        "brake_pressure": _parse_car_words(data, off["brake_pressure"], _CAR_COUNT),
        "usage_rate": _parse_car_bytes(data, off["usage_rate"], _CAR_COUNT),
        "line_net": _parse_car_bytes(data, off["line_net"], _CAR_COUNT),
        "temp": [round(v, 1) for v in _parse_car_floats(data, off["temp"], _CAR_COUNT)],
        "pull_stream": _parse_car_bytes(data, off["pull_stream"], _CAR_COUNT),
        "stop_im": _parse_car_bytes(data, off["stop_im"], 10),
        "side_info": _parse_car_bytes(data, off["side_info"], _CAR_COUNT),
        "braker_state": _parse_car_bytes(data, off["braker_state"], 11),
        "line_and_elect_stop": _parse_car_bytes(data, off["line_and_elect_stop"], _CAR_COUNT),
        "line_v": _parse_car_words(data, off["line_v"], _CAR_COUNT),
        "stop_state": _parse_car_bytes(data, off["stop_state"], _CAR_COUNT),
        "air_stop": _parse_car_words(data, off["air_stop"], _CAR_COUNT),
        "empty_press1": _parse_car_words(data, off["empty_press1"], _CAR_COUNT),
        "empty_press2": _parse_car_words(data, off["empty_press2"], _CAR_COUNT),
        "b05_and_b19": _parse_car_bytes(data, off["b05_and_b19"], _CAR_COUNT),
        "kma_and_elect_power": _parse_car_bytes(data, off["kma_and_elect_power"], _CAR_COUNT),
        "ni_bian_input_v": _parse_car_words(data, off["ni_bian_input_v"], _CAR_COUNT),
        "ni_bian_output_v": _parse_car_words(data, off["ni_bian_output_v"], _CAR_COUNT),
        "charge_output_v": _parse_car_words(data, off["charge_output_v"], _CAR_COUNT),
        "ni_bian_input_a": _parse_car_bytes(data, off["ni_bian_input_a"], _CAR_COUNT),
        "ni_bian_output_a": _parse_car_bytes(data, off["ni_bian_output_a"], _CAR_COUNT),
        "charge_output_a": _parse_car_bytes(data, off["charge_output_a"], _CAR_COUNT),
        # 接触器/KM
        "tc1_km1": data[off["tc1_km1"]],
        "tc1_km3": data[off["tc1_km3"]],
        "tc1_km5": data[off["tc1_km5"]],
        "tc2_km1": data[off["tc2_km1"]],
        "tc2_km3": data[off["tc2_km3"]],
        "tc2_km5": data[off["tc2_km5"]],
        # 蓄电池 TC1
        "tc1_battle_remain": struct.unpack_from("<H", data, off["tc1_battle_remain"])[0],
        "tc1_battle_v": struct.unpack_from("<H", data, off["tc1_battle_v"])[0],
        "tc1_battle_charge_a": struct.unpack_from("<H", data, off["tc1_battle_charge_a"])[0],
        "tc1_battle_output_a": struct.unpack_from("<H", data, off["tc1_battle_output_a"])[0],
        "tc1_battle_temp": struct.unpack_from("<H", data, off["tc1_battle_temp"])[0],
        "tc1_hi_v": struct.unpack_from("<H", data, off["tc1_hi_v"])[0],
        "tc1_li_v": struct.unpack_from("<H", data, off["tc1_li_v"])[0],
        "tc1_hi_pos": data[off["tc1_hi_pos"]],
        "tc1_li_pos": data[off["tc1_li_pos"]],
        "tc1_temp": struct.unpack_from("<H", data, off["tc1_temp"])[0],
        "tc2_temp": struct.unpack_from("<H", data, off["tc2_temp"])[0],
        "tc1_temp_pos": data[off["tc1_temp_pos"]],
        "tc2_temp_pos": data[off["tc2_temp_pos"]],
        # 蓄电池 TC2
        "tc2_battle_remain": struct.unpack_from("<H", data, off["tc2_battle_remain"])[0],
        "tc2_battle_v": struct.unpack_from("<H", data, off["tc2_battle_v"])[0],
        "tc2_battle_charge_a": struct.unpack_from("<H", data, off["tc2_battle_charge_a"])[0],
        "tc2_battle_output_a": struct.unpack_from("<H", data, off["tc2_battle_output_a"])[0],
        "tc2_battle_temp": struct.unpack_from("<H", data, off["tc2_battle_temp"])[0],
        "tc2_hi_v": struct.unpack_from("<H", data, off["tc2_hi_v"])[0],
        "tc2_li_v": struct.unpack_from("<H", data, off["tc2_li_v"])[0],
        "tc2_hi_pos": data[off["tc2_hi_pos"]],
        "tc2_li_pos": data[off["tc2_li_pos"]],
        # 烟火/空调
        "smoke_temp": _parse_car_dwords(data, off["smoke_temp"], _CAR_COUNT),
        "out_temp": [round(v, 1) for v in _parse_car_floats(data, off["out_temp"], _CAR_COUNT)],
        "inside_temp": [round(v, 1) for v in _parse_car_floats(data, off["inside_temp"], _CAR_COUNT)],
        "air_cond_mode": _parse_car_bytes(data, off["air_cond_mode"], _CAR_COUNT),
        "cold_wind": _parse_car_bytes(data, off["cold_wind"], _CAR_COUNT),
        "wind_fan": _parse_car_bytes(data, off["wind_fan"], _CAR_COUNT),
        "press_machine": _parse_car_words(data, off["press_machine"], _CAR_COUNT),
        "big_wind": _parse_car_bytes(data, off["big_wind"], _CAR_COUNT),
        "machine11": _parse_car_bytes(data, off["machine11"], _CAR_COUNT),
        "machine12": _parse_car_bytes(data, off["machine12"], _CAR_COUNT),
        "machine21": _parse_car_bytes(data, off["machine21"], _CAR_COUNT),
        "machine22": _parse_car_bytes(data, off["machine22"], _CAR_COUNT),
        # 网络设备
        "tc1_net": _parse_car_words(data, off["tc1_net"], 2),
        "tc2_net": _parse_car_words(data, off["tc2_net"], 2),
        "tc3_net": _parse_car_bytes(data, off["tc3_net"], 2),
        "tc4_net": _parse_car_bytes(data, off["tc4_net"], 2),
        "tc5_net": _parse_car_bytes(data, off["tc5_net"], 2),
        "tc6_net": _parse_car_bytes(data, off["tc6_net"], 2),
        "conn_ab": data[off["conn_ab"]],
        "tc1_devs_state": struct.unpack_from("<H", data, off["tc1_devs_state"])[0],
        "tc2_devs_state": struct.unpack_from("<H", data, off["tc2_devs_state"])[0],
        "tc3_devs_state": data[off["tc3_devs_state"]],
        "tc4_devs_state": data[off["tc4_devs_state"]],
        "tc5_devs_state": data[off["tc5_devs_state"]],
        "tc6_devs_state": data[off["tc6_devs_state"]],
        "econn_dev_state": data[off["econn_dev_state"]],
        "econn_dev_state2": data[off["econn_dev_state2"]],
        "fault_code": struct.unpack_from("<H", data, off["fault_code"])[0],
        "train_no": struct.unpack_from("<H", data, off["train_no"])[0],
        # 原始字节
        "raw": data[:NETWORK_SCREEN_LEN],
    }
    return result


# ------------------- 网络屏 → 上位机 (26字节, 牵引切除请求) -------------------

def parse_network_screen_request(data: bytes) -> dict:
    """
    解析 网络屏 → 上位机 牵引切除请求报文（26字节）

    协议定义见文档「司机驾驶模拟台网络屏协议」第二节
    """
    if len(data) < NETWORK_SCREEN_REQUEST_LEN:
        raise ValueError(
            f"网络屏请求报文长度不足: {len(data)} < {NETWORK_SCREEN_REQUEST_LEN}"
        )

    off = NETWORK_SCREEN_REQUEST_OFFSET

    identify = struct.unpack_from("<I", data, off["identify"])[0]
    total_len = struct.unpack_from("<H", data, off["total_len"])[0]
    data_len = struct.unpack_from("<H", data, off["data_len"])[0]
    timestamp_ms = struct.unpack_from("<Q", data, off["timestamp"])[0]

    pull_ctrl = data[off["pull_ctrl"]]

    # 解析 Bit0-Bit5 分别对应 1-6 车的牵引切除
    pull_cut = {}
    for car in range(6):
        pull_cut[f"car_{car + 1}"] = (pull_ctrl >> car) & 1 == 1

    return {
        "identify": f"0x{identify:08X}",
        "identify_ok": identify == 0x55AA55AA,
        "total_len": total_len,
        "data_len": data_len,
        "timestamp_ms": timestamp_ms,
        "verify_type": struct.unpack_from("<H", data, off["verify_type"])[0],
        "verify_code": struct.unpack_from("<H", data, off["verify_code"])[0],
        "protocol_id": struct.unpack_from("<H", data, off["protocol_id"])[0],
        "msg_id": struct.unpack_from("<H", data, off["msg_id"])[0],
        "pull_ctrl": pull_ctrl,
        "pull_cut": pull_cut,
        "reserve": data[off["reserve"]],
        "raw": data[:NETWORK_SCREEN_REQUEST_LEN],
    }


def pack_network_screen_response(
    # 复用 572字节 下行报文作为反馈（或使用简化确认包）
    # 文档未单独定义反馈格式，实际反馈通过上位机→网络屏 572B 报文中的牵引切除状态体现
    # 此函数保留占位，具体反馈方式待与硬件方确认
    success: bool = True,
    pull_cut_state: int = 0,
) -> bytes:
    """
    打包 上位机 → 网络屏 牵引切除反馈（暂用26字节确认包）

    注意：文档未明确定义牵引切除反馈的报文格式。
    此实现发送一个简化确认包，实际格式待硬件联调确认。
    """
    off = NETWORK_SCREEN_REQUEST_OFFSET
    data = bytearray(NETWORK_SCREEN_REQUEST_LEN)

    struct.pack_into("<I", data, off["identify"], 0x55AA55AA)
    struct.pack_into("<H", data, off["total_len"], NETWORK_SCREEN_REQUEST_LEN)
    struct.pack_into("<H", data, off["data_len"], 2)
    struct.pack_into("<Q", data, off["timestamp"], 0)
    struct.pack_into("<H", data, off["verify_type"], 0)
    struct.pack_into("<H", data, off["verify_code"], 0)
    struct.pack_into("<H", data, off["protocol_id"], 0)
    struct.pack_into("<H", data, off["msg_id"], 0)
    data[off["pull_ctrl"]] = pull_cut_state & 0xFF
    data[off["reserve"]] = 0

    return bytes(data)


# ====================================================================
# 信号屏协议编解码（66字节）
# ====================================================================

def pack_signal_screen(
    train_id: int = 1,
    current_speed_cm_s: int = 0,
    permit_speed_cm_s: int = 0,
    eb_trigger_speed_cm_s: int = 0,
    target_speed_cm_s: int = 0,
    target_distance_cm: int = 0,
    speed_change_distance_cm: int = 0,
    current_mode: int = 0,
    max_mode: int = 0,
    run_level: int = 0,
    signal_aspect: int = 0,
    next_signal_id: int = 0,
    dmi_display: int = 1,
) -> bytes:
    """
    打包信号屏（DMI）显示数据（66字节）

    参考 ATP -> DMI 应用数据包格式
    """
    data = bytearray(SIGNAL_SCREEN_LEN)

    # 0-1: 报文头
    struct.pack_into("<H", data, 0, 0xAA55)

    # 2-3: 报文长度
    struct.pack_into("<H", data, 2, SIGNAL_SCREEN_LEN)

    # 4: DMI显示状态
    data[4] = dmi_display & 0xFF

    # 5-6: 当前速度 (cm/s)
    struct.pack_into("<H", data, 5, current_speed_cm_s & 0xFFFF)

    # 7-8: 允许速度 (cm/s)
    struct.pack_into("<H", data, 7, permit_speed_cm_s & 0xFFFF)

    # 9-10: 紧急制动触发速度 (cm/s)
    struct.pack_into("<H", data, 9, eb_trigger_speed_cm_s & 0xFFFF)

    # 11-12: 目标速度 (cm/s)
    struct.pack_into("<H", data, 11, target_speed_cm_s & 0xFFFF)

    # 13-15: 限速变化点距离 (cm, 24bit)
    data[13] = (speed_change_distance_cm >> 16) & 0xFF
    data[14] = (speed_change_distance_cm >> 8) & 0xFF
    data[15] = speed_change_distance_cm & 0xFF

    # 16-18: 目标距离 (cm, 24bit)
    data[16] = (target_distance_cm >> 16) & 0xFF
    data[17] = (target_distance_cm >> 8) & 0xFF
    data[18] = target_distance_cm & 0xFF

    # 19: 当前驾驶模式
    data[19] = current_mode & 0x0F

    # 20: 最大可用驾驶模式
    data[20] = max_mode & 0x0F

    # 21: 运行等级
    data[21] = run_level & 0x0F

    # 22-25: 列车ID
    struct.pack_into("<I", data, 22, train_id & 0xFFFFFFFF)

    # 26: 信号机显示
    data[26] = signal_aspect & 0xFF

    # 27-28: 下一架信号机ID
    struct.pack_into("<H", data, 27, next_signal_id & 0xFFFF)

    # 29-65: 预留
    return bytes(data)


def parse_signal_screen(data: bytes) -> dict:
    """
    解析信号屏（DMI）数据（66字节）
    """
    if len(data) < SIGNAL_SCREEN_LEN:
        raise ValueError(f"信号屏报文长度不足: {len(data)} < {SIGNAL_SCREEN_LEN}")

    header = struct.unpack_from("<H", data, 0)[0]
    pkt_len = struct.unpack_from("<H", data, 2)[0]
    dmi_display = data[4]
    current_speed = struct.unpack_from("<H", data, 5)[0]
    permit_speed = struct.unpack_from("<H", data, 7)[0]
    eb_speed = struct.unpack_from("<H", data, 9)[0]
    target_speed = struct.unpack_from("<H", data, 11)[0]
    speed_change_dist = (data[13] << 16) | (data[14] << 8) | data[15]
    target_dist = (data[16] << 16) | (data[17] << 8) | data[18]
    current_mode = data[19] & 0x0F
    max_mode = data[20] & 0x0F
    run_level = data[21] & 0x0F
    train_id = struct.unpack_from("<I", data, 22)[0]
    signal_aspect = data[26]
    next_signal_id = struct.unpack_from("<H", data, 27)[0]

    mode_map = {0: "INIT", 2: "RD", 3: "RM", 4: "CM", 5: "AM",
                6: "AR", 7: "EUM", 8: "CAM", 9: "FAM"}

    return {
        "header": hex(header),
        "length": pkt_len,
        "dmi_display": dmi_display,
        "current_speed_cm_s": current_speed,
        "current_speed_km_h": current_speed / 100.0,
        "permit_speed_cm_s": permit_speed,
        "permit_speed_km_h": permit_speed / 100.0,
        "eb_trigger_speed_cm_s": eb_speed,
        "eb_trigger_speed_km_h": eb_speed / 100.0,
        "target_speed_cm_s": target_speed,
        "target_speed_km_h": target_speed / 100.0,
        "speed_change_distance_m": speed_change_dist / 100.0,
        "target_distance_m": target_dist / 100.0,
        "current_mode": mode_map.get(current_mode, f"UNKNOWN({current_mode})"),
        "max_mode": max_mode,
        "run_level": run_level,
        "train_id": train_id,
        "signal_aspect": hex(signal_aspect),
        "next_signal_id": next_signal_id,
    }


# ====================================================================
# 信号系统 UDP 报文编解码
# ====================================================================

def pack_signal_to_db_train_data(trains: list) -> bytes:
    """
    打包 信号系统 -> 总控数据库节点 列车数据报文

    Args:
        trains: 列车信息列表，每项为 dict:
            - train_id: int
            - speed_cm_s: int
            - distance_cm: int
            - direction: int (0x55 上行, 0xAA 下行)
            - load_kg: int
            - fault_speed: int (故障限速)
            - eb_status: int (0/1)
            - traction_avail: int
            - brake_avail: int
    """
    n = len(trains)
    if n == 0:
        return b""

    content_len = n * 18  # 单列车18字节
    packet_len = 2 + content_len  # 数据长度字段+CONTENT

    data = bytearray(14 + packet_len)  # 固定头14字节 + 数据长度(2) + content

    # 报文头
    data[0] = 0xFF
    data[1] = 0xF0
    # 源标识（信号系统）
    data[2:10] = b"\x00\x10\x00\x10\x00\x10\x00\x10"
    # 目的标识（总控数据库）
    data[10:14] = b"\x01\x00\x01\x00"

    # 数据长度
    struct.pack_into("<H", data, 14, content_len)

    offset = 16
    for t in trains:
        struct.pack_into("<B", data, offset, t["train_id"] & 0xFF)
        struct.pack_into("<I", data, offset + 1, t["speed_cm_s"] & 0xFFFFFFFF)
        struct.pack_into("<I", data, offset + 5, t["distance_cm"] & 0xFFFFFFFF)
        data[offset + 9] = t.get("direction", 0x55) & 0xFF
        struct.pack_into("<I", data, offset + 10, t["load_kg"] & 0xFFFFFFFF)
        data[offset + 14] = t.get("fault_speed", 0) & 0xFF
        data[offset + 15] = t.get("eb_status", 0) & 0xFF
        data[offset + 16] = t.get("traction_avail", 1) & 0xFF
        data[offset + 17] = t.get("brake_avail", 1) & 0xFF
        offset += 18

    return bytes(data)


def pack_signal_to_db_cab_binary(
    train_id: int = 1,
    atp_safe_output: int = 0,
    atp_nonsafe_output: int = 0,
    ato_nonsafe_output: int = 0,
    vehicle_output: int = 0,
) -> bytes:
    """
    打包 信号系统 -> 总控数据库节点 驾驶台开关量信息

    报文头：0xff 0xf1
    """
    data = bytearray(33)  # 14头 + 2数据长度 + 1列车ID + 4*4输出

    # 报文头
    data[0] = 0xFF
    data[1] = 0xF1
    # 源标识（信号系统）
    data[2:10] = b"\x00\x10\x00\x10\x00\x10\x00\x10"
    # 目的标识（总控数据库）
    data[10:14] = b"\x01\x00\x01\x00"

    # 数据长度 (2+1+16=19)
    struct.pack_into("<H", data, 14, 19)

    # CONTENT
    data[16] = train_id & 0xFF
    struct.pack_into("<I", data, 17, atp_safe_output & 0xFFFFFFFF)
    struct.pack_into("<I", data, 21, atp_nonsafe_output & 0xFFFFFFFF)
    struct.pack_into("<I", data, 25, ato_nonsafe_output & 0xFFFFFFFF)
    struct.pack_into("<I", data, 29, vehicle_output & 0xFFFFFFFF)

    return bytes(data)


def parse_signal_to_db_cab_binary(data: bytes) -> dict:
    """
    解析 信号系统 -> 总控数据库节点 驾驶台开关量信息
    """
    if len(data) < 33:
        raise ValueError(f"驾驶台开关量报文长度不足: {len(data)}")

    result = {
        "header": (data[0], data[1]),
        "train_id": data[16],
        "atp_safe_output": struct.unpack_from("<I", data, 17)[0],
        "atp_nonsafe_output": struct.unpack_from("<I", data, 21)[0],
        "ato_nonsafe_output": struct.unpack_from("<I", data, 25)[0],
        "vehicle_output": struct.unpack_from("<I", data, 29)[0],
    }

    # 解码比特位
    result["atp_safe_bits"] = _decode_bits(result["atp_safe_output"], ATP_SAFE_OUTPUT)
    result["atp_nonsafe_bits"] = _decode_bits(result["atp_nonsafe_output"], ATP_NONSAFE_OUTPUT)
    result["ato_nonsafe_bits"] = _decode_bits(result["ato_nonsafe_output"], ATO_NONSAFE_OUTPUT)

    return result


def pack_db_to_signal_train_data(trains: list) -> bytes:
    """
    打包 总控数据库节点 -> 信号系统 列车数据报文

    报文头：0xff 0xf0
    单列车18字节，单包最多40列车
    """
    n = min(len(trains), 40)
    if n == 0:
        return b""

    content_len = n * 18
    data = bytearray(16 + content_len)

    # 报文头
    data[0] = 0xFF
    data[1] = 0xF0
    # 源标识（总控数据库）
    data[2:10] = b"\x01\x00\x01\x00\x01\x00\x01\x00"
    # 目的标识（信号系统）
    data[10:14] = b"\x00\x10\x00\x10"

    # 数据长度
    struct.pack_into("<H", data, 14, content_len)

    offset = 16
    for t in trains:
        data[offset] = t["train_id"] & 0xFF
        struct.pack_into("<I", data, offset + 1, t["speed_cm_s"] & 0xFFFFFFFF)
        struct.pack_into("<I", data, offset + 5, t["distance_cm"] & 0xFFFFFFFF)
        data[offset + 9] = t.get("direction", 0x55) & 0xFF
        struct.pack_into("<I", data, offset + 10, t["load_kg"] & 0xFFFFFFFF)
        data[offset + 14] = t.get("fault_speed", 0) & 0xFF
        data[offset + 15] = t.get("eb_status", 0) & 0xFF
        data[offset + 16] = t.get("traction_avail", 1) & 0xFF
        data[offset + 17] = t.get("brake_avail", 1) & 0xFF
        offset += 18

    return bytes(data)


def parse_db_to_signal_train_data(data: bytes) -> dict:
    """
    解析 总控数据库节点 -> 信号系统 列车数据报文
    """
    if len(data) < 16:
        raise ValueError(f"总控->信号报文长度不足: {len(data)}")

    content_len = struct.unpack_from("<H", data, 14)[0]
    n = content_len // 18

    trains = []
    offset = 16
    for _ in range(n):
        if offset + 18 > len(data):
            break
        train = {
            "train_id": data[offset],
            "speed_cm_s": struct.unpack_from("<I", data, offset + 1)[0],
            "distance_cm": struct.unpack_from("<I", data, offset + 5)[0],
            "direction": data[offset + 9],
            "load_kg": struct.unpack_from("<I", data, offset + 10)[0],
            "fault_speed": data[offset + 14],
            "eb_status": data[offset + 15],
            "traction_avail": data[offset + 16],
            "brake_avail": data[offset + 17],
        }
        train["direction_str"] = "上行" if train["direction"] == 0x55 else "下行" if train["direction"] == 0xAA else "无效"
        trains.append(train)
        offset += 18

    return {
        "header": (data[0], data[1]),
        "train_count": n,
        "trains": trains,
    }


def pack_db_to_signal_cab_binary(
    train_id: int = 1,
    atp_safe_input: int = 0,
    atp_nonsafe_input: int = 0,
    ato_nonsafe_input: int = 0,
) -> bytes:
    """
    打包 总控数据库节点 -> 信号系统 驾驶台开关量信息（仅1车）

    报文头：0xff 0xf1
    """
    data = bytearray(29)

    data[0] = 0xFF
    data[1] = 0xF1
    data[2:10] = b"\x01\x00\x01\x00\x01\x00\x01\x00"
    data[10:14] = b"\x00\x10\x00\x10"

    # 数据长度 (2+1+12=15)
    struct.pack_into("<H", data, 14, 15)

    # CONTENT
    data[16] = train_id & 0xFF
    struct.pack_into("<I", data, 17, atp_safe_input & 0xFFFFFFFF)
    struct.pack_into("<I", data, 21, atp_nonsafe_input & 0xFFFFFFFF)
    struct.pack_into("<I", data, 25, ato_nonsafe_input & 0xFFFFFFFF)

    return bytes(data)


def parse_db_to_signal_cab_binary(data: bytes) -> dict:
    """
    解析 总控数据库节点 -> 信号系统 驾驶台开关量信息
    """
    if len(data) < 29:
        raise ValueError(f"驾驶台开关量报文长度不足: {len(data)}")

    result = {
        "header": (data[0], data[1]),
        "train_id": data[16],
        "atp_safe_input": struct.unpack_from("<I", data, 17)[0],
        "atp_nonsafe_input": struct.unpack_from("<I", data, 21)[0],
        "ato_nonsafe_input": struct.unpack_from("<I", data, 25)[0],
    }

    # 解码比特位
    result["atp_safe_bits"] = _decode_bits(result["atp_safe_input"], ATP_SAFE_INPUT)
    result["atp_nonsafe_bits"] = _decode_bits(result["atp_nonsafe_input"], ATP_NONSAFE_INPUT)
    result["ato_nonsafe_bits"] = _decode_bits(result["ato_nonsafe_input"], ATO_NONSAFE_INPUT)

    return result


# ====================================================================
# 辅助函数
# ====================================================================

def _decode_bits(value: int, bit_map: dict) -> dict:
    """将 UINT32 按位图字典解码为布尔值"""
    return {name: (value & mask) != 0 for name, mask in bit_map.items()}


def _encode_bits(bits: dict, bit_map: dict) -> int:
    """将布尔值字典按位图编码为 UINT32"""
    value = 0
    for name, mask in bit_map.items():
        if bits.get(name, False):
            value |= mask
    return value


def encode_atp_safe_input(bits: dict) -> int:
    """编码 ATP安全输入 UINT32"""
    return _encode_bits(bits, ATP_SAFE_INPUT)


def encode_atp_nonsafe_input(bits: dict) -> int:
    """编码 ATP非安全输入 UINT32"""
    return _encode_bits(bits, ATP_NONSAFE_INPUT)


def encode_ato_nonsafe_input(bits: dict) -> int:
    """编码 ATO非安全输入 UINT32"""
    return _encode_bits(bits, ATO_NONSAFE_INPUT)


def encode_atp_safe_output(bits: dict) -> int:
    """编码 ATP安全输出 UINT32"""
    return _encode_bits(bits, ATP_SAFE_OUTPUT)


def encode_atp_nonsafe_output(bits: dict) -> int:
    """编码 ATP非安全输出 UINT32"""
    return _encode_bits(bits, ATP_NONSAFE_OUTPUT)


def encode_ato_nonsafe_output(bits: dict) -> int:
    """编码 ATO非安全输出 UINT32"""
    return _encode_bits(bits, ATO_NONSAFE_OUTPUT)


# ====================================================================
# 自检
# ====================================================================
def self_test():
    """运行协议编解码自检"""
    print("=" * 60)
    print("协议编解码自检")
    print("=" * 60)

    # 1. PLC -> 上位机 (文档 7.1 节 46字节大端序)
    print("\n[1] PLC -> 上位机 编解码 (文档7.1节 46字节大端序)")
    raw = pack_plc_to_upper(
        year=2025, month=7, day=16, hour=15, minute=11, second=3,
        vehicle_speed=5000,
        hscb=1, door_closed=1, ato_available=1, ato_active=1,
        eb_button=1, horn=0,
        door_mode_switch=2,
        key_switch=1, alert_flag=1,
        dir_handle=1, main_handle=1, traction_level=12800, brake_level=0,  # 12800=50%
    )
    parsed = parse_plc_to_upper(raw)
    assert parsed["identify_ok"] == True
    assert parsed["year"] == 2025
    assert parsed["month"] == 7
    assert parsed["vehicle_speed"] == 5000
    assert parsed["hscb"] == True
    assert parsed["door_closed_indicator"] == True
    assert parsed["ato_available"] == True
    assert parsed["ato_active"] == True
    assert parsed["eb_button_locked"] == True
    assert parsed["door_mode_switch_str"] == "自动"
    assert parsed["key_switch"] == True
    assert parsed["alert_flag"] == True
    assert parsed["dir_handle_str"] == "向前"
    assert parsed["main_handle_str"] == "牵引"
    assert parsed["traction_level"] == 50 * 256  # 原始值 50*256
    assert parsed["traction_level_pct"] == 50.0  # 换算后 50%
    assert parsed["brake_level"] == 0
    assert parsed["brake_level_pct"] == 0.0
    print(f"    [OK] 打包 {len(raw)}B -> 解析: time={parsed['timestamp_str']}, "
          f"speed={parsed['vehicle_speed']}, hscb={parsed['hscb']}, "
          f"牵引极位={parsed['traction_level_pct']}%, "
          f"制动极位={parsed['brake_level_pct']}%")

    # 2. 上位机 -> PLC
    print("\n[2] 上位机 -> PLC 编解码")
    raw = pack_upper_to_plc(year=2025, month=7, day=16,
                            hscb=1, door_closed=1, vehicle_speed=5000)
    parsed = parse_upper_to_plc(raw)
    assert parsed["identify_ok"] == True
    assert parsed["total_len"] == UPPER_TO_PLC_LEN
    assert parsed["hscb"] == True
    assert parsed["door_closed_indicator"] == True
    assert parsed["vehicle_speed"] == 5000
    assert parsed["year"] == 2025
    assert parsed["month"] == 7
    assert parsed["day"] == 16
    print(f"    [OK] 打包 {len(raw)}B -> 解析: time={parsed['timestamp_str']}, "
          f"speed={parsed['vehicle_speed']}, hscb={parsed['hscb']}")

    # 3. 网络屏
    print("\n[3] 网络屏 编解码 (572字节)")
    raw = pack_network_screen(
        year=2025, month=7, day=16, hour=15, minute=30, second=0,
        speed=60.0,
        acceleration=0.5,
        power_pull=2000,
        net_pressure=1500,
        speed_limit=80,
        level_pos=LEVEL_POS["TRACTION"],
        run_mode=(DOOR_MODE_MM_AM_AA["AM"] << 4) | RUN_MODE_MANUAL_ATO["MANUAL"],
        master_v=750,
        run_dir=RUN_DIR["RIGHT"],
        driver_room_state=(CAB_STATE["ACTIVE"] << 0) | (CAB_STATE["INACTIVE"] << 4),
        curr_station_id=3,
        next_station_id=4,
        end_station_id=16,
        power_state=1,
        # 6车数组
        door_state=[0x00000000, 0x00000000, 0x00000000,
                    0x00000000, 0x00000000, 0x00000000],
        brake_pressure=[50, 55, 60, 55, 50, 45],
        temp=[22.5, 23.0, 23.5, 23.0, 22.8, 22.0],
        inside_temp=[25.0, 25.5, 26.0, 25.5, 25.0, 24.8],
        # 蓄电池 TC1
        tc1_battle_remain=85,
        tc1_battle_v=110,
        tc1_hi_v=4200,
        tc1_li_v=3800,
        tc1_temp=28,
        tc1_hi_pos=5,
        tc1_li_pos=12,
        # 列车号
        train_no=1,
        fault_code=0,
    )
    parsed = parse_network_screen(raw)
    assert parsed["identify_ok"] == True
    assert parsed["total_len"] == NETWORK_SCREEN_LEN
    assert abs(parsed["speed"] - 60.0) < 0.01
    assert abs(parsed["acceleration"] - 0.5) < 0.01
    assert parsed["power_pull"] == 2000
    assert parsed["net_pressure"] == 1500
    assert parsed["speed_limit"] == 80
    assert parsed["level_pos_str"] == "牵引"
    assert parsed["run_dir_str"] == "右"
    assert parsed["driver_room_tc1"] == "激活"
    assert parsed["driver_room_tc2"] == "未激活"
    assert parsed["curr_station_id"] == 3
    assert parsed["next_station_id"] == 4
    assert parsed["power_state"] == 1
    assert parsed["brake_pressure"] == [50, 55, 60, 55, 50, 45]
    assert parsed["temp"] == [22.5, 23.0, 23.5, 23.0, 22.8, 22.0]
    assert parsed["tc1_battle_remain"] == 85
    assert parsed["tc1_battle_v"] == 110
    assert parsed["tc1_hi_v"] == 4200
    assert parsed["tc1_li_v"] == 3800
    assert parsed["tc1_temp"] == 28
    assert parsed["tc1_hi_pos"] == 5
    assert parsed["tc1_li_pos"] == 12
    assert parsed["train_no"] == 1
    assert parsed["fault_code"] == 0
    print(f"    [OK] 打包 {len(raw)}B -> 解析: speed={parsed['speed']}, "
          f"level={parsed['level_pos_str']}, dir={parsed['run_dir_str']}, "
          f"brake_pressure={parsed['brake_pressure']}, "
          f"battery_tc1={{remain={parsed['tc1_battle_remain']}%, "
          f"v={parsed['tc1_battle_v']}V, hi={parsed['tc1_hi_v']}mV, "
          f"li={parsed['tc1_li_v']}mV, temp={parsed['tc1_temp']}°C}}")

    # 3b. 网络屏 → 上位机 牵引切除请求 (26字节)
    print("\n[3b] 网络屏 → 上位机 牵引切除请求 (26字节)")
    req_data = bytearray(NETWORK_SCREEN_REQUEST_LEN)
    struct.pack_into("<I", req_data, 0, 0x55AA55AA)
    struct.pack_into("<H", req_data, 4, NETWORK_SCREEN_REQUEST_LEN)
    struct.pack_into("<H", req_data, 6, 2)
    # 模拟：第3车牵引切除
    req_data[24] = 0x04  # Bit2 = 1 (第3车)
    parsed_req = parse_network_screen_request(bytes(req_data))
    assert parsed_req["identify_ok"] == True
    assert parsed_req["pull_cut"]["car_3"] == True
    assert parsed_req["pull_cut"]["car_1"] == False
    assert parsed_req["pull_cut"]["car_6"] == False
    print(f"    [OK] 解析 {len(req_data)}B: pull_ctrl=0b{parsed_req['pull_ctrl']:06b}, "
          f"car_3_cut={parsed_req['pull_cut']['car_3']}")

    # 3c. 网络屏 空报文默认值
    print("\n[3c] 网络屏 空报文默认值")
    raw_default = pack_network_screen()
    parsed_default = parse_network_screen(raw_default)
    assert parsed_default["identify_ok"] == True
    assert parsed_default["speed"] == 0.0
    assert parsed_default["net_pressure"] == 1500  # 文档默认值
    assert parsed_default["level_pos_str"] == "惰行"
    assert parsed_default["brake_pressure"] == [0] * 6
    print(f"    [OK] 默认值: speed=0, net_pressure=1500V, level=惰行")

    # 4. 信号屏
    print("\n[4] 信号屏(DMI) 编解码")
    raw = pack_signal_screen(current_speed_cm_s=5000, permit_speed_cm_s=8000,
                             target_distance_cm=100000, current_mode=3)
    parsed = parse_signal_screen(raw)
    assert parsed["current_speed_cm_s"] == 5000
    assert parsed["permit_speed_cm_s"] == 8000
    assert parsed["target_distance_m"] == 1000.0
    assert parsed["current_mode"] == "RM"
    print(f"    [OK] 打包 {len(raw)}B -> 解析: speed={parsed['current_speed_km_h']}km/h, "
          f"dist={parsed['target_distance_m']}m, mode={parsed['current_mode']}")

    # 5. 驾驶台开关量 ATP位编解码
    print("\n[5] 驾驶台开关量 ATP位编解码")
    bits = {
        "cab_active": True,
        "key_active": True,
        "door_closed": True,
        "traction_cut": False,
        "eb_applied": False,
        "handle_zero_forward": True,
        "confirm_btn": False,
        "brake_fault": False,
    }
    atp_safe = encode_atp_safe_input(bits)
    decoded = _decode_bits(atp_safe, ATP_SAFE_INPUT)
    assert decoded["cab_active"] == True
    assert decoded["key_active"] == True
    assert decoded["door_closed"] == True
    assert decoded["traction_cut"] == False
    assert decoded["handle_zero_forward"] == True
    print(f"    [OK] 编码 0x{atp_safe:08x} -> 解码: cab_active={decoded['cab_active']}, "
          f"key={decoded['key_active']}, door={decoded['door_closed']}")

    # 6. 信号系统 <-> 总控 驾驶台开关量
    print("\n[6] 信号系统 <-> 总控 驾驶台开关量")
    raw = pack_signal_to_db_cab_binary(
        train_id=1,
        atp_safe_output=encode_atp_safe_output({"eb_output": True, "zero_speed": True}),
        atp_nonsafe_output=encode_atp_nonsafe_output({"fam_mode": True}),
        ato_nonsafe_output=encode_ato_nonsafe_output({"ato_active": True}),
    )
    parsed = parse_signal_to_db_cab_binary(raw)
    assert parsed["train_id"] == 1
    assert parsed["atp_safe_bits"]["eb_output"] == True
    assert parsed["atp_safe_bits"]["zero_speed"] == True
    assert parsed["atp_nonsafe_bits"]["fam_mode"] == True
    assert parsed["ato_nonsafe_bits"]["ato_active"] == True
    print(f"    [OK] 信号->总控 {len(raw)}B: eb_output={parsed['atp_safe_bits']['eb_output']}")

    # 7. 总控->信号 列车数据
    print("\n[7] 总控->信号 列车数据")
    trains = [
        {"train_id": 1, "speed_cm_s": 5000, "distance_cm": 100000,
         "direction": 0x55, "load_kg": 50000, "fault_speed": 0, "eb_status": 0,
         "traction_avail": 1, "brake_avail": 1},
        {"train_id": 2, "speed_cm_s": 0, "distance_cm": 50000,
         "direction": 0xAA, "load_kg": 48000, "fault_speed": 0, "eb_status": 0,
         "traction_avail": 1, "brake_avail": 1},
    ]
    raw = pack_db_to_signal_train_data(trains)
    parsed = parse_db_to_signal_train_data(raw)
    assert parsed["train_count"] == 2
    assert parsed["trains"][0]["speed_cm_s"] == 5000
    assert parsed["trains"][1]["direction"] == 0xAA
    print(f"    [OK] 总控->信号 {len(raw)}B: {parsed['train_count']}列车, "
          f"列车1 speed={parsed['trains'][0]['speed_cm_s']}cm/s, "
          f"列车2 direction={parsed['trains'][1]['direction_str']}")

    print("\n" + "=" * 60)
    print("所有自检通过 [OK]")
    print("=" * 60)
    return True


if __name__ == "__main__":
    self_test()