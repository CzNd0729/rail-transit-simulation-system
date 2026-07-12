#!/usr/bin/env python3
"""
监听 PLC 所有数据（7.1 节 46字节，只接收不发送）
===================================================
连接司机台 PLC，接收46字节报文，完整解析并显示全部字段。
用于验证内网连通性和 PLC 数据格式。

用法：
  python -m driver_cab_test.listen_plc              # 持续接收（每秒刷新）
  python -m driver_cab_test.listen_plc --count 100   # 接收100包后退出
  python -m driver_cab_test.listen_plc --interval 2  # 每2秒刷新一次
"""

import socket
import os
import sys
import argparse
import time

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from driver_cab_test.config import PLC_SERVER_IP, PLC_PORT_A, PLC_TO_UPPER_LEN
from driver_cab_test.protocols import parse_plc_to_upper


def _bool_str(val: bool) -> str:
    return "●" if val else "○"


def _format_flags(flags: dict, columns: int = 4) -> str:
    """格式化标志位为表格"""
    items = sorted(flags.items())
    lines = []
    row = []
    for name, val in items:
        icon = "●" if val else "○"
        row.append(f"  {icon} {name}")
        if len(row) >= columns:
            lines.append("".join(row))
            row = []
    if row:
        lines.append("".join(row))
    return "\n".join(lines)


def display_pkt(parsed: dict, index: int):
    """显示一包完整数据"""
    print(f"\n{'=' * 72}")
    print(f"  第 {index:2d} 包  |  {parsed['timestamp_str']}")
    print(f"{'=' * 72}")

    # ---- 报文头 ----
    print(f"【报文头】  identify={parsed['identify']}  "
          f"total_len={parsed['total_len']}B  data_len={parsed['data_len']}B  "
          f"校验={parsed['verify_type']}/{parsed['verify_code']}")

    # ---- 时间 ----
    print(f"【时间】    {parsed['timestamp_str']}")

    # ---- 指示灯标志 (字节24) ----
    print(f"【指示灯】  "
          f"高断合={_bool_str(parsed['hscb'])}  "
          f"制动缓解不良={_bool_str(parsed['brake_fault_indicator'])}  "
          f"门关好={_bool_str(parsed['door_closed_indicator'])}  "
          f"网络故障={_bool_str(parsed['net_fault_indicator'])}  "
          f"具备AR={_bool_str(parsed['ar_available'])}")

    # ---- 模式标志 (字节25) ----
    print(f"【模式标志】"
          f"  具备ATO={_bool_str(parsed['ato_available'])}  "
          f"洗车模式={_bool_str(parsed['wash_mode'])}  "
          f"ATO激活={_bool_str(parsed['ato_active'])}  "
          f"AR激活={_bool_str(parsed['ar_active'])}")

    # ---- 车辆速度 ----
    print(f"【车辆速度】 {parsed['vehicle_speed']} （上位机传来的速度值）")

    # ---- 按钮/标志 (字节28) ----
    flags_28 = {
        "紧急制动按钮锁定": parsed['eb_button_locked'],
        "母线控制按钮锁定": parsed['bus_ctrl_locked'],
        "强迫缓解": parsed['forced_release'],
        "强迫泵风": parsed['forced_pump'],
        "应急指挥按钮锁定": parsed['emergency_cmd_locked'],
        "停放制动施加": parsed['parking_apply'],
        "停放制动缓解": parsed['parking_release'],
        "电笛": parsed['horn'],
    }
    print(f"【按钮/标志(字节28)】")
    print(_format_flags(flags_28, 4))

    # ---- 门控标志 (字节29) ----
    flags_29 = {
        "开左门": parsed['open_left_door'],
        "开右门": parsed['open_right_door'],
        "关左门": parsed['close_left_door'],
        "关右门": parsed['close_right_door'],
    }
    print(f"【门控标志(字节29)】")
    print(_format_flags(flags_29, 4))

    # ---- 外部照明 / 门模式 ----
    print(f"【外部照明】 {parsed['light_switch_str']} ({parsed['light_switch']})  "
          f" 【门模式】 {parsed['door_mode_switch_str']} ({parsed['door_mode_switch']})")

    # ---- 按钮/标志 (字节34) ----
    flags_34 = {
        "高加速": parsed['high_accel'],
        "司机室照明": parsed['cab_light'],
        "模式升级确认": parsed['mode_up_confirm'],
        "模式降级确认": parsed['mode_down_confirm'],
        "确认": parsed['confirm_flag'],
        "自动折返": parsed['ar_flag'],
        "牵引辅助复位": parsed['traction_reset'],
        "ATO启动": parsed['ato_start_flag'],
    }
    print(f"【按钮/标志(字节34)】")
    print(_format_flags(flags_34, 4))

    # ---- 开关 (字节35) ----
    flags_35 = {
        "洗车模式开关": parsed['wash_switch'],
        "钥匙开关": parsed['key_switch'],
        "警惕": parsed['alert_flag'],
        "警惕允许解除": parsed['alert_release'],
    }
    print(f"【开关/标志(字节35)】")
    print(_format_flags(flags_35, 4))

    # ---- 手柄/极位 ----
    print(f"【手柄】  方向手柄={parsed['dir_handle_str']}  "
          f"主手柄={parsed['main_handle_str']}  "
          f"牵引极位={parsed['traction_level_pct']}%  "
          f"制动极位={parsed['brake_level_pct']}%")

    print(f"{'=' * 72}")


def main():
    parser = argparse.ArgumentParser(description="监听 PLC 全部数据（7.1 节 46字节，持续运行）")
    parser.add_argument("--count", type=int, default=0, help="接收 N 包后退出（默认持续运行）")
    parser.add_argument("--local", action="store_true", help="连接本地模拟器 (127.0.0.1)")
    parser.add_argument("--interval", type=float, default=1.0, help="显示刷新间隔（秒，默认1.0）")
    args = parser.parse_args()

    plc_ip = "127.0.0.1" if args.local else PLC_SERVER_IP
    PLC_ADDR = (plc_ip, PLC_PORT_A)
    max_packets = args.count if args.count > 0 else 999999

    print(f"连接 PLC: {plc_ip}:{PLC_PORT_A} ...")
    print(f"接收模式: {'持续接收（Ctrl+C 停止）' if args.count == 0 else f'接收 {args.count} 包后退出'}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect(PLC_ADDR)
        print(f"✓ 连接成功！开始接收数据（每100ms一包）\n")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        if args.local:
            print("\n提示：请先启动本地模拟器")
            print("  python -m driver_cab_test.plc_simulator --local")
        else:
            print("\n尝试 ping 测试...")
            ret = os.system(f"ping -n 2 {PLC_SERVER_IP} > nul 2>&1")
            if ret == 0:
                print(f"  Ping {PLC_SERVER_IP} 可达，但端口 {PLC_PORT_A} 可能未开放或被防火墙阻断")
            else:
                print(f"  Ping {PLC_SERVER_IP} 不通，请检查网络连接")
        sock.close()
        return

    try:
        last_display = 0.0
        i = 0
        while i < max_packets:
            try:
                data = sock.recv(PLC_TO_UPPER_LEN, socket.MSG_WAITALL)
            except Exception:
                data = sock.recv(PLC_TO_UPPER_LEN)

            if not data or len(data) < PLC_TO_UPPER_LEN:
                print(f"  [{i+1}] 收到 {len(data) if data else 0} 字节（不足46，可能断开）")
                break

            i += 1
            parsed = parse_plc_to_upper(data[:PLC_TO_UPPER_LEN])

            # 按 interval 刷新显示，不闪屏
            now = time.time()
            if now - last_display >= args.interval:
                last_display = now
                os.system("cls" if os.name == "nt" else "clear")
                display_pkt(parsed, i)

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"接收异常: {e}")
    finally:
        sock.close()
        print("\n连接已关闭")


if __name__ == "__main__":
    main()