"""
司机台联动测试 — 通信参数配置
==================================
所有IP/端口/超时参数集中管理，按需修改。
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

# 上位机发送给 PLC（无固定周期，26字节）
UPPER_TO_PLC_LEN = 26

# ============================================================
# 网络屏协议（司机驾驶模拟台网络屏）
# ============================================================
NETWORK_SCREEN_IP = "192.168.100.122"
NETWORK_SCREEN_PORT = 8888
NETWORK_SCREEN_LEN = 572  # 总长572字节

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

# 上位机 → PLC (26字节)
UPPER_OFFSET = {
    "header": 0,            # 2字节 报文头
    "traction_cmd": 2,      # 2字节 牵引制动命令
    "traction_pct": 4,      # 2字节 牵引百分比 (%)
    "brake_pct": 6,         # 2字节 制动百分比 (%)
    "target_speed": 8,      # 4字节 目标速度 (cm/s)
    "door_cmd": 12,         # 2字节 门控命令
    "ato_cmd": 14,          # 2字节 ATO命令
    "eb_reset": 16,         # 2字节 紧急制动复位
    "reserved": 18,         # 8字节 预留
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