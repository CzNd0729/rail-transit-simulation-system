"""
PLC 模拟服务器
=================
模拟真实司机驾驶模拟台 PLC，通过 TCP 协议与上位机通信。

- 作为 TCP Server 监听 8001/8002/8003 端口
- 周期（100ms）发送 46 字节数据给上位机
- 接收上位机 26 字节控制指令
"""

import socket
import threading
import struct
import time
import logging
from typing import Optional

from .config import (
    PLC_SERVER_IP, PLC_PORT_A, PLC_PORT_B, PLC_PORT_C,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    SIM_CYCLE_INTERVAL, DRIVE_MODE,
)
from .protocols import pack_plc_to_upper, parse_upper_to_plc

logger = logging.getLogger(__name__)


class PlcSimulator:
    """PLC 模拟器"""

    def __init__(self, host: str = "0.0.0.0", port: int = PLC_PORT_A):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_addr: Optional[tuple] = None
        self.running = False

        # 模拟状态
        self.train_id = 1
        self.speed_cm_s = 0
        self.accel = 0
        self.master_controller = 0
        self.brake_pressure = 0
        self.door_status = 0
        self.cab_active = 0
        self.key_status = 0
        self.eb_status = 0
        self.mode = DRIVE_MODE["INIT"]

        # 接收到的上位机命令
        self.last_upper_cmd: Optional[dict] = None

        # 回调：收到上位机数据时触发
        self.on_upper_data = None

    def start(self):
        """启动 PLC 服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.server_socket.settimeout(1.0)
        self.running = True
        logger.info(f"PLC模拟器 启动: {self.host}:{self.port}")

        # 接收客户端连接线程
        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()

        # 周期发送线程
        send_thread = threading.Thread(target=self._send_loop, daemon=True)
        send_thread.start()

    def stop(self):
        """停止 PLC 服务器"""
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

    def _accept_loop(self):
        """接受客户端连接循环"""
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                self.client_socket = client
                self.client_addr = addr
                logger.info(f"上位机已连接: {addr}")

                # 接收线程
                recv_thread = threading.Thread(target=self._recv_loop, args=(client,), daemon=True)
                recv_thread.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _recv_loop(self, client: socket.socket):
        """接收上位机数据循环"""
        buffer = b""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    logger.info("上位机已断开连接")
                    self.client_socket = None
                    self.client_addr = None
                    break
                buffer += data
                # 解析 26 字节报文
                while len(buffer) >= UPPER_TO_PLC_LEN:
                    pkt = buffer[:UPPER_TO_PLC_LEN]
                    buffer = buffer[UPPER_TO_PLC_LEN:]
                    try:
                        cmd = parse_upper_to_plc(pkt)
                        self.last_upper_cmd = cmd
                        logger.debug(f"收到上位机指令: {cmd}")
                        if self.on_upper_data:
                            self.on_upper_data(cmd)
                    except Exception as e:
                        logger.warning(f"解析上位机报文失败: {e}")
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                logger.info(f"上位机连接异常: {e}")
                self.client_socket = None
                self.client_addr = None
                break

    def _send_loop(self):
        """周期发送数据给上位机"""
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
        """构建当前状态报文"""
        return pack_plc_to_upper(
            train_id=self.train_id,
            speed_cm_s=self.speed_cm_s,
            accel=self.accel,
            master_controller=self.master_controller,
            brake_pressure=self.brake_pressure,
            door_status=self.door_status,
            cab_active=self.cab_active,
            key_status=self.key_status,
            eb_status=self.eb_status,
            mode=self.mode,
        )

    def set_speed(self, speed_cm_s: int):
        """设置列车速度"""
        self.speed_cm_s = max(0, speed_cm_s)

    def set_accel(self, accel: int):
        self.accel = accel

    def set_brake_pressure(self, pressure: int):
        self.brake_pressure = max(0, min(1023, pressure))

    def set_cab_active(self, active: bool):
        self.cab_active = 1 if active else 0

    def set_key_status(self, status: bool):
        self.key_status = 1 if status else 0

    def set_eb_status(self, active: bool):
        self.eb_status = 1 if active else 0

    def set_mode(self, mode: int):
        self.mode = mode

    def set_door_status(self, status: int):
        self.door_status = status & 0xFFFF

    def get_last_command(self) -> Optional[dict]:
        """获取最近一次上位机指令"""
        return self.last_upper_cmd


def run_plc_simulator(port: int = PLC_PORT_A):
    """运行独立 PLC 模拟器"""
    logging.basicConfig(
        level=logging.INFO,
        format="[PLC] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    sim = PlcSimulator(port=port)
    sim.start()

    print(f"\nPLC模拟器运行中 (端口 {port})")
    print("  按 Enter 停止模拟器")
    print("  在控制台输入命令可改变模拟状态:")
    print("    speed <cm/s>  - 设置速度")
    print("    eb 0/1        - 设置紧急制动")
    print("    cab 0/1       - 设置驾驶室激活")
    print("    key 0/1       - 设置钥匙状态")
    print("    mode <N>      - 设置驾驶模式")
    print("    status        - 显示当前状态")
    print("    quit          - 退出")
    print()

    try:
        while True:
            cmd = input("PLC> ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()

            if action == "quit" or action == "exit":
                break
            elif action == "speed" and len(parts) > 1:
                sim.set_speed(int(parts[1]))
                print(f"  速度已设为 {parts[1]} cm/s")
            elif action == "eb" and len(parts) > 1:
                sim.set_eb_status(int(parts[1]) == 1)
                print(f"  紧急制动: {'施加' if int(parts[1]) == 1 else '解除'}")
            elif action == "cab" and len(parts) > 1:
                sim.set_cab_active(int(parts[1]) == 1)
                print(f"  驾驶室: {'激活' if int(parts[1]) == 1 else '未激活'}")
            elif action == "key" and len(parts) > 1:
                sim.set_key_status(int(parts[1]) == 1)
                print(f"  钥匙: {'打开' if int(parts[1]) == 1 else '关闭'}")
            elif action == "mode" and len(parts) > 1:
                sim.set_mode(int(parts[1]))
                print(f"  驾驶模式已设为 {parts[1]}")
            elif action == "status":
                print(f"  速度: {sim.speed_cm_s} cm/s")
                print(f"  加速度: {sim.accel}")
                print(f"  驾驶室激活: {sim.cab_active}")
                print(f"  钥匙状态: {sim.key_status}")
                print(f"  紧急制动: {sim.eb_status}")
                print(f"  驾驶模式: {sim.mode}")
                print(f"  制动缸压力: {sim.brake_pressure}")
                if sim.last_upper_cmd:
                    print(f"  上位机指令: {sim.last_upper_cmd}")
            else:
                print(f"  未知命令: {cmd}")
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        sim.stop()


if __name__ == "__main__":
    run_plc_simulator()