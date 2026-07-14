"""
PLC 双向通信客户端（7.1 接收 + 7.2 发送）

**已弃用** — 外部系统接入方案已废弃，不再需要司机台联动测试。
保留此文件仅作参考，不再维护。

连接真实 PLC 硬件，实现：

- 接收线程：持续接收 PLC 7.1 报文（46字节），解析并缓存为 PLC 状态
- 发送线程：周期发送 7.2 报文（28字节），下发车辆速度/指示灯等控制指令

双向数据流：

  PLC ──7.1(100ms)──→ 上位机（接收手柄/按钮/指示灯状态）
  上位机 ──7.2(按需)──→ PLC（下发车辆速度/灯状态/时钟同步）

用法：
  python -m driver_cab_test.plc_client                         # 交互模式
  python -m driver_cab_test.plc_client --no-interactive         # 后台运行
  python -m driver_cab_test.plc_client --speed 50               # 初始速度50
"""

import socket
import threading
import time
import logging
import os
from datetime import datetime
from typing import Optional, Callable

from .config import (
    PLC_SERVER_IP, PLC_PORT_A,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    SIM_CYCLE_INTERVAL,
)
from .protocols import parse_plc_to_upper, pack_upper_to_plc

logger = logging.getLogger(__name__)


class PlcClient:
    """PLC 双向通信客户端"""

    def __init__(self, host: str = PLC_SERVER_IP, port: int = PLC_PORT_A):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.running = False

        # ---- 最近一次 PLC 状态（7.1 报文解析结果） ----
        self.last_plc_state: Optional[dict] = None
        self.last_recv_time: Optional[float] = None

        # ---- 待发送的 7.2 控制值（上位机→PLC） ----
        # 时间默认用当前系统时间，_build_upper_packet 中每次打包时刷新
        self._update_send_time()
        self.send_verify_type = 0
        self.send_verify_code = 0
        self.send_hscb = 0
        self.send_brake_fault = 0
        self.send_door_open_light = 0
        self.send_door_closed = 0
        self.send_net_fault = 0
        self.send_ar_available = 0
        self.send_ato_available = 0
        self.send_wash_mode = 0
        self.send_ato_active = 0
        self.send_ar_active = 0
        self.send_vehicle_speed = 0

        # 发送周期控制
        self.send_interval = SIM_CYCLE_INTERVAL  # 默认与 PLC 周期一致（100ms）

        # 回调：收到新 PLC 数据时触发
        self.on_plc_data: Optional[Callable[[dict], None]] = None

        # 接收统计
        self.pkt_count = 0
        self.send_count = 0

    # ──────────────────────────────────────────────
    # 连接 / 启动 / 停止
    # ──────────────────────────────────────────────

    def connect(self) -> bool:
        """连接 PLC 服务器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.port))
            logger.info(f"已连接 PLC: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接 PLC 失败: {e}")
            self.sock = None
            return False

    def start(self):
        """启动收发线程"""
        if not self.sock:
            raise RuntimeError("请先调用 connect()")
        self.running = True

        recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        send_thread = threading.Thread(target=self._send_loop, daemon=True)
        recv_thread.start()
        send_thread.start()

        logger.info("PLC 客户端收发线程已启动")

    def stop(self):
        """停止客户端"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("PLC 客户端已停止")

    # ──────────────────────────────────────────────
    # 接收线程（7.1 报文）
    # ──────────────────────────────────────────────

    def _recv_loop(self):
        """接收 PLC 7.1 报文循环"""
        buffer = b""
        while self.running:
            try:
                # 尝试读取完整一包
                if len(buffer) < PLC_TO_UPPER_LEN:
                    chunk = self.sock.recv(1024)
                    if not chunk:
                        logger.warning("PLC 连接断开")
                        self.running = False
                        break
                    buffer += chunk

                # 逐包解析
                while len(buffer) >= PLC_TO_UPPER_LEN:
                    pkt = buffer[:PLC_TO_UPPER_LEN]
                    buffer = buffer[PLC_TO_UPPER_LEN:]
                    try:
                        parsed = parse_plc_to_upper(pkt)
                        self.last_plc_state = parsed
                        self.last_recv_time = time.time()
                        self.pkt_count += 1

                        if self.on_plc_data:
                            self.on_plc_data(parsed)
                    except Exception as e:
                        logger.warning(f"解析 PLC 7.1 报文失败: {e}")
            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                logger.error(f"接收异常: {e}")
                self.running = False
                break

    # ──────────────────────────────────────────────
    # 发送线程（7.2 报文）
    # ──────────────────────────────────────────────

    def _send_loop(self):
        """周期发送上位机 7.2 报文"""
        while self.running:
            if self.sock:
                try:
                    data = self._build_upper_packet()
                    self.sock.sendall(data)
                    self.send_count += 1
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    logger.error(f"发送 7.2 报文失败: {e}")
                    self.running = False
                    break
            time.sleep(self.send_interval)

    def _update_send_time(self):
        """刷新发送时间戳为当前系统时间"""
        now = datetime.now()
        self.send_year = now.year
        self.send_month = now.month
        self.send_day = now.day
        self.send_hour = now.hour
        self.send_minute = now.minute
        self.send_second = now.second

    def _build_upper_packet(self) -> bytes:
        """构建当前 7.2 报文，时间自动取系统时钟"""
        self._update_send_time()  # 每次发包前刷新时间
        return pack_upper_to_plc(
            year=self.send_year, month=self.send_month,
            day=self.send_day, hour=self.send_hour,
            minute=self.send_minute, second=self.send_second,
            verify_type=self.send_verify_type,
            verify_code=self.send_verify_code,
            # 指示灯 (字节24)
            hscb=self.send_hscb,
            brake_fault=self.send_brake_fault,
            door_open_light=self.send_door_open_light,
            door_closed=self.send_door_closed,
            net_fault=self.send_net_fault,
            ar_available=self.send_ar_available,
            # 模式标志 (字节25)
            ato_available=self.send_ato_available,
            wash_mode=self.send_wash_mode,
            ato_active=self.send_ato_active,
            ar_active=self.send_ar_active,
            # 车辆速度
            vehicle_speed=self.send_vehicle_speed,
        )

    # ──────────────────────────────────────────────
    # 公开 API：外部控制
    # ──────────────────────────────────────────────

    def set_vehicle_speed(self, speed: int):
        """设置下发给 PLC 的车辆速度（0-65535）"""
        self.send_vehicle_speed = max(0, min(65535, speed))

    def set_time(self, year: int, month: int, day: int,
                 hour: int, minute: int, second: int):
        """设置下发给 PLC 的时间同步数据"""
        self.send_year = year
        self.send_month = month
        self.send_day = day
        self.send_hour = hour
        self.send_minute = minute
        self.send_second = second

    def set_indicator(self, name: str, value: int):
        """设置指示灯/模式标志（字节24-25）

        name 取值:
          hscb, brake_fault, door_open_light, door_closed,
          net_fault, ar_available,
          ato_available, wash_mode, ato_active, ar_active
        """
        valid_names = {
            "hscb", "brake_fault", "door_open_light", "door_closed",
            "net_fault", "ar_available",
            "ato_available", "wash_mode", "ato_active", "ar_active",
        }
        if name not in valid_names:
            raise ValueError(f"未知标志名: {name}，可选: {valid_names}")
        attr = f"send_{name}"
        setattr(self, attr, 1 if value else 0)

    def get_plc_state(self) -> Optional[dict]:
        """获取最近一次 PLC 状态"""
        return self.last_plc_state

    def get_status_str(self) -> str:
        """获取当前状态摘要"""
        lines = []
        lines.append(f"连接状态: {'已连接' if self.sock else '未连接'}")
        lines.append(f"接收包数: {self.pkt_count}  发送包数: {self.send_count}")
        if self.last_recv_time:
            elapsed = time.time() - self.last_recv_time
            lines.append(f"距上次接收: {elapsed:.1f}s")
        if self.last_plc_state:
            s = self.last_plc_state
            lines.append(f"PLC 时间: {s.get('timestamp_str', 'N/A')}")
            lines.append(f"PLC 速度: {s.get('vehicle_speed', 'N/A')}")
            lines.append(f"PLC 手柄: 方向={s.get('dir_handle_str', 'N/A')}  "
                         f"主手柄={s.get('main_handle_str', 'N/A')}  "
                         f"牵引={s.get('traction_level_pct', 'N/A')}%  "
                         f"制动={s.get('brake_level_pct', 'N/A')}%")
            lines.append(f"PLC 门控: 开左={_bs(s.get('open_left_door'))}  "
                         f"开右={_bs(s.get('open_right_door'))}  "
                         f"关左={_bs(s.get('close_left_door'))}  "
                         f"关右={_bs(s.get('close_right_door'))}")
            lines.append(f"PLC 按钮: EB={_bs(s.get('eb_button_locked'))}  "
                         f"母线={_bs(s.get('bus_ctrl_locked'))}  "
                         f"强迫缓解={_bs(s.get('forced_release'))}  "
                         f"强迫泵风={_bs(s.get('forced_pump'))}")
            lines.append(f"PLC 模式: ATO可用={_bs(s.get('ato_available'))}  "
                         f"ATO激活={_bs(s.get('ato_active'))}  "
                         f"AR可用={_bs(s.get('ar_available'))}  "
                         f"AR激活={_bs(s.get('ar_active'))}")
            lines.append(f"PLC 指示灯: 高断合={_bs(s.get('hscb'))}  "
                         f"制动缓解不良={_bs(s.get('brake_fault_indicator'))}  "
                         f"门关好={_bs(s.get('door_closed_indicator'))}  "
                         f"网络故障={_bs(s.get('net_fault_indicator'))}")
        lines.append(f"下发速度: {self.send_vehicle_speed}")
        return "\n".join(lines)


def _bs(val) -> str:
    """布尔值转标记符号"""
    return "●" if val else "○"


# ──────────────────────────────────────────────
# 交互式运行
# ──────────────────────────────────────────────

def run_plc_client(host: str = PLC_SERVER_IP, port: int = PLC_PORT_A,
                   initial_speed: int = 0, interactive: bool = True):
    """运行 PLC 双向通信客户端"""
    logging.basicConfig(
        level=logging.INFO,
        format="[PLC] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    client = PlcClient(host=host, port=port)
    if initial_speed:
        client.set_vehicle_speed(initial_speed)

    # 收到 PLC 数据时不打印日志，避免干扰命令行输入
    # 需要查看时用 status 命令

    if not client.connect():
        print(f"✗ 连接 PLC {host}:{port} 失败")
        return

    client.start()
    print(f"\nPLC 双向通信客户端运行中")
    print(f"  目标: {host}:{port}")
    print(f"  ← 7.1 接收（PLC→上位机，100ms周期）")
    print(f"  → 7.2 发送（上位机→PLC，{client.send_interval*1000:.0f}ms周期）")
    print(f"  初始下发速度: {initial_speed}")

    if not interactive:
        try:
            while client.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            client.stop()
        return

    print()
    print("  按 Enter 停止客户端")
    print("  控制台命令:")
    print("  ── 速度控制 ──")
    print("    speed <N>       设置下发给 PLC 的车辆速度 (0-65535)")
    print("  ── 指示灯(字节24) ──")
    print("    hscb 0/1        高断合指示灯")
    print("    bf 0/1          制动缓解不良指示灯")
    print("    dol 0/1         开门灯")
    print("    dc 0/1          门关好指示灯")
    print("    nf 0/1          网络故障指示灯")
    print("    ar_avail 0/1    具备AR模式")
    print("  ── 模式标志(字节25) ──")
    print("    ato_avail 0/1   具备ATO模式")
    print("    ato_act 0/1     ATO已激活")
    print("    ar_act 0/1      AR已激活")
    print("    wash 0/1        洗车模式")
    print("  ── 其他 ──")
    print("    status          显示当前状态")
    print("    quit            退出")
    print()

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
                client.set_vehicle_speed(int(parts[1]))
                print(f"  下发速度已设为 {parts[1]}")
            elif action == "hscb" and len(parts) > 1:
                client.set_indicator("hscb", int(parts[1]))
                print(f"  高断合指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "bf" and len(parts) > 1:
                client.set_indicator("brake_fault", int(parts[1]))
                print(f"  制动缓解不良指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "dol" and len(parts) > 1:
                client.set_indicator("door_open_light", int(parts[1]))
                print(f"  开门灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "dc" and len(parts) > 1:
                client.set_indicator("door_closed", int(parts[1]))
                print(f"  门关好指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "nf" and len(parts) > 1:
                client.set_indicator("net_fault", int(parts[1]))
                print(f"  网络故障指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "ar_avail" and len(parts) > 1:
                client.set_indicator("ar_available", int(parts[1]))
                print(f"  具备AR模式: {'是' if int(parts[1]) else '否'}")
            elif action == "ato_avail" and len(parts) > 1:
                client.set_indicator("ato_available", int(parts[1]))
                print(f"  具备ATO模式: {'是' if int(parts[1]) else '否'}")
            elif action == "ato_act" and len(parts) > 1:
                client.set_indicator("ato_active", int(parts[1]))
                print(f"  ATO已激活: {'是' if int(parts[1]) else '否'}")
            elif action == "ar_act" and len(parts) > 1:
                client.set_indicator("ar_active", int(parts[1]))
                print(f"  AR已激活: {'是' if int(parts[1]) else '否'}")
            elif action == "wash" and len(parts) > 1:
                client.set_indicator("wash_mode", int(parts[1]))
                print(f"  洗车模式: {'是' if int(parts[1]) else '否'}")
            elif action == "status":
                print(client.get_status_str())
            else:
                print(f"  未知命令: {cmd}")
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        client.stop()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="PLC 双向通信客户端（7.1 接收 + 7.2 发送）"
    )
    parser.add_argument("--host", default=PLC_SERVER_IP, help="PLC IP 地址")
    parser.add_argument("--port", type=int, default=PLC_PORT_A, help="PLC 端口")
    parser.add_argument("--speed", type=int, default=0, help="初始下发速度")
    parser.add_argument("--no-interactive", action="store_true",
                        help="非交互模式（后台运行）")
    args = parser.parse_args()

    run_plc_client(
        host=args.host,
        port=args.port,
        initial_speed=args.speed,
        interactive=not args.no_interactive,
    )


if __name__ == "__main__":
    main()