#!/usr/bin/env python3
"""
监听 PLC 数据（只接收，不发送）
=================================
连接司机台 PLC，只收不发，观察当前数据状态。
用于验证内网连通性和 PLC 数据格式。
"""

import socket
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from driver_cab_test.config import PLC_SERVER_IP, PLC_PORT_A, PLC_TO_UPPER_LEN
from driver_cab_test.protocols import parse_plc_to_upper

PLC_ADDR = (PLC_SERVER_IP, PLC_PORT_A)

def main():
    print(f"正在连接 PLC: {PLC_SERVER_IP}:{PLC_PORT_A} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect(PLC_ADDR)
        print(f"✓ 连接成功！开始接收数据（每100ms一包，共收20包）\n")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        # 尝试 ping
        print("\n尝试 ping 测试...")
        ret = os.system(f"ping -n 2 {PLC_SERVER_IP} > nul 2>&1")
        if ret == 0:
            print(f"  Ping {PLC_SERVER_IP} 可达，但端口 {PLC_PORT_A} 可能未开放或被防火墙阻断")
        else:
            print(f"  Ping {PLC_SERVER_IP} 不通，请检查网络连接")
        sock.close()
        return

    try:
        for i in range(20):
            try:
                data = sock.recv(PLC_TO_UPPER_LEN, socket.MSG_WAITALL)
            except:
                data = sock.recv(PLC_TO_UPPER_LEN)

            if not data or len(data) < PLC_TO_UPPER_LEN:
                print(f"  [{i+1}] 收到 {len(data) if data else 0} 字节（不足46，可能断开）")
                break

            parsed = parse_plc_to_upper(data[:PLC_TO_UPPER_LEN])

            # 关键信息摘录
            speed_kmh = parsed["speed_cm_s"] / 100.0
            print(
                f"  [{i+1:2d}] 速度={speed_kmh:6.1f}km/h  "
                f"驾驶室={'激活' if parsed['cab_active'] else '关闭'}  "
                f"钥匙={'开' if parsed['key_status'] else '关'}  "
                f"紧急制动={'施加' if parsed['eb_status'] else '解除'}  "
                f"模式={parsed['mode']}  "
                f"制动缸压力={parsed['brake_pressure']}"
            )

    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"接收异常: {e}")
    finally:
        sock.close()
        print("\n连接已关闭")


if __name__ == "__main__":
    main()