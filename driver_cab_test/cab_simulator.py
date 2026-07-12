"""
司机台整体模拟器
===================
整合 PLC、网络屏、信号屏三个协议的模拟器，模拟完整的司机驾驶台。

- PLC 服务器（TCP 8001/8002/8003）：接收上位机指令，发送状态数据
- 网络屏服务器（TCP 8888）：接收显示数据
- 信号屏服务器（TCP 9999）：接收 DMI 显示数据
"""

import socket
import threading
import time
import logging
from typing import Optional

from .config import (
    PLC_SERVER_IP, PLC_PORT_A, PLC_PORT_B, PLC_PORT_C,
    NETWORK_SCREEN_IP, NETWORK_SCREEN_PORT,
    SIGNAL_SCREEN_IP, SIGNAL_SCREEN_PORT,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    NETWORK_SCREEN_LEN, SIGNAL_SCREEN_LEN,
    SIM_CYCLE_INTERVAL, DRIVE_MODE,
)
from .protocols import (
    pack_plc_to_upper, parse_upper_to_plc,
    parse_network_screen, parse_signal_screen,
)

logger = logging.getLogger(__name__)


class CabSimulator:
    """司机台综合模拟器"""

    def __init__(self):
        self.running = False

        # PLC 状态
        self.plc_state = {
            "train_id": 1,
            "speed_cm_s": 0,
            "accel": 0,
            "master_controller": 0,
            "brake_pressure": 0,
            "door_status": 0,
            "cab_active": 0,
            "key_status": 0,
            "eb_status": 0,
            "mode": DRIVE_MODE["INIT"],
        }
        self.last_upper_cmd: Optional[dict] = None

        # 网络屏数据（最近一次接收的）
        self.last_network_data: Optional[dict] = None

        # 信号屏数据（最近一次接收的）
        self.last_signal_data: Optional[dict] = None

        # 服务器 sockets
        self._plc_sockets: list[socket.socket] = []
        self._plc_clients: list[tuple[socket.socket, tuple]] = []
        self._net_socket: Optional[socket.socket] = None
        self._net_client: Optional[tuple[socket.socket, tuple]] = None
        self._sig_socket: Optional[socket.socket] = None
        self._sig_client: Optional[tuple[socket.socket, tuple]] = None

        # 回调
        self.on_upper_cmd = None       # 收到上位机→PLC指令
        self.on_network_data = None    # 收到网络屏数据
        self.on_signal_data = None     # 收到信号屏数据

    def start(self):
        """启动所有服务器"""
        self.running = True

        # PLC 服务器 (8001)
        self._start_plc_server(PLC_PORT_A)
        # PLC 辅助端口 (8002, 8003)
        self._start_plc_server(PLC_PORT_B)
        self._start_plc_server(PLC_PORT_C)

        # 网络屏服务器 (8888)
        self._start_net_server()

        # 信号屏服务器 (9999)
        self._start_sig_server()

        logger.info("司机台模拟器已启动")
        logger.info(f"  PLC:     :{PLC_PORT_A}/:{PLC_PORT_B}/:{PLC_PORT_C}")
        logger.info(f"  网络屏:  :{NETWORK_SCREEN_PORT}")
        logger.info(f"  信号屏:  :{SIGNAL_SCREEN_PORT}")

    def stop(self):
        """停止所有服务器"""
        self.running = False
        for sock, _ in self._plc_clients:
            try:
                sock.close()
            except Exception:
                pass
        for sock in self._plc_sockets:
            try:
                sock.close()
            except Exception:
                pass
        if self._net_client:
            try:
                self._net_client[0].close()
            except Exception:
                pass
        if self._net_socket:
            try:
                self._net_socket.close()
            except Exception:
                pass
        if self._sig_client:
            try:
                self._sig_client[0].close()
            except Exception:
                pass
        if self._sig_socket:
            try:
                self._sig_socket.close()
            except Exception:
                pass
        logger.info("司机台模拟器已停止")

    # ---- PLC 模拟 ----

    def _start_plc_server(self, port: int):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.listen(1)
        sock.settimeout(1.0)
        self._plc_sockets.append(sock)

        t = threading.Thread(target=self._plc_accept_loop, args=(sock, port), daemon=True)
        t.start()

    def _plc_accept_loop(self, sock: socket.socket, port: int):
        while self.running:
            try:
                client, addr = sock.accept()
                logger.info(f"PLC({port}) 上位机连接: {addr}")
                self._plc_clients.append((client, addr))

                recv_t = threading.Thread(target=self._plc_recv_loop, args=(client, addr), daemon=True)
                recv_t.start()

                send_t = threading.Thread(target=self._plc_send_loop, args=(client, addr), daemon=True)
                send_t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _plc_recv_loop(self, client: socket.socket, addr: tuple):
        buffer = b""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    break
                buffer += data
                while len(buffer) >= UPPER_TO_PLC_LEN:
                    pkt = buffer[:UPPER_TO_PLC_LEN]
                    buffer = buffer[UPPER_TO_PLC_LEN:]
                    try:
                        cmd = parse_upper_to_plc(pkt)
                        self.last_upper_cmd = cmd
                        logger.debug(f"PLC 收到上位机指令: {cmd}")
                        if self.on_upper_cmd:
                            self.on_upper_cmd(cmd)
                    except Exception as e:
                        logger.warning(f"解析上位机报文失败: {e}")
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break

        self._plc_clients = [(c, a) for c, a in self._plc_clients if c != client]
        try:
            client.close()
        except Exception:
            pass

    def _plc_send_loop(self, client: socket.socket, addr: tuple):
        while self.running:
            try:
                data = self._build_plc_packet()
                client.sendall(data)
            except (BrokenPipeError, ConnectionResetError, OSError):
                break
            time.sleep(SIM_CYCLE_INTERVAL)

    def _build_plc_packet(self) -> bytes:
        return pack_plc_to_upper(
            train_id=self.plc_state["train_id"],
            speed_cm_s=self.plc_state["speed_cm_s"],
            accel=self.plc_state["accel"],
            master_controller=self.plc_state["master_controller"],
            brake_pressure=self.plc_state["brake_pressure"],
            door_status=self.plc_state["door_status"],
            cab_active=self.plc_state["cab_active"],
            key_status=self.plc_state["key_status"],
            eb_status=self.plc_state["eb_status"],
            mode=self.plc_state["mode"],
        )

    # ---- 网络屏模拟 ----

    def _start_net_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", NETWORK_SCREEN_PORT))
        sock.listen(1)
        sock.settimeout(1.0)
        self._net_socket = sock

        t = threading.Thread(target=self._net_accept_loop, daemon=True)
        t.start()

    def _net_accept_loop(self):
        while self.running:
            try:
                client, addr = self._net_socket.accept()
                logger.info(f"网络屏 上位机连接: {addr}")
                self._net_client = (client, addr)

                t = threading.Thread(target=self._net_recv_loop, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _net_recv_loop(self, client: socket.socket):
        buffer = b""
        while self.running:
            try:
                data = client.recv(2048)
                if not data:
                    break
                buffer += data
                while len(buffer) >= NETWORK_SCREEN_LEN:
                    pkt = buffer[:NETWORK_SCREEN_LEN]
                    buffer = buffer[NETWORK_SCREEN_LEN:]
                    try:
                        parsed = parse_network_screen(pkt)
                        self.last_network_data = parsed
                        logger.info(f"网络屏 收到: speed={parsed['speed_km_h']}km/h "
                                    f"station={parsed['next_station']} "
                                    f"mode={parsed['mode_name']}")
                        if self.on_network_data:
                            self.on_network_data(parsed)
                    except Exception as e:
                        logger.warning(f"解析网络屏报文失败: {e}")
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
        self._net_client = None
        try:
            client.close()
        except Exception:
            pass

    # ---- 信号屏模拟 ----

    def _start_sig_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", SIGNAL_SCREEN_PORT))
        sock.listen(1)
        sock.settimeout(1.0)
        self._sig_socket = sock

        t = threading.Thread(target=self._sig_accept_loop, daemon=True)
        t.start()

    def _sig_accept_loop(self):
        while self.running:
            try:
                client, addr = self._sig_socket.accept()
                logger.info(f"信号屏 上位机连接: {addr}")
                self._sig_client = (client, addr)

                t = threading.Thread(target=self._sig_recv_loop, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                break

    def _sig_recv_loop(self, client: socket.socket):
        buffer = b""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    break
                buffer += data
                while len(buffer) >= SIGNAL_SCREEN_LEN:
                    pkt = buffer[:SIGNAL_SCREEN_LEN]
                    buffer = buffer[SIGNAL_SCREEN_LEN:]
                    try:
                        parsed = parse_signal_screen(pkt)
                        self.last_signal_data = parsed
                        logger.info(f"信号屏 收到: speed={parsed['current_speed_km_h']}km/h "
                                    f"permit={parsed['permit_speed_km_h']}km/h "
                                    f"dist={parsed['target_distance_m']}m "
                                    f"mode={parsed['current_mode']}")
                        if self.on_signal_data:
                            self.on_signal_data(parsed)
                    except Exception as e:
                        logger.warning(f"解析信号屏报文失败: {e}")
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                break
        self._sig_client = None
        try:
            client.close()
        except Exception:
            pass

    # ---- 状态查询 ----

    def get_status(self) -> dict:
        """获取模拟器综合状态"""
        return {
            "plc": {**self.plc_state, "last_upper_cmd": self.last_upper_cmd},
            "network_screen": self.last_network_data,
            "signal_screen": self.last_signal_data,
            "running": self.running,
        }

    def update_plc_state(self, **kwargs):
        """更新 PLC 模拟状态"""
        for k, v in kwargs.items():
            if k in self.plc_state:
                self.plc_state[k] = v


def run_cab_simulator():
    """运行司机台综合模拟器"""
    logging.basicConfig(
        level=logging.INFO,
        format="[司控台] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    sim = CabSimulator()
    sim.start()

    print("\n" + "=" * 60)
    print("司机台模拟器已启动")
    print("=" * 60)
    print("  PLC:     TCP 0.0.0.0:8001/8002/8003")
    print("  网络屏:  TCP 0.0.0.0:8888")
    print("  信号屏:  TCP 0.0.0.0:9999")
    print()
    print("  控制台命令:")
    print("    speed <cm/s>   - 设置列车速度")
    print("    eb 0/1         - 紧急制动 施加/解除")
    print("    cab 0/1        - 驾驶室 激活/关闭")
    print("    key 0/1        - 钥匙 打开/关闭")
    print("    mode <N>       - 驾驶模式 (0=INIT,3=RM,4=CM,5=AM,7=EUM)")
    print("    brake <0-1023> - 制动缸压力")
    print("    status         - 显示完整状态")
    print("    quit           - 退出")
    print()

    try:
        while True:
            cmd = input("司控台> ").strip()
            if not cmd:
                continue
            parts = cmd.split()
            action = parts[0].lower()

            if action in ("quit", "exit"):
                break
            elif action == "speed" and len(parts) > 1:
                sim.update_plc_state(speed_cm_s=int(parts[1]))
                print(f"  速度 → {parts[1]} cm/s")
            elif action == "eb" and len(parts) > 1:
                sim.update_plc_state(eb_status=int(parts[1]))
                print(f"  紧急制动 → {'施加' if int(parts[1]) == 1 else '解除'}")
            elif action == "cab" and len(parts) > 1:
                sim.update_plc_state(cab_active=int(parts[1]))
                print(f"  驾驶室 → {'激活' if int(parts[1]) == 1 else '关闭'}")
            elif action == "key" and len(parts) > 1:
                sim.update_plc_state(key_status=int(parts[1]))
                print(f"  钥匙 → {'打开' if int(parts[1]) == 1 else '关闭'}")
            elif action == "mode" and len(parts) > 1:
                sim.update_plc_state(mode=int(parts[1]))
                print(f"  驾驶模式 → {parts[1]}")
            elif action == "brake" and len(parts) > 1:
                sim.update_plc_state(brake_pressure=int(parts[1]))
                print(f"  制动缸压力 → {parts[1]}")
            elif action == "status":
                s = sim.get_status()
                print("\n--- PLC 状态 ---")
                plc = s["plc"]
                print(f"  速度: {plc['speed_cm_s']} cm/s")
                print(f"  加速度: {plc['accel']}")
                print(f"  驾驶室: {'激活' if plc['cab_active'] else '关闭'}")
                print(f"  钥匙: {'打开' if plc['key_status'] else '关闭'}")
                print(f"  紧急制动: {'施加' if plc['eb_status'] else '解除'}")
                print(f"  驾驶模式: {plc['mode']}")
                print(f"  制动缸压力: {plc['brake_pressure']}")
                if plc["last_upper_cmd"]:
                    print(f"  上位机指令: {plc['last_upper_cmd']}")
                print("\n--- 网络屏 ---")
                ns = s["network_screen"]
                if ns:
                    print(f"  速度: {ns['speed_km_h']} km/h")
                    print(f"  限速: {ns['limit_speed_km_h']} km/h")
                    print(f"  站台: {ns['next_station']}")
                    print(f"  模式: {ns['mode_name']}")
                else:
                    print("  (无数据)")
                print("\n--- 信号屏 ---")
                ss = s["signal_screen"]
                if ss:
                    print(f"  当前速度: {ss['current_speed_km_h']} km/h")
                    print(f"  允许速度: {ss['permit_speed_km_h']} km/h")
                    print(f"  EBI速度: {ss['eb_trigger_speed_km_h']} km/h")
                    print(f"  目标距离: {ss['target_distance_m']} m")
                    print(f"  驾驶模式: {ss['current_mode']}")
                else:
                    print("  (无数据)")
                print()
            else:
                print(f"  未知命令: {cmd}")
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        sim.stop()
        print("司机台模拟器已停止")


if __name__ == "__main__":
    run_cab_simulator()