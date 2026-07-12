#!/usr/bin/env python3
"""
司机台全数据监听器
====================
统一读取并显示司机台可提供的全部数据：

  1. PLC 实时状态（TCP :8001，每100ms推送）
  2. 驾驶台开关量输入（UDP :9000，ATP/ATO 35个信号位）
  3. 网络屏显示数据（TCP :8888，上位机→司机台，可选）
  4. 信号屏DMI显示数据（TCP :9999，上位机→司机台，可选）

用法：
  python -m driver_cab_test.listen_cab_all            # 仅监听PLC+UDP
  python -m driver_cab_test.listen_cab_all --net      # +网络屏
  python -m driver_cab_test.listen_cab_all --signal   # +信号屏
  python -m driver_cab_test.listen_cab_all --all      # 全部监听
"""

import socket
import threading
import time
import os
import sys
import argparse
from typing import Optional
from dataclasses import dataclass, field, asdict

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from driver_cab_test.config import (
    PLC_SERVER_IP, PLC_PORT_A,
    NETWORK_SCREEN_IP, NETWORK_SCREEN_PORT,
    SIGNAL_SCREEN_IP, SIGNAL_SCREEN_PORT,
    DB_NODE_IP, DB_NODE_PORT,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    NETWORK_SCREEN_LEN, SIGNAL_SCREEN_LEN,
    DRIVE_MODE, TRACTION_BRAKE, TRAIN_DIRECTION,
    ATP_SAFE_INPUT, ATP_NONSAFE_INPUT, ATO_NONSAFE_INPUT,
    ATP_SAFE_OUTPUT, ATP_NONSAFE_OUTPUT, ATO_NONSAFE_OUTPUT,
)
from driver_cab_test.protocols import (
    parse_plc_to_upper,
    parse_network_screen,
    parse_signal_screen,
    parse_db_to_signal_cab_binary,
    parse_signal_to_db_cab_binary,
    _decode_bits,
)

# ====================================================================
# 全局状态
# ====================================================================

@dataclass
class CabAllData:
    """司机台全数据快照"""
    # PLC 状态
    plc: dict = field(default_factory=dict)
    plc_time: float = 0.0
    # 驾驶台开关量输入（司机操作 → 信号系统）
    cab_input: dict = field(default_factory=dict)
    cab_input_time: float = 0.0
    # 信号系统输出（信号系统 → 司机台显示）
    signal_output: dict = field(default_factory=dict)
    signal_output_time: float = 0.0
    # 网络屏显示数据
    network_screen: dict = field(default_factory=dict)
    network_time: float = 0.0
    # 信号屏显示数据
    signal_screen: dict = field(default_factory=dict)
    signal_time: float = 0.0
    # 连接状态
    plc_connected: bool = False
    udp_ready: bool = False
    net_connected: bool = False
    sig_connected: bool = False

    def age(self, t: float) -> str:
        """获取数据龄期（秒）"""
        ages = []
        if self.plc_time:
            ages.append(f"PLC={t - self.plc_time:.1f}s")
        if self.cab_input_time:
            ages.append(f"输入={t - self.cab_input_time:.1f}s")
        if self.signal_output_time:
            ages.append(f"输出={t - self.signal_output_time:.1f}s")
        if self.network_time:
            ages.append(f"网络屏={t - self.network_time:.1f}s")
        if self.signal_time:
            ages.append(f"信号屏={t - self.signal_time:.1f}s")
        return ", ".join(ages) if ages else "无数据"


data = CabAllData()
_lock = threading.Lock()


def update_plc(parsed: dict):
    with _lock:
        data.plc = parsed
        data.plc_time = time.time()


def update_cab_input(parsed: dict):
    with _lock:
        data.cab_input = parsed
        data.cab_input_time = time.time()


def update_signal_output(parsed: dict):
    with _lock:
        data.signal_output = parsed
        data.signal_output_time = time.time()


def update_network(parsed: dict):
    with _lock:
        data.network_screen = parsed
        data.network_time = time.time()


def update_signal_screen(parsed: dict):
    with _lock:
        data.signal_screen = parsed
        data.signal_time = time.time()


# ====================================================================
# 1. PLC 监听线程（TCP 客户端）
# ====================================================================

def plc_listener(stop_event: threading.Event):
    """连接 PLC 并接收 46 字节状态报文"""
    global data
    while not stop_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((PLC_SERVER_IP, PLC_PORT_A))
            with _lock:
                data.plc_connected = True
            print(f"  ✓ PLC 已连接: {PLC_SERVER_IP}:{PLC_PORT_A}")

            while not stop_event.is_set():
                try:
                    raw = sock.recv(PLC_TO_UPPER_LEN, socket.MSG_WAITALL)
                except Exception:
                    raw = sock.recv(PLC_TO_UPPER_LEN)

                if not raw or len(raw) < PLC_TO_UPPER_LEN:
                    break
                parsed = parse_plc_to_upper(raw[:PLC_TO_UPPER_LEN])
                update_plc(parsed)

            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            with _lock:
                data.plc_connected = False
            if not stop_event.is_set():
                time.sleep(2)
        except Exception as e:
            with _lock:
                data.plc_connected = False
            if not stop_event.is_set():
                time.sleep(2)


# ====================================================================
# 2. UDP 监听线程（驾驶台开关量）
# ====================================================================

def udp_listener(stop_event: threading.Event):
    """监听 UDP 驾驶台开关量报文（信号系统 ↔ 总控数据库）"""
    global data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0)
        sock.bind(("0.0.0.0", DB_NODE_PORT))
        with _lock:
            data.udp_ready = True
        print(f"  ✓ UDP 监听启动: 0.0.0.0:{DB_NODE_PORT}")

        while not stop_event.is_set():
            try:
                raw, addr = sock.recvfrom(1024)
            except socket.timeout:
                continue

            if len(raw) < 14:
                continue

            header = raw[0:2]
            # 0xFF 0xF0 = 列车数据, 0xFF 0xF1 = 驾驶台开关量
            if header == b"\xff\xf0":
                continue  # 列车数据，暂不处理
            elif header == b"\xff\xf1":
                # 判断方向：源标识决定
                src = raw[2:10]
                db_sig = b"\x01\x00\x01\x00\x01\x00\x01\x00"  # 总控→信号 = 驾驶台输入
                sig_db = b"\x00\x10\x00\x10\x00\x10\x00\x10"  # 信号→总控 = 信号系统输出

                if src == db_sig and len(raw) >= 29:
                    # 总控→信号：驾驶台开关量输入（司机操作）
                    parsed = parse_db_to_signal_cab_binary(raw[:29])
                    update_cab_input(parsed)
                elif src == sig_db and len(raw) >= 33:
                    # 信号→总控：信号系统输出（含车辆输出）
                    parsed = parse_signal_to_db_cab_binary(raw[:33])
                    update_signal_output(parsed)

    except OSError as e:
        print(f"  ✗ UDP 监听启动失败: {e}")
    finally:
        with _lock:
            data.udp_ready = False


# ====================================================================
# 3. 网络屏监听线程（TCP 客户端，接收上位机→司机台的数据）
# ====================================================================

def net_screen_listener(stop_event: threading.Event):
    """连接网络屏并接收 572 字节显示数据"""
    global data
    while not stop_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((NETWORK_SCREEN_IP, NETWORK_SCREEN_PORT))
            with _lock:
                data.net_connected = True
            print(f"  ✓ 网络屏已连接: {NETWORK_SCREEN_IP}:{NETWORK_SCREEN_PORT}")

            while not stop_event.is_set():
                try:
                    raw = sock.recv(NETWORK_SCREEN_LEN)
                except Exception:
                    raw = sock.recv(NETWORK_SCREEN_LEN)
                if not raw or len(raw) < NETWORK_SCREEN_LEN:
                    break
                parsed = parse_network_screen(raw[:NETWORK_SCREEN_LEN])
                update_network(parsed)

            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError):
            with _lock:
                data.net_connected = False
            if not stop_event.is_set():
                time.sleep(2)
        except Exception:
            with _lock:
                data.net_connected = False
            if not stop_event.is_set():
                time.sleep(2)


# ====================================================================
# 4. 信号屏监听线程（TCP 客户端，接收上位机→司机台的数据）
# ====================================================================

def sig_screen_listener(stop_event: threading.Event):
    """连接信号屏并接收 66 字节 DMI 显示数据"""
    global data
    while not stop_event.is_set():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3.0)
            sock.connect((SIGNAL_SCREEN_IP, SIGNAL_SCREEN_PORT))
            with _lock:
                data.sig_connected = True
            print(f"  ✓ 信号屏已连接: {SIGNAL_SCREEN_IP}:{SIGNAL_SCREEN_PORT}")

            buffer = b""
            while not stop_event.is_set():
                try:
                    chunk = sock.recv(1024)
                except Exception:
                    chunk = sock.recv(1024)
                if not chunk:
                    break
                buffer += chunk
                while len(buffer) >= SIGNAL_SCREEN_LEN:
                    pkt = buffer[:SIGNAL_SCREEN_LEN]
                    buffer = buffer[SIGNAL_SCREEN_LEN:]
                    parsed = parse_signal_screen(pkt)
                    update_signal_screen(parsed)

            sock.close()
        except (socket.timeout, ConnectionRefusedError, OSError):
            with _lock:
                data.sig_connected = False
            if not stop_event.is_set():
                time.sleep(2)
        except Exception:
            with _lock:
                data.sig_connected = False
            if not stop_event.is_set():
                time.sleep(2)


# ====================================================================
# 显示格式化
# ====================================================================

MODE_REV = {v: k for k, v in DRIVE_MODE.items()}
TRACTION_REV = {v: k for k, v in TRACTION_BRAKE.items()}


def _format_bits(bits: dict, columns: int = 4) -> str:
    """将开关量字典格式化为表格"""
    if not bits:
        return "    (无数据)"
    items = sorted(bits.items())
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


def _format_mode(mode_val: int) -> str:
    return MODE_REV.get(mode_val, f"未知({mode_val})")


def display():
    """定时刷新显示全部数据"""
    while True:
        with _lock:
            now = time.time()
            d = CabAllData(**asdict(data))  # 快照
            d.plc_time = data.plc_time
            d.cab_input_time = data.cab_input_time
            d.signal_output_time = data.signal_output_time
            d.network_time = data.network_time
            d.signal_time = data.signal_time

        # 清屏
        os.system("cls" if os.name == "nt" else "clear")

        print("=" * 72)
        print("  司机台全数据监听器   (按 Ctrl+C 退出)")
        print("=" * 72)
        print(f"  数据龄期: {d.age(now)}")
        print(f"  连接状态: ", end="")
        status = []
        status.append(f"PLC={'✓' if d.plc_connected else '✗'}")
        status.append(f"UDP={'✓' if d.udp_ready else '✗'}")
        if d.net_connected:
            status.append("网络屏=✓")
        if d.sig_connected:
            status.append("信号屏=✓")
        print(" | ".join(status))
        print("-" * 72)

        # ============================================================
        # 1. PLC 实时状态
        # ============================================================
        print("【1. PLC 实时状态】")
        if d.plc:
            speed_kmh = d.plc.get("speed_cm_s", 0) / 100.0
            accel_ms2 = d.plc.get("accel", 0) / 100.0
            mode_str = _format_mode(d.plc.get("mode", 0))
            print(f"   速度: {speed_kmh:>6.1f} km/h    "
                  f"加速度: {accel_ms2:>+5.2f} m/s²")
            print(f"   驾驶室: {'● 激活' if d.plc.get('cab_active') else '○ 关闭'}    "
                  f"钥匙: {'● 开' if d.plc.get('key_status') else '○ 关'}    "
                  f"紧急制动: {'● 施加' if d.plc.get('eb_status') else '○ 解除'}")
            print(f"   驾驶模式: {mode_str:10s}    "
                  f"司控器: {d.plc.get('master_controller', 0)}    "
                  f"制动缸压力: {d.plc.get('brake_pressure', 0)}")
            print(f"   车门: {'● 开' if d.plc.get('door_status') else '○ 关'}    "
                  f"列车ID: {d.plc.get('train_id', '-')}")
        else:
            print("   (等待数据...)")
        print()

        # ============================================================
        # 2. 驾驶台开关量输入（司机操作 → 信号系统）
        # ============================================================
        print("【2. 驾驶台开关量输入（司机操作 → 信号系统）】")
        if d.cab_input:
            inp = d.cab_input
            print("  ATP安全输入:")
            print(_format_bits(inp.get("atp_safe_bits", {}), 4))
            print("  ATP非安全输入:")
            print(_format_bits(inp.get("atp_nonsafe_bits", {}), 4))
            print("  ATO非安全输入:")
            print(_format_bits(inp.get("ato_nonsafe_bits", {}), 4))
            print(f"  (原始: atp_safe=0x{inp.get('atp_safe_input', 0):08x}  "
                  f"atp_nonsafe=0x{inp.get('atp_nonsafe_input', 0):08x}  "
                  f"ato_nonsafe=0x{inp.get('ato_nonsafe_input', 0):08x})")
        else:
            print("   (等待数据...)")
        print()

        # ============================================================
        # 3. 信号系统输出（信号系统 → 司机台显示）
        # ============================================================
        print("【3. 信号系统输出（信号系统 → 司机台）】")
        if d.signal_output:
            out = d.signal_output
            print("  ATP安全输出:")
            print(_format_bits(out.get("atp_safe_bits", {}), 4))
            print("  ATP非安全输出:")
            print(_format_bits(out.get("atp_nonsafe_bits", {}), 4))
            print("  ATO非安全输出:")
            print(_format_bits(out.get("ato_nonsafe_bits", {}), 4))
            vehicle = out.get("vehicle_output", 0)
            if vehicle:
                print(f"  车辆输出: 0x{vehicle:08x}")
        else:
            print("   (等待数据...)")
        print()

        # ============================================================
        # 4. 网络屏显示数据
        # ============================================================
        if d.network_screen:
            ns = d.network_screen
            print("【4. 网络屏显示数据】")
            print(f"   当前速度: {ns.get('speed_km_h', 0):>6.1f} km/h    "
                  f"目标速度: {ns.get('target_speed_km_h', 0):>6.1f} km/h    "
                  f"限速: {ns.get('limit_speed_km_h', 0):>6.1f} km/h")
            print(f"   下一站: {ns.get('next_station', '--')}    "
                  f"驾驶模式: {ns.get('mode_name', '--')}    "
                  f"列车ID: {ns.get('train_id', '-')}")
            print()
        elif d.net_connected:
            print("【4. 网络屏显示数据】   (等待数据...)")
            print()

        # ============================================================
        # 5. 信号屏（DMI）显示数据
        # ============================================================
        if d.signal_screen:
            ss = d.signal_screen
            print("【5. 信号屏（DMI）显示数据】")
            print(f"   当前速度: {ss.get('current_speed_km_h', 0):>6.1f} km/h    "
                  f"允许速度: {ss.get('permit_speed_km_h', 0):>6.1f} km/h    "
                  f"EBI速度: {ss.get('eb_trigger_speed_km_h', 0):>6.1f} km/h")
            print(f"   目标速度: {ss.get('target_speed_km_h', 0):>6.1f} km/h    "
                  f"目标距离: {ss.get('target_distance_m', 0):>8.0f} m    "
                  f"限速变化点: {ss.get('speed_change_distance_m', 0):>8.0f} m")
            print(f"   驾驶模式: {ss.get('current_mode', '--')}    "
                  f"信号机: {ss.get('signal_aspect', '--')}    "
                  f"下一信号机ID: {ss.get('next_signal_id', '-')}")
            print()
        elif d.sig_connected:
            print("【5. 信号屏（DMI）显示数据】   (等待数据...)")
            print()

        print("-" * 72)
        print(f"  刷新时间: {time.strftime('%H:%M:%S')}  |  "
              f"按 Ctrl+C 退出")
        print("=" * 72)

        time.sleep(0.5)  # 刷新间隔


# ====================================================================
# 主入口
# ====================================================================

def main():
    parser = argparse.ArgumentParser(description="司机台全数据监听器")
    parser.add_argument("--net", action="store_true", help="同时监听网络屏数据")
    parser.add_argument("--signal", action="store_true", help="同时监听信号屏数据")
    parser.add_argument("--all", action="store_true", help="监听全部数据源")
    args = parser.parse_args()

    listen_net = args.net or args.all
    listen_signal = args.signal or args.all

    stop_event = threading.Event()

    print("=" * 72)
    print("  司机台全数据监听器")
    print("=" * 72)
    print("  启动中...")
    print()

    # 启动线程
    threads = []

    t_plc = threading.Thread(target=plc_listener, args=(stop_event,), daemon=True)
    t_plc.start()
    threads.append(t_plc)

    t_udp = threading.Thread(target=udp_listener, args=(stop_event,), daemon=True)
    t_udp.start()
    threads.append(t_udp)

    if listen_net:
        t_net = threading.Thread(target=net_screen_listener, args=(stop_event,), daemon=True)
        t_net.start()
        threads.append(t_net)
        print("  ○ 网络屏监听: 已启用")
    else:
        print("  ○ 网络屏监听: 未启用 (加 --net 或 --all 启用)")

    if listen_signal:
        t_sig = threading.Thread(target=sig_screen_listener, args=(stop_event,), daemon=True)
        t_sig.start()
        threads.append(t_sig)
        print("  ○ 信号屏监听: 已启用")
    else:
        print("  ○ 信号屏监听: 未启用 (加 --signal 或 --all 启用)")

    print()
    print("  等待数据... (确保 cab_simulator 或真实硬件已运行)")
    time.sleep(1)

    try:
        display()
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        stop_event.set()
        print("监听器已停止")


if __name__ == "__main__":
    main()