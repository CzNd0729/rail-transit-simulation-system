"""
司机台联动测试 — 通信参数配置

**已弃用** — 外部系统接入方案已废弃，不再需要司机台联动测试。
保留此文件仅作参考，不再维护。
"""

# ============================================================
# 全局开关
# ============================================================
USE_REAL_HARDWARE = False  # True=连接真实硬件, False=使用模拟器

# ============================================================
# PLC 协议（司机驾驶模拟台PLC）
# ============================================================
PLC_SERVER_IP = "192.168.100.123"
PLC_PORT_A = 8001  # 连接1：主数据通道
PLC_PORT_B = 8002  # 连接2：备用/辅助数据通道
PLC_PORT_C = 8003  # 连接3：备用/辅助数据通道

# PLC 发送给上位机（周期100ms，46字节）
PLC_TO_UPPER_LEN = 46

# 上位机发送给 PLC（无固定周期，28字节，帧头24+数据区2+车辆速度2）
UPPER_TO_PLC_LEN = 28

# ============================================================
# 网络屏协议（司机驾驶模拟台网络屏）
# ============================================================
NETWORK_SCREEN_IP = "192.168.100.122"
NETWORK_SCREEN_PORT = 8888
NETWORK_SCREEN_LEN = 572  # 总长572字节（上位机→网络屏）
NETWORK_SCREEN_REQUEST_LEN = 26  # 总长26字节（网络屏→上位机，牵引切除请求）

# 网络屏报文偏移量定义（上位机→网络屏，572字节）
NETWORK_SCREEN_OFFSET = {
    # 报文头（24字节）
    "identify": 0,          # 4B DWORD  固定 0x55AA55AA
    "total_len": 4,         # 2B WORD   报文总大小
    "data_len": 6,          # 2B WORD   数据长度
    "timestamp": 8,         # 8B DDWORD 毫秒级时间戳
    "verify_type": 16,      # 2B WORD   校验方式（备用）
    "verify_code": 18,      # 2B WORD   校验码（备用）
    "protocol_id": 20,      # 2B WORD   协议ID（备用）
    "msg_id": 22,           # 2B WORD   消息ID
    # 时间
    "year": 24,             # 2B WORD
    "month": 26,            # 2B WORD
    "day": 28,              # 2B WORD
    "hour": 30,             # 2B WORD
    "minute": 32,           # 2B WORD
    "second": 34,           # 2B WORD
    # 基础运行信息
    "curr_station_id": 36,  # 1B BYTE   当前站ID (0-16)
    "next_station_id": 37,  # 1B BYTE   下一站ID (0-16)
    "end_station_id": 38,   # 1B BYTE   终点站ID (0-16)
    "power_state": 39,      # 1B BYTE   车间电源供电 有(1)/无(0)
    "speed": 40,            # 4B FLOAT  速度
    "acceleration": 44,     # 4B FLOAT  加速度
    "power_pull": 48,       # 2B WORD   总牵引力
    "net_pressure": 50,     # 2B WORD   网压
    "speed_limit": 52,      # 2B WORD   限速
    "level_pos": 54,        # 1B BYTE   级位: 惰行(0)/牵引(1)/制动(2)/紧急(3)
    "run_mode": 55,         # 1B BYTE   模式: 低4位=手动(0)/ATO(1), 高4位=MM(0)/AM(1)/AA(2)
    "master_v": 56,         # 2B WORD   母线电压值
    "run_dir": 58,          # 1B BYTE   运行方向: 无(0)/左(1)/右(2)/未知(0xff)
    "driver_room_state": 59,# 1B BYTE   司机室: 激活(1)/未激活(0), 低4=tc1+高4=tc2
    # 6节车 × 多字段（BYTE-6 / WORD-6 / DWORD-6 / FLOAT-6 / BYTE-10 / BYTE-11）
    "door_state": 60,       # 24B DWORD[6]  门状态
    "stop_pos_state": 84,   # 6B  BYTE[6]   制动(低4)+停放(高4)
    "fire_empty_run": 90,   # 6B  BYTE[6]   火警(低4)+空转(高4)
    "warm_empty_state1": 96,# 6B  BYTE[6]   乘客报警1(低4)+乘客报警2(高4)
    "warm_empty_state2": 102,# 6B BYTE[6]   同上
    "pull_switch": 108,     # 6B  BYTE[6]   牵引状态(低4)+空压机(高4)
    "charge": 114,          # 6B  BYTE[6]   充电机1(低4)+充电机2(高4)
    "assist_high_switch": 120,# 6B BYTE[6]  辅逆(低4)+开关车间电压(高4)
    "breaker_master": 126,  # 6B  BYTE[6]   断路器(低4)+母线高速断路器(高4)
    "elect_stop": 132,      # 12B WORD[6]   牵引/电制动力
    "wind_press": 144,      # 12B WORD[6]   主风缸压力
    "brake_pressure": 156,  # 12B WORD[6]   制动缸压力
    "usage_rate": 168,      # 6B  BYTE[6]   载客率
    "line_net": 174,        # 6B  BYTE[6]   线网电流
    "temp": 180,            # 24B FLOAT[6]  温度
    "pull_stream": 204,     # 6B  BYTE[6]   牵引无流
    "stop_im": 210,         # 10B BYTE[10]  紧急制动
    "side_info": 220,       # 6B  BYTE[6]   旁路信息
    "braker_state": 226,    # 11B BYTE[11]  断路器状态
    "line_and_elect_stop": 237,# 6B BYTE[6] KIC(低4)+电制动(高4)
    "line_v": 244,          # 12B WORD[6]   线电压
    "stop_state": 256,      # 6B  BYTE[6]   紧急制动(低4)+保持制动(高4)
    "air_stop": 262,        # 12B WORD[6]   空气制动力
    "empty_press1": 274,    # 12B WORD[6]   空簧压力
    "empty_press2": 286,    # 12B WORD[6]   空簧压力2
    "b05_and_b19": 298,     # 6B  BYTE[6]   B05(bit0-1)+B19(1)(bit2-3)+B19(2)(bit4-5)
    "kma_and_elect_power": 304,# 6B BYTE[6] KMA(低4)+扩展供电(高4)
    "ni_bian_input_v": 310, # 12B WORD[6]   逆变器输入电压
    "ni_bian_output_v": 322,# 12B WORD[6]   逆变器输出线电压
    "charge_output_v": 334, # 12B WORD[6]   充电机输出电压
    "ni_bian_input_a": 346, # 6B  BYTE[6]   逆变器输入电流
    "ni_bian_output_a": 352,# 6B  BYTE[6]   逆变器输出电流
    "charge_output_a": 358, # 6B  BYTE[6]   充电机输出电流
    # 接触器/KM 状态
    "tc1_km1": 364,         # 1B BYTE  闭合(0)/断开(1)/故障(2)/未知(0xff)
    "tc1_km3": 365,         # 1B BYTE
    "tc1_km5": 366,         # 1B BYTE
    "tc2_km1": 367,         # 1B BYTE
    "tc2_km3": 368,         # 1B BYTE
    "tc2_km5": 369,         # 1B BYTE
    # 蓄电池 TC1
    "tc1_battle_remain": 370,   # 2B WORD  蓄电池剩余容量
    "tc1_battle_v": 372,        # 2B WORD  蓄电池电压
    "tc1_battle_charge_a": 374, # 2B WORD  蓄电池充电电流
    "tc1_battle_output_a": 376, # 2B WORD  蓄电池放电电流
    "tc1_battle_temp": 378,     # 2B WORD  蓄电池箱温度
    "tc1_hi_v": 380,            # 2B WORD  最高单体电压
    "tc1_li_v": 382,            # 2B WORD  最低单体电压
    "tc1_hi_pos": 384,          # 1B BYTE  最高单体位置
    "tc1_li_pos": 385,          # 1B BYTE  最低单体位置
    "tc1_temp": 386,            # 2B WORD  最高单体温度
    "tc2_temp": 388,            # 2B WORD
    "tc1_temp_pos": 390,        # 1B BYTE  最高单体位置
    "tc2_temp_pos": 391,        # 1B BYTE
    # 蓄电池 TC2
    "tc2_battle_remain": 392,   # 2B WORD
    "tc2_battle_v": 394,        # 2B WORD
    "tc2_battle_charge_a": 396, # 2B WORD
    "tc2_battle_output_a": 398, # 2B WORD
    "tc2_battle_temp": 400,     # 2B WORD
    "tc2_hi_v": 402,            # 2B WORD
    "tc2_li_v": 404,            # 2B WORD
    "tc2_hi_pos": 406,          # 1B BYTE
    "tc2_li_pos": 407,          # 1B BYTE
    # 烟火/空调
    "smoke_temp": 408,      # 24B DWORD[6]  烟火温度
    "out_temp": 432,        # 24B FLOAT[6]  室外温度
    "inside_temp": 456,     # 24B FLOAT[6]  室内温度
    "air_cond_mode": 480,   # 6B  BYTE[6]   空调控制模式
    "cold_wind": 486,       # 6B  BYTE[6]   冷凝风机
    "wind_fan": 492,        # 6B  BYTE[6]   风机
    "press_machine": 498,   # 12B WORD[6]   压缩机
    "big_wind": 510,        # 6B  BYTE[6]   强风状态 打开(1)/关闭(0)
    "machine11": 516,       # 6B  BYTE[6]   机组1-1新风阀开度
    "machine12": 522,       # 6B  BYTE[6]   机组1-2新风阀开度
    "machine21": 528,       # 6B  BYTE[6]   机组2-1新风阀开度
    "machine22": 534,       # 6B  BYTE[6]   机组2-2新风阀开度
    # 网络设备状态
    "tc1_net": 540,         # 4B  WORD[2]   TC1 A/B网设备
    "tc2_net": 544,         # 4B  WORD[2]   TC2 A/B网设备
    "tc3_net": 548,         # 2B  BYTE[2]   TC3 设备
    "tc4_net": 550,         # 2B  BYTE[2]   TC4 设备
    "tc5_net": 552,         # 2B  BYTE[2]   TC5 设备
    "tc6_net": 554,         # 2B  BYTE[2]   TC6 设备
    "conn_ab": 556,         # 1B  BYTE     bit0:A→B, bit1:B→A
    "tc1_devs_state": 558,  # 2B  WORD     TC1设备状态
    "tc2_devs_state": 560,  # 2B  WORD     TC2设备状态
    "tc3_devs_state": 562,  # 1B  BYTE     TC3设备状态
    "tc4_devs_state": 563,  # 1B  BYTE     TC4设备状态
    "tc5_devs_state": 564,  # 1B  BYTE     TC5设备状态
    "tc6_devs_state": 565,  # 1B  BYTE     TC6设备状态
    "econn_dev_state": 566, # 1B  BYTE     A网络设备状态
    "econn_dev_state2": 567,# 1B  BYTE     B网络设备状态
    "fault_code": 568,      # 2B  WORD     故障码
    "train_no": 570,        # 2B  WORD     列车号
}

# 网络屏→上位机 牵引切除请求 偏移量（26字节）
NETWORK_SCREEN_REQUEST_OFFSET = {
    "identify": 0,          # 4B DWORD  固定 0x55AA55AA
    "total_len": 4,         # 2B WORD   报文总大小
    "data_len": 6,          # 2B WORD   数据长度
    "timestamp": 8,         # 8B DDWORD 毫秒级时间戳
    "verify_type": 16,      # 2B WORD   校验方式（备用）
    "verify_code": 18,      # 2B WORD   校验码（备用）
    "protocol_id": 20,      # 2B WORD   协议ID（备用）
    "msg_id": 22,           # 2B WORD   消息ID
    "pull_ctrl": 24,        # 1B BYTE   牵引切除 Bit0-Bit5（1-6车）
    "reserve": 25,          # 1B BYTE   保留
}

# ============================================================
# 网络屏 枚举定义
# ============================================================

# 级位
LEVEL_POS = {
    "COAST": 0,       # 惰行
    "TRACTION": 1,    # 牵引
    "BRAKE": 2,       # 制动
    "EMERGENCY": 3,   # 紧急制动
}

# 运行方向
RUN_DIR = {
    "NONE": 0,        # 无
    "LEFT": 1,        # 左
    "RIGHT": 2,       # 右
    "UNKNOWN": 0xff,  # 未知
}

# 司机室状态
CAB_STATE = {
    "INACTIVE": 0,    # 未激活
    "ACTIVE": 1,      # 激活
    "UNKNOWN": 0xf,   # 未知
}

# 门状态
DOOR_STATE = {
    "CLOSED": 0,           # 关到位
    "OPEN": 1,             # 门开
    "FAULT": 2,            # 故障
    "OBSTACLE": 3,         # 检测到障碍物
    "ISOLATED": 4,         # 隔离
    "EMERGENCY_UNLOCK": 5, # 紧急解锁
    "UNKNOWN": 0xf,        # 未知
}

# 制动/停放状态
BRAKE_PARKING_STATE = {
    "APPLIED": 0,     # 施加
    "RELEASED": 1,    # 缓解
    "FAULT": 2,       # 故障
    "CUT_OFF": 3,     # 切除
    "UNKNOWN": 0xf,   # 未知
}

# 火警状态
FIRE_STATE = {
    "INACTIVE": 0,    # 未激活
    "ACTIVE": 1,      # 激活
    "UNKNOWN": 0xff,  # 未知
}

# 空转滑行状态
SLIP_STATE = {
    "NORMAL": 0,      # 正常
    "SLIP": 1,        # 空转
    "SKID": 2,        # 滑行
    "UNKNOWN": 0xf,   # 未知
}

# 乘客报警状态
PASSENGER_ALARM_STATE = {
    "NORMAL": 0,      # 正常
    "TALK_DRIVER": 1, # 与司机通话
    "TALK_OCC": 2,    # 与OCC通话
    "CALL": 3,        # 呼叫
    "UNKNOWN": 0xf,   # 未知
}

# 运行模式（低4位）
RUN_MODE_MANUAL_ATO = {
    "MANUAL": 0,      # 手动
    "ATO": 1,         # ATO
}

# 门模式（高4位）
DOOR_MODE_MM_AM_AA = {
    "MM": 0,          # MM
    "AM": 1,          # AM
    "AA": 2,          # AA
    "UNKNOWN": 0xf,   # 未知
}

# 断路器/接触器状态
BREAKER_STATE = {
    "CLOSED": 0,      # 闭合
    "OPEN": 1,        # 断开
    "FAULT": 2,       # 故障
    "UNKNOWN": 0xff,  # 未知
}

# 设备工作状态（牵引/辅逆/充电机等）
DEVICE_WORK_STATE = {
    "WORKING": 0,     # 工作
    "STANDBY": 1,     # 待机
    "FAULT": 2,       # 故障
    "CUT_OFF": 3,     # 切除
    "BYPASS": 0,      # 旁路
    "NOT_BYPASS": 1,  # 未旁路
    "UNKNOWN": 0xf,   # 未知
}

# 空调控制模式
AIR_COND_CTRL_MODE = {
    "CENTRAL": 1,     # 集控
    "LOCAL": 2,       # 本控
}

# 空调运行模式
AIR_COND_MODE = {
    "COOL": 0,        # 制冷
    "HEAT": 1,        # 制暖
    "PRE_COOL": 2,    # 预冷
    "PRE_HEAT": 3,    # 预热
    "AUTO": 4,        # 自动
    "VENT": 5,        # 通风
    "STOP": 6,        # 停机
    "EMERGENCY_VENT": 7, # 紧急通风
}

# ============================================================
# 信号屏协议（司机驾驶模拟台信号屏）
# ============================================================
SIGNAL_SCREEN_IP = "192.168.100.121"
SIGNAL_SCREEN_PORT = 9999
SIGNAL_SCREEN_LEN = 66  # 总长66字节

# ============================================================
# 信号系统 ↔ 总控数据库节点（UDP）
# ============================================================
# 总控数据库节点
DB_NODE_IP = "192.168.100.10"
DB_NODE_PORT = 9000

# 信号系统接口转换单元
SIGNAL_IF_IP = "192.168.100.20"
SIGNAL_IF_PORT = 9001

# 驾驶台开关量信息（报文头0xff 0xf1）
CAB_BINARY_SIGNAL = 0xF1

# ============================================================
# 车辆系统（UDP）
# ============================================================
VEHICLE_MODEL_IP = "192.168.200.110"
VEHICLE_MODEL_PORT = 23001
PLATFORM_IP = "192.168.200.102"
PLATFORM_PORT = 23002

# ============================================================
# 测试参数
# ============================================================
TEST_TIMEOUT = 5.0          # 单次测试超时（秒）
SIM_CYCLE_INTERVAL = 0.1   # 模拟器发送周期（秒）
TEST_LOOP_COUNT = 50        # 全链路测试循环次数

# ============================================================
# PLC 报文内容偏移量定义（根据文档7.1节）
# ============================================================
# PLC → 上位机 (46字节)
PLC_OFFSET = {
    "header": 0,            # 2字节 报文头
    "train_id": 2,          # 2字节 列车ID
    "speed": 4,             # 4字节 速度 (cm/s)
    "accel": 8,             # 4字节 加速度
    "master_controller": 12, # 2字节 司控器状态
    "brake_pressure": 14,   # 2字节 制动缸压力
    "door_status": 16,      # 2字节 门状态
    "cab_active": 18,       # 2字节 驾驶室激活
    "key_status": 20,       # 2字节 钥匙状态
    "eb_status": 22,        # 2字节 紧急制动状态
    "mode": 24,             # 2字节 驾驶模式
    "reserved": 26,         # 20字节 预留
}

# 上位机 → PLC (28字节，文档7.2节，帧头24+数据区4)
UPPER_OFFSET = {
    "identify": 0,          # 4字节 DWORD 固定数据 55 AA 55 AA
    "total_len": 4,         # 2字节 WORD 报文总大小
    "data_len": 6,          # 2字节 WORD 数据区总大小
    "year": 8,              # 2字节 WORD 年
    "month": 10,            # 2字节 WORD 月
    "day": 12,              # 2字节 WORD 日
    "hour": 14,             # 2字节 WORD 时
    "minute": 16,           # 2字节 WORD 分
    "second": 18,           # 2字节 WORD 秒
    "verify_type": 20,      # 2字节 WORD 校验类型
    "verify_code": 22,      # 2字节 WORD 校验值
    "flags": 24,            # 2字节 BOOL 标志（同7.1字节24-25, 但bit4=开门灯）
    "vehicle_speed": 26,    # 2字节 WORD 车辆速度
}

# ============================================================
# ATP 安全输入/非安全输入 位定义
# ============================================================
# ATP安全输入 (UINT32, 4字节)
ATP_SAFE_INPUT = {
    "cab_active":      0x01000000,  # 本端驾驶室激活
    "key_active":      0x02000000,  # 本端司机钥匙激活
    "door_closed":     0x04000000,  # 车门关闭且锁闭
    "traction_cut":    0x08000000,  # 牵引已切断
    "train_complete":  0x10000000,  # 列车完整
    "eb_applied":      0x20000000,  # 列车已实施紧急制动
    "hold_brake":      0x40000000,  # 已实施保持制动
    "handle_zero_forward": 0x80000000,  # 牵引制动手柄在零位且方向手柄在向前位
    "confirm_btn":     0x00010000,  # 确认按钮按下
    "brake_fault":     0x00020000,  # 制动重故障
    "emergency_device":0x00040000,  # 车辆紧急操作装置激活
    "obstacle_detect": 0x00080000,  # 障碍物检测激活
    "escape_door":     0x00100000,  # 逃生门激活
    "escape_cover":    0x00200000,  # 逃生门封盖
    "dir_forward":     0x00400000,  # 方向手柄向前
    "dir_backward":    0x00800000,  # 方向手柄向后
}

# ATP非安全输入 (UINT32, 4字节)
ATP_NONSAFE_INPUT = {
    "eum_active":      0x00000100,  # EUM开关激活
    "ato_start_btn":   0x00000200,  # ATO启动按钮已按下
    "mode_up":         0x00000400,  # 模式升选择
    "mode_down":       0x00000800,  # 模式降选择
    "ar_btn":          0x00001000,  # AR按钮按下
    "right_door_open": 0x00002000,  # 右门开门按钮按下
    "right_door_close":0x00004000,  # 右门关门按钮按下
    "left_door_open":  0x00008000,  # 左门开门按钮按下
    "left_door_close": 0x00000001,  # 左门关门按钮按下
    "master_traction": 0x00000002,  # 司控器在牵引位
    "master_zero":     0x00000004,  # 司控器在零位
    "fire_alarm":      0x00000008,  # 烟火报警
}

# ATO非安全输入 (UINT32, 4字节)
ATO_NONSAFE_INPUT = {
    "door_mode_aa":   0x01000000,  # 门模式AA
    "door_mode_am":   0x02000000,  # 门模式AM
    "door_mode_mm":   0x04000000,  # 门模式MM
    "maintenance_btn":0x08000000,  # 检修按钮状态
    "sleep_btn":      0x10000000,  # 休眠按钮状态
    "wakeup_btn":     0x20000000,  # 唤醒按钮状态
    "battery_ok":     0x40000000,  # 蓄电池欠压状态（1:正常，0:欠压）
}

# ============================================================
# ATP 安全输出/非安全输出 位定义
# ============================================================
# ATP安全输出 (UINT32, 4字节)
ATP_SAFE_OUTPUT = {
    "left_door_enable":  0x01000000,  # 左门使能
    "right_door_enable": 0x02000000,  # 右门使能
    "eb_output":         0x04000000,  # 紧急制动输出
    "traction_cut_out":  0x08000000,  # 牵引切除输出
    "zero_speed":        0x10000000,  # 零速信号
    "train_start_light": 0x20000000,  # 车启动灯
    "escape_door_enable":0x40000000,  # 逃生门使能
    "ato_enable_1":      0x80000000,  # ATO使能输出1
    "ato_enable_2":      0x00010000,  # ATO使能输出2
}

# ATP非安全输出 (UINT32, 4字节)
ATP_NONSAFE_OUTPUT = {
    "ar_indicator":   0x00000100,  # AR指示灯输出
    "non_key_cab":    0x00000200,  # 非钥匙驾驶室激活（AR继电器）
    "fam_mode":       0x00000400,  # FAM模式输出
    "cam_mode":       0x00000800,  # CAM模式输出
    "parking_brake":  0x00001000,  # 停放制动施加输出(1:施加，0:不施加)
}

# ATO非安全输出 (UINT32, 4字节)
ATO_NONSAFE_OUTPUT = {
    "ato_active":     0x01000000,  # ATO激活状态
    "traction_cmd":   0x02000000,  # 牵引命令
    "brake_cmd":      0x04000000,  # 制动命令
    "hold_brake":     0x08000000,  # 保持制动
    "open_left_door": 0x10000000,  # 开左门
    "close_left_door":0x20000000,  # 关左门
    "open_right_door":0x40000000,  # 开右门
    "close_right_door":0x80000000, # 关右门
    "ato_start_light":0x00010000,  # ATO启动灯
    "sleep_output":   0x00020000,  # 休眠输出
    "wakeup_output":  0x00040000,  # 唤醒输出
    "dir_forward":    0x00080000,  # 方向向前
    "dir_backward":   0x00100000,  # 方向向后
}

# ============================================================
# 驾驶模式枚举
# ============================================================
DRIVE_MODE = {
    "INIT": 0,        # 初始
    "RD": 2,          # 限制人工驾驶模式 (Restricted Manual)
    "RM": 3,          # 人工驾驶模式 (Manual)
    "CM": 4,          # 受控人工驾驶模式 (Controlled Manual)
    "AM": 5,          # 自动驾驶模式 (Automatic)
    "AR": 6,          # 自动折返模式 (Automatic Reversal)
    "EUM": 7,         # 非限制人工驾驶模式 (Emergency Unrestricted Manual)
    "CAM": 8,         # 受控人工驾驶模式 (Controlled Automatic)
    "FAM": 9,         # 全自动运行模式 (Full Automatic)
}

# 运行等级
RUN_LEVEL = {
    "INIT": 0,        # 初始
    "BLOC": 1,        # 基于点式通信
    "CBTC": 2,        # 基于连续通信
    "IL": 3,          # 联锁
}

# 最大可用驾驶模式
MAX_DRIVE_MODE = {
    "INIT": 0,
    "RM": 3,
    "BLOC_CM": 9,
    "CBTC_CM": 10,
    "BLOC_AM": 11,
    "CBTC_AM": 12,
    "CBTC_FAM": 13,
}

# ============================================================
# 信号机状态
# ============================================================
SIGNAL_ASPECT = {
    "DEFAULT": 0x00,
    "RED":       0x01,   # 红灯
    "YELLOW":    0x02,   # 黄灯
    "RED_YELLOW":0x03,   # 红黄灯
    "GREEN":     0x04,   # 绿灯
    "YELLOW_OFF":0x05,   # 黄灭
    "RED_OFF":   0x06,   # 红灭
    "GREEN_OFF": 0x07,   # 绿灭
    "WHITE":     0x08,   # 白灯
    "RED_BROKEN":0x09,   # 红断
    "BLUE":      0x0A,   # 蓝灯
    "GREEN_BROKEN":0x10, # 绿断
    "YELLOW_BROKEN":0x20,# 黄断
    "WHITE_BROKEN":0x30, # 白断
}

# 道岔状态
SWITCH_STATE = {
    "DEFAULT": 0x00,  # 默认状态
    "NORMAL": 0x01,   # 道岔定位
    "REVERSE": 0x02,  # 道岔反位
    "FOUR_OPEN": 0x04,# 道岔四开
}

# ============================================================
# 列车运行方向
# ============================================================
TRAIN_DIRECTION = {
    "UP": 0x55,     # 上行方向
    "DOWN": 0xAA,   # 下行方向
    "INVALID": 0xFF, # 无效
}

# 牵引制动命令
TRACTION_BRAKE = {
    "TRACTION": 0x55,  # 牵引状态
    "BRAKE": 0xAA,     # 制动状态
    "INVALID": 0x00,   # 其他/无效
}