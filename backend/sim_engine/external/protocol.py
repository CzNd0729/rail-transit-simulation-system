"""外部系统协议常量定义。

基于《外部系统对接方案》文档定义所有通信协议常量、
报文长度、偏移量、位映射和枚举值。

文档版本: 2026-07  (基于《轨交多系统平台接口协议汇总20260630》)
"""

from __future__ import annotations

# ====================================================================
# 全局开关
# ====================================================================
USE_REAL_HARDWARE = False
"""True=连接真实硬件, False=使用内置模拟器。"""

# ====================================================================
# 总控数据库节点 UDP 20ms 高频通道
# ====================================================================
# 文档 3.1 节 / 4.1 节
DB_NODE_IP = "192.168.200.102"
DB_NODE_PORT = 23002
VEHICLE_MODEL_IP = "192.168.200.110"
VEHICLE_MODEL_PORT = 23001

# 你 → 总控节点: 20列车 × 3字段(加速度/速度/里程) × 8字节 = 480字节
UDP_TRAIN_DATA_TO_DB_LEN = 480
# 总控节点 → 你: 20列车 × 2字段(指令/百分比) × 8字节 = 320字节
UDP_DB_TO_TRAIN_LEN = 320

# ====================================================================
# 司机台 PLC TCP 协议
# ====================================================================
# 文档 3.2 节 / 4.3 节
PLC_DEVICE_IP = "192.168.100.123"
PLC_DEPLOY_IP = "192.168.200.102"
PLC_PORT = 8001
PLC_PORT_B = 8002
PLC_PORT_C = 8003

# 报文长度
PLC_TO_UPPER_LEN = 46      # PLC → 上位机 (24B头 + 22B数据)
UPPER_TO_PLC_LEN = 28      # 上位机 → PLC (24B头 + 4B数据)

# 报文头固定标识
PLC_HEADER_ID = 0xAA55AA55

# ---- 字节序 ----
# 文档 3.2 节: "字节序 | 小端 (Little Endian)"
# PLC 协议报文头和数据区统一使用小端序

# ====================================================================
# 司机台网络屏 (HMI) TCP 协议
# ====================================================================
# 文档 3.3 节 / 4.4 节
NETWORK_SCREEN_DEVICE_IP = "192.168.100.121"
NETWORK_SCREEN_DEPLOY_IP = "192.168.200.102"
NETWORK_SCREEN_PORT = 8888

NETWORK_SCREEN_LEN = 572           # 上位机 → 网络屏 (24B头 + 548B数据)
NETWORK_SCREEN_REQUEST_LEN = 26    # 网络屏 → 上位机 (牵引切除请求)
NETWORK_SCREEN_HEADER_ID = 0x55AA55AA

# 网络屏报文偏移量 (上位机 → 网络屏, 572字节)
NETWORK_SCREEN_OFFSET = {
    # ---- 报文头 (24字节) ----
    "identify": 0,          # 4B DWORD  固定 0x55AA55AA
    "total_len": 4,         # 2B WORD   报文总大小
    "data_len": 6,          # 2B WORD   数据长度 (= 548)
    "timestamp": 8,         # 8B DDWORD 毫秒级时间戳
    "verify_type": 16,      # 2B WORD   校验方式（备用）
    "verify_code": 18,      # 2B WORD   校验码（备用）
    "protocol_id": 20,      # 2B WORD   协议ID（备用）
    "msg_id": 22,           # 2B WORD   消息ID
    # ---- 时间 (12字节) ----
    "year": 24,             # 2B WORD
    "month": 26,            # 2B WORD
    "day": 28,              # 2B WORD
    "hour": 30,             # 2B WORD
    "minute": 32,           # 2B WORD
    "second": 34,           # 2B WORD
    # ---- 基础运行信息 (22字节) ----
    "curr_station_id": 36,  # 1B BYTE   当前站ID (0-16)
    "next_station_id": 37,  # 1B BYTE   下一站ID (0-16)
    "end_station_id": 38,   # 1B BYTE   终点站ID (0-16)
    "power_state": 39,      # 1B BYTE   车间电源供电状态
    "speed": 40,            # 4B FLOAT  速度 (km/h)
    "acceleration": 44,     # 4B FLOAT  加速度 (m/s²)
    "power_pull": 48,       # 2B WORD   总牵引力 (N)
    "net_pressure": 50,     # 2B WORD   网压 (V)
    "speed_limit": 52,      # 2B WORD   限速 (km/h)
    "level_pos": 54,        # 1B BYTE   级位: 惰行(0)/牵引(1)/制动(2)/紧急(3)
    "run_mode": 55,         # 1B BYTE   低4位=手动(0)/ATO(1), 高4位=门模式
    "master_v": 56,         # 2B WORD   母线电压值 (V)
    "run_dir": 58,          # 1B BYTE   运行方向: 无(0)/左(1)/右(2)
    "driver_room_state": 59,# 1B BYTE   司机室状态: 低4=tc1 高4=tc2
    # ---- 6节车 门状态 (24字节) ----
    "door_state": 60,       # 24B DWORD[6]  门状态, 每门2bit
    # ---- 6节车 制动/停放状态 (6字节) ----
    "stop_pos_state": 84,   # 6B BYTE[6]   低4=制动 高4=停放
    "fire_empty_run": 90,   # 6B BYTE[6]   火警(低4) 空转(高4)
    "warm_empty_state1": 96,# 6B BYTE[6]   乘客报警1(低4) 2(高4)
    "warm_empty_state2": 102,# 6B BYTE[6]  同上
    "pull_switch": 108,     # 6B BYTE[6]   牵引(低4) 空压机(高4)
    "charge": 114,          # 6B BYTE[6]   充电机1(低4) 2(高4)
    "assist_high_switch": 120,# 6B BYTE[6] 辅逆(低4) 开关车间电压(高4)
    "breaker_master": 126,  # 6B BYTE[6]   断路器(低4) 母线高速断路器(高4)
    "elect_stop": 132,      # 12B WORD[6]  牵引/电制动力
    "wind_press": 144,      # 12B WORD[6]  主风缸压力
    "brake_pressure": 156,  # 12B WORD[6]  制动缸压力
    "usage_rate": 168,      # 6B BYTE[6]   载客率
    "line_net": 174,        # 6B BYTE[6]   线网电流
    "temp": 180,            # 24B FLOAT[6] 温度
    "pull_stream": 204,     # 6B BYTE[6]   牵引无流
    "stop_im": 210,         # 10B BYTE[10] 紧急制动
    "side_info": 220,       # 6B BYTE[6]   旁路信息
    "braker_state": 226,    # 11B BYTE[11] 断路器状态
    "line_and_elect_stop": 237,# 6B BYTE[6] KIC(低4) 电制动(高4)
    "line_v": 244,          # 12B WORD[6]  线电压
    "stop_state": 256,      # 6B BYTE[6]   紧急制动(低4) 保持制动(高4)
    "air_stop": 262,        # 12B WORD[6]  空气制动力
    "empty_press1": 274,    # 12B WORD[6]  空簧压力
    "empty_press2": 286,    # 12B WORD[6]  空簧压力2
    "b05_and_b19": 298,     # 6B BYTE[6]   B05+B19
    "kma_and_elect_power": 304,# 6B BYTE[6] KMA(低4) 扩展供电(高4)
    "ni_bian_input_v": 310, # 12B WORD[6]  逆变器输入电压
    "ni_bian_output_v": 322,# 12B WORD[6]  逆变器输出线电压
    "charge_output_v": 334, # 12B WORD[6]  充电机输出电压
    "ni_bian_input_a": 346, # 6B BYTE[6]   逆变器输入电流
    "ni_bian_output_a": 352,# 6B BYTE[6]   逆变器输出电流
    "charge_output_a": 358, # 6B BYTE[6]   充电机输出电流
    # ---- 接触器/KM (6字节) ----
    "tc1_km1": 364,         # 1B BYTE
    "tc1_km3": 365,
    "tc1_km5": 366,
    "tc2_km1": 367,
    "tc2_km3": 368,
    "tc2_km5": 369,
    # ---- 蓄电池 TC1 (22字节) ----
    "tc1_battle_remain": 370,   # 2B WORD
    "tc1_battle_v": 372,
    "tc1_battle_charge_a": 374,
    "tc1_battle_output_a": 376,
    "tc1_battle_temp": 378,
    "tc1_hi_v": 380,
    "tc1_li_v": 382,
    "tc1_hi_pos": 384,          # 1B BYTE
    "tc1_li_pos": 385,
    "tc1_temp": 386,            # 2B WORD
    "tc2_temp": 388,
    "tc1_temp_pos": 390,        # 1B BYTE
    "tc2_temp_pos": 391,
    # ---- 蓄电池 TC2 (18字节) ----
    "tc2_battle_remain": 392,
    "tc2_battle_v": 394,
    "tc2_battle_charge_a": 396,
    "tc2_battle_output_a": 398,
    "tc2_battle_temp": 400,
    "tc2_hi_v": 402,
    "tc2_li_v": 404,
    "tc2_hi_pos": 406,          # 1B BYTE
    "tc2_li_pos": 407,
    # ---- 烟火/空调 (72字节) ----
    "smoke_temp": 408,      # 24B DWORD[6]
    "out_temp": 432,        # 24B FLOAT[6]
    "inside_temp": 456,     # 24B FLOAT[6]
    "air_cond_mode": 480,   # 6B BYTE[6]
    "cold_wind": 486,
    "wind_fan": 492,
    "press_machine": 498,   # 12B WORD[6]
    "big_wind": 510,        # 6B BYTE[6]
    "machine11": 516,
    "machine12": 522,
    "machine21": 528,
    "machine22": 534,
    # ---- 网络设备状态 (32字节) ----
    "tc1_net": 540,         # 4B WORD[2]
    "tc2_net": 544,
    "tc3_net": 548,         # 2B BYTE[2]
    "tc4_net": 550,
    "tc5_net": 552,
    "tc6_net": 554,
    "conn_ab": 556,         # 1B BYTE
    "tc1_devs_state": 558,  # 2B WORD
    "tc2_devs_state": 560,
    "tc3_devs_state": 562,  # 1B BYTE
    "tc4_devs_state": 563,
    "tc5_devs_state": 564,
    "tc6_devs_state": 565,
    "econn_dev_state": 566, # 1B BYTE
    "econn_dev_state2": 567,
    "fault_code": 568,      # 2B WORD
    "train_no": 570,        # 2B WORD
}

# 网络屏 → 上位机 牵引切除请求偏移量 (26字节)
NETWORK_SCREEN_REQUEST_OFFSET = {
    "identify": 0,          # 4B DWORD
    "total_len": 4,         # 2B WORD
    "data_len": 6,          # 2B WORD
    "timestamp": 8,         # 8B DDWORD
    "verify_type": 16,      # 2B WORD
    "verify_code": 18,      # 2B WORD
    "protocol_id": 20,      # 2B WORD
    "msg_id": 22,           # 2B WORD
    "pull_ctrl": 24,        # 1B BYTE   牵引切除 Bit0-Bit5
    "reserve": 25,          # 1B BYTE
}

# ====================================================================
# 司机台信号屏 (MMI) TCP 协议
# ====================================================================
# 文档 3.4 节 / 4.5 节
SIGNAL_SCREEN_DEVICE_IP = "192.168.100.122"
SIGNAL_SCREEN_DEPLOY_IP = "192.168.200.102"
SIGNAL_SCREEN_PORT = 9999

SIGNAL_SCREEN_LEN = 68            # 上位机 → 信号屏 (24B头 + 44B数据)
SIGNAL_SCREEN_HEADER_ID = 0x55AA55AA

# 信号屏报文偏移量 (上位机 → 信号屏, 66字节)
SIGNAL_SCREEN_OFFSET = {
    # ---- 报文头 (24字节) ----
    "identify": 0,          # 4B DWORD  固定 0x55AA55AA
    "total_len": 4,         # 2B WORD   报文总大小
    "data_len": 6,          # 2B WORD   数据长度 (= 42)
    "timestamp": 8,         # 8B DDWORD 毫秒级时间戳
    "verify_type": 16,      # 2B WORD   校验类型
    "verify_code": 18,      # 2B WORD   校验码
    "protocol_id": 20,      # 2B WORD   协议ID
    "msg_id": 22,           # 2B WORD   消息ID
    # ---- 数据区 (42字节) ----
    "year": 24,             # 2B WORD
    "month": 26,
    "day": 28,
    "hour": 30,
    "minute": 32,
    "second": 34,
    "curr_station_id": 36,  # 1B BYTE   当前站ID
    "next_station_id": 37,  # 1B BYTE   下一站ID
    "end_station_id": 38,   # 1B BYTE   终点站ID
    "cm_state": 39,         # 1B BYTE   CM状态 -1/0/1
    "mm_state": 40,         # 1B BYTE   MM状态 -1/0/1
    "ctc_state": 41,        # 1B BYTE   CTC状态 -1/0/1
    "run_direction": 42,    # 1B BYTE   运行方向 -1=非法 0=上行 1=下行
    "reserved_43": 43,      # 1B BYTE   预留
    "speed": 44,            # 4B FLOAT  速度 (km/h)
    "acceleration": 48,     # 4B FLOAT  加速度 (m/s²)
    "traction_cut": 52,     # 2B WORD   牵引切除 0/1
    "speed_limit": 54,      # 2B WORD   限速 (km/h)
    "mode": 56,             # 1B BYTE   模式 DTO/ATO/AR/SM/RM
    "traction_state": 57,   # 1B BYTE   牵引状态 0/1
    "brake_state": 58,      # 1B BYTE   制动状态 0/1
    "eb_state": 59,         # 1B BYTE   紧急制动 0/1
    "event_id": 60,         # 1B BYTE   事件ID
    "signal_state": 61,     # 1B BYTE   信号状态 BIT0-3
    "train_id": 62,         # 2B WORD   车号
    "dist_to_station": 64,  # 4B FLOAT  距下一站距离 (m)
}

# ====================================================================
# 枚举定义
# ====================================================================

# 级位 (文档 4.4)
LEVEL_POS = {
    "COAST": 0,       # 惰行
    "TRACTION": 1,    # 牵引
    "BRAKE": 2,       # 制动
    "EMERGENCY": 3,   # 紧急制动
}

# 运行方向 (文档 4.4)
RUN_DIR = {
    "NONE": 0,        # 无
    "LEFT": 1,        # 左
    "RIGHT": 2,       # 右
    "UNKNOWN": 0xFF,  # 未知
}

# 司机室状态
CAB_STATE = {
    "INACTIVE": 0,    # 未激活
    "ACTIVE": 1,      # 激活
}

# 运行模式 (低4位)
RUN_MODE_MANUAL_ATO = {
    "MANUAL": 0,
    "ATO": 1,
}

# 门模式 (高4位)
DOOR_MODE_MM_AM_AA = {
    "MM": 0,
    "AM": 1,
    "AA": 2,
}

# 信号屏运行方向 (文档 4.5)
SIGNAL_RUN_DIR = {
    "UP": 0,          # 上行
    "DOWN": 1,        # 下行
    "INVALID": -1,    # 非法
}

# 信号屏驾驶模式 (文档 4.5)
SIGNAL_MODE_MAP = {
    0: "RM",
    1: "SM",
    2: "AR",
    3: "ATO",
    4: "DTO",
}

# 驾驶模式枚举 (信号系统)
DRIVE_MODE = {
    "INIT": 0,
    "RD": 2,
    "RM": 3,
    "CM": 4,
    "AM": 5,
    "AR": 6,
    "EUM": 7,
    "CAM": 8,
    "FAM": 9,
}

# ====================================================================
# 常量辅助
# ====================================================================
_CAR_COUNT = 6  # 6节编组

# 通信超时 (秒)
CONNECT_TIMEOUT = 5.0
SEND_TIMEOUT = 3.0
RECV_TIMEOUT = 3.0

# PLC 数据接收超时 (秒) — 超过此时间未收到数据视为 PLC 断开
PLC_RECV_TIMEOUT = 2.0