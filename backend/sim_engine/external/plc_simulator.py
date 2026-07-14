"""PLC 模拟器 — 模拟真实司机台 PLC 的行为。

**已弃用** — 外部系统接入方案已废弃，后端默认直接对接前端。
保留此文件仅作参考，不再维护。

作为 TCP 服务器，周期（100ms）发送 46 字节 7.1 报文给上位机，
同时接收上位机的 28 字节 7.2 控制指令。

用于本地开发测试，无需连接真实 PLC 硬件。

用法（仅作历史参考）:
  # 启动模拟器（默认端口 8001）
  python -m backend.sim_engine.external.plc_simulator

  # 指定端口 + 交互模式
  python -m backend.sim_engine.external.plc_simulator --port 8001 --interactive
"""

from __future__ import annotations

import logging
import socket
import threading
import time
from typing import Optional

from .protocol import PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN, PLC_PORT
from .plc_bridge import pack_plc_to_upper, parse_upper_to_plc

logger = logging.getLogger(__name__)

SIM_CYCLE_INTERVAL = 0.1  # 100ms


class PlcSimulator:
    """PLC 模拟器 — TCP 服务器，周期发送 7.1 报文，接收 7.2 指令。

    用法:
        sim = PlcSimulator()
        sim.start()
        # ... 运行一段时间 ...
        sim.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = PLC_PORT):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_addr: Optional[tuple] = None
        self.running = False

        # ---- 7.1 报文各字段初始值 ----
        self.year = 2026
        self.month = 7
        self.day = 13
        self.hour = 15
        self.minute = 30
        self.second = 0
        self.verify_type = 0
        self.verify_code = 0
        # 指示灯 (字节24)
        self.hscb = 0
        self.brake_fault = 0
        self.door_closed = 0
        self.net_fault = 0
        self.ar_available = 0
        # 模式 (字节25)
        self.ato_available = 0
        self.wash_mode = 0
        self.ato_active = 0
        self.ar_active = 0
        # 速度
        self.vehicle_speed = 0
        # 按钮 (字节28)
        self.eb_button = 0
        self.bus_ctrl = 0
        self.forced_release = 0
        self.forced_pump = 0
        self.emergency_cmd = 0
        self.parking_apply = 0
        self.parking_release = 0
        self.horn = 0
        # 门控 (字节29)
        self.open_left_door = 0
        self.open_right_door = 0
        self.close_left_door = 0
        self.close_right_door = 0
        # 照明/门模式
        self.light_switch = 0
        self.door_mode_switch = 0
        # 按钮 (字节34)
        self.high_accel = 0
        self.cab_light = 0
        self.mode_up_confirm = 0
        self.mode_down_confirm = 0
        self.confirm_flag = 0
        self.ar_flag = 0
        self.traction_reset = 0
        self.ato_start = 0
        # 开关 (字节35)
        self.wash_switch = 0
        self.key_switch = 0
        self.alert_flag = 0
        self.alert_release = 0
        # 手柄
        self.dir_handle = 0
        self.main_handle = 0
        self.traction_level = 0
        self.brake_level = 0

        # 最近收到的上位机指令
        self.last_upper_cmd: Optional[dict] = None

    def start(self):
        """启动 PLC 模拟器。"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)
        self.running = True
        logger.info(f"PLC模拟器 启动: {self.host}:{self.port}")

        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        send_thread = threading.Thread(target=self._send_loop, daemon=True)
        accept_thread.start()
        send_thread.start()

    def stop(self):
        """停止模拟器。"""
        self.running = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception:
                pass
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("PLC模拟器 已停止")

    # ── 内部线程 ──────────────────────────────────────

    def _accept_loop(self):
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                self.client_socket = client
                self.client_addr = addr
                logger.info(f"上位机已连接: {addr}")
                recv_thread = threading.Thread(
                    target=self._recv_loop, args=(client,), daemon=True
                )
                recv_thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _recv_loop(self, client: socket.socket):
        buffer = b""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    logger.info("上位机已断开")
                    self.client_socket = None
                    self.client_addr = None
                    break
                buffer += data
                while len(buffer) >= UPPER_TO_PLC_LEN:
                    pkt = buffer[:UPPER_TO_PLC_LEN]
                    buffer = buffer[UPPER_TO_PLC_LEN:]
                    try:
                        cmd = parse_upper_to_plc(pkt)
                        self.last_upper_cmd = cmd
                        # 将上位机下发的速度回显到 7.1 报文中
                        speed = cmd.get("vehicle_speed", 0)
                        if speed is not None:
                            self.vehicle_speed = speed
                    except Exception as e:
                        logger.warning(f"解析上位机报文失败: {e}")
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                logger.info(f"上位机连接异常: {e}")
                self.client_socket = None
                self.client_addr = None
                break

    def _send_loop(self):
        while self.running:
            if self.client_socket:
                try:
                    data = self._build_packet()
                    self.client_socket.sendall(data)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    self.client_socket = None
                    self.client_addr = None
            time.sleep(SIM_CYCLE_INTERVAL)

    def _build_packet(self) -> bytes:
        return pack_plc_to_upper(
            year=self.year, month=self.month, day=self.day,
            hour=self.hour, minute=self.minute, second=self.second,
            verify_type=self.verify_type, verify_code=self.verify_code,
            hscb=self.hscb, brake_fault=self.brake_fault,
            door_closed=self.door_closed, net_fault=self.net_fault,
            ar_available=self.ar_available,
            ato_available=self.ato_available, wash_mode=self.wash_mode,
            ato_active=self.ato_active, ar_active=self.ar_active,
            vehicle_speed=self.vehicle_speed,
            eb_button=self.eb_button, bus_ctrl=self.bus_ctrl,
            forced_release=self.forced_release, forced_pump=self.forced_pump,
            emergency_cmd=self.emergency_cmd,
            parking_apply=self.parking_apply, parking_release=self.parking_release,
            horn=self.horn,
            open_left_door=self.open_left_door,
            open_right_door=self.open_right_door,
            close_left_door=self.close_left_door,
            close_right_door=self.close_right_door,
            light_switch=self.light_switch,
            door_mode_switch=self.door_mode_switch,
            high_accel=self.high_accel, cab_light=self.cab_light,
            mode_up_confirm=self.mode_up_confirm,
            mode_down_confirm=self.mode_down_confirm,
            confirm_flag=self.confirm_flag, ar_flag=self.ar_flag,
            traction_reset=self.traction_reset, ato_start=self.ato_start,
            wash_switch=self.wash_switch, key_switch=self.key_switch,
            alert_flag=self.alert_flag, alert_release=self.alert_release,
            dir_handle=self.dir_handle, main_handle=self.main_handle,
            traction_level=self.traction_level, brake_level=self.brake_level,
        )


def main():
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="[PLC模拟器] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="PLC 模拟器")
    parser.add_argument("--port", type=int, default=PLC_PORT, help="监听端口")
    parser.add_argument("--local", action="store_true", help="仅绑定 127.0.0.1")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    args = parser.parse_args()

    host = "127.0.0.1" if args.local else "0.0.0.0"
    sim = PlcSimulator(host=host, port=args.port)
    sim.start()

    print(f"\nPLC模拟器运行中 (端口 {args.port})")
    print(f"  绑定地址: {host}")
    print(f"  每100ms发送 46 字节 7.1 报文")
    print(f"  接收上位机 28 字节 7.2 报文")
    print(f"  Ctrl+C 停止\n")

    if not args.interactive:
        try:
            while sim.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            sim.stop()
        return

    # 交互模式
    print("  交互命令:")
    print("    speed <N>       车辆速度 (0-65535)")
    print("    eb 0/1          紧急制动按钮")
    print("    key 0/1         钥匙开关")
    print("    dir <N>         方向手柄 (0=0位 1=向前 2=向后)")
    print("    handle <N>      主手柄 (0=0位 1=牵引 2=制动 4=快制)")
    print("    traction <N>    牵引极位 (0-25600, 100%=25600)")
    print("    brake <N>       制动极位 (0-25600, 100%=25600)")
    print("    ato 0/1         ATO启动")
    print("    ol 0/1          开左门")
    print("    or 0/1          开右门")
    print("    status          显示状态")
    print("    quit            退出\n")

    try:
        while True:
            cmd = input("PLC> ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()

            if action in ("quit", "exit", "q"):
                break
            elif action == "speed" and len(parts) > 1:
                sim.vehicle_speed = int(parts[1])
                print(f"  速度 -> {parts[1]}")
            elif action == "eb" and len(parts) > 1:
                sim.eb_button = int(parts[1])
                print(f"  紧急制动: {'锁定' if int(parts[1]) else '解除'}")
            elif action == "key" and len(parts) > 1:
                sim.key_switch = int(parts[1])
                print(f"  钥匙: {'开' if int(parts[1]) else '关'}")
            elif action == "dir" and len(parts) > 1:
                sim.dir_handle = int(parts[1])
                d = {0: "0位", 1: "向前", 2: "向后"}
                print(f"  方向手柄: {d.get(int(parts[1]), parts[1])}")
            elif action == "handle" and len(parts) > 1:
                sim.main_handle = int(parts[1])
                h = {0: "0位", 1: "牵引", 2: "制动", 4: "快制"}
                print(f"  主手柄: {h.get(int(parts[1]), parts[1])}")
            elif action == "traction" and len(parts) > 1:
                sim.traction_level = int(parts[1])
                pct = int(parts[1]) / 256.0
                print(f"  牵引极位: {pct:.1f}%")
            elif action == "brake" and len(parts) > 1:
                sim.brake_level = int(parts[1])
                pct = int(parts[1]) / 256.0
                print(f"  制动极位: {pct:.1f}%")
            elif action == "ato" and len(parts) > 1:
                sim.ato_start = int(parts[1])
                print(f"  ATO启动: {'按下' if int(parts[1]) else '松开'}")
            elif action == "ol" and len(parts) > 1:
                sim.open_left_door = int(parts[1])
                print(f"  开左门: {'触发' if int(parts[1]) else '复位'}")
            elif action == "or" and len(parts) > 1:
                sim.open_right_door = int(parts[1])
                print(f"  开右门: {'触发' if int(parts[1]) else '复位'}")
            elif action == "status":
                print(f"  速度={sim.vehicle_speed} EB={sim.eb_button} 钥匙={sim.key_switch}")
                print(f"  手柄: dir={sim.dir_handle} main={sim.main_handle}")
                print(f"  极位: 牵引={sim.traction_level/256:.1f}% 制动={sim.brake_level/256:.1f}%")
                print(f"  连接: {'✓' if sim.client_socket else '✗'}")
            else:
                print(f"  未知命令: {cmd}")
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()


if __name__ == "__main__":
    main()