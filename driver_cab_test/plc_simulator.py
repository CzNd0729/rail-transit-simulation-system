"""
PLC 模拟服务器
=================
模拟真实司机驾驶模拟台 PLC，通过 TCP 协议与上位机通信。

- 作为 TCP Server 监听 8001/8002/8003 端口
- 周期（100ms）发送 46 字节数据给上位机（文档 7.1节）
- 接收上位机 28 字节控制指令（文档 7.2节）
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

        # 模拟状态（按文档 7.1 节 46字节协议）
        self.train_id = 1
        self.speed_cm_s = 0
        self.accel = 0
        self.master_controller = 0
        self.brake_pressure = 0
        self.door_status = 0
        self.cab_active = 0
        self.key_status = 0
        self.eb_status = 0
        self.mode = DRIVE_MODE["INIT"]  # 现在用做兼容旧引用的默认值

        # ---- 文档 7.1 节 46字节协议字段 ----
        self.year = 2025
        self.month = 7
        self.day = 16
        self.hour = 15
        self.minute = 11
        self.second = 3
        self.verify_type = 0
        self.verify_code = 0
        # 指示灯 (字节24)
        self.hscb = 0
        self.brake_fault_indicator = 0
        self.door_open_light = 0
        self.door_closed_indicator = 0
        self.net_fault_indicator = 0
        self.ar_available = 0
        # 模式标志 (字节25)
        self.ato_available = 0
        self.wash_mode = 0
        self.ato_active = 0
        self.ar_active = 0
        # 车辆速度 (字节26-27)
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
        # 外部照明 / 门模式
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
                # 解析 28 字节报文（文档 7.2 节）
                while len(buffer) >= UPPER_TO_PLC_LEN:
                    pkt = buffer[:UPPER_TO_PLC_LEN]
                    buffer = buffer[UPPER_TO_PLC_LEN:]
                    try:
                        cmd = parse_upper_to_plc(pkt)
                        self.last_upper_cmd = cmd
                        self._apply_upper_cmd(cmd)
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
        """构建当前状态报文（文档 7.1 节 46字节小端序）"""
        return pack_plc_to_upper(
            year=self.year, month=self.month, day=self.day,
            hour=self.hour, minute=self.minute, second=self.second,
            verify_type=self.verify_type, verify_code=self.verify_code,
            # 指示灯
            hscb=self.hscb,
            brake_fault=self.brake_fault_indicator,
            door_closed=self.door_closed_indicator,
            net_fault=self.net_fault_indicator,
            ar_available=self.ar_available,
            # 模式标志
            ato_available=self.ato_available,
            wash_mode=self.wash_mode,
            ato_active=self.ato_active,
            ar_active=self.ar_active,
            # 车辆速度
            vehicle_speed=self.vehicle_speed,
            # 按钮 (字节28)
            eb_button=self.eb_button,
            bus_ctrl=self.bus_ctrl,
            forced_release=self.forced_release,
            forced_pump=self.forced_pump,
            emergency_cmd=self.emergency_cmd,
            parking_apply=self.parking_apply,
            parking_release=self.parking_release,
            horn=self.horn,
            # 门控 (字节29)
            open_left_door=self.open_left_door,
            open_right_door=self.open_right_door,
            close_left_door=self.close_left_door,
            close_right_door=self.close_right_door,
            # 照明/门模式
            light_switch=self.light_switch,
            door_mode_switch=self.door_mode_switch,
            # 按钮 (字节34)
            high_accel=self.high_accel,
            cab_light=self.cab_light,
            mode_up_confirm=self.mode_up_confirm,
            mode_down_confirm=self.mode_down_confirm,
            confirm_flag=self.confirm_flag,
            ar_flag=self.ar_flag,
            traction_reset=self.traction_reset,
            ato_start=self.ato_start,
            # 开关 (字节35)
            wash_switch=self.wash_switch,
            key_switch=self.key_switch,
            alert_flag=self.alert_flag,
            alert_release=self.alert_release,
            # 手柄
            dir_handle=self.dir_handle,
            main_handle=self.main_handle,
            traction_level=self.traction_level,
            brake_level=self.brake_level,
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

    def _apply_upper_cmd(self, cmd: dict):
        """将上位机 7.2 控制指令应用到模拟器状态，7.1 报文中会体现出来"""
        # 车辆速度
        speed = cmd.get("vehicle_speed", 0)
        if speed is not None:
            self.vehicle_speed = speed
        # 时间同步
        if cmd.get("year"):
            self.year = cmd["year"]
            self.month = cmd["month"]
            self.day = cmd["day"]
            self.hour = cmd["hour"]
            self.minute = cmd["minute"]
            self.second = cmd["second"]
        # 指示灯 (字节24)
        self.hscb = 1 if cmd.get("hscb") else 0
        self.brake_fault_indicator = 1 if cmd.get("brake_fault_indicator") else 0
        self.door_closed_indicator = 1 if cmd.get("door_closed_indicator") else 0
        self.net_fault_indicator = 1 if cmd.get("net_fault_indicator") else 0
        self.ar_available = 1 if cmd.get("ar_available") else 0
        # 模式标志 (字节25)
        self.ato_available = 1 if cmd.get("ato_available") else 0
        self.wash_mode = 1 if cmd.get("wash_mode") else 0
        self.ato_active = 1 if cmd.get("ato_active") else 0
        self.ar_active = 1 if cmd.get("ar_active") else 0


def run_plc_simulator(port: int = PLC_PORT_A, local_only: bool = False, interactive: bool = True):
    """运行独立 PLC 模拟器"""
    logging.basicConfig(
        level=logging.INFO,
        format="[PLC] %(asctime)s %(message)s",
        datefmt="%H:%M:%S",
    )

    host = "127.0.0.1" if local_only else "0.0.0.0"
    sim = PlcSimulator(host=host, port=port)
    sim.start()

    print(f"\nPLC模拟器运行中 (端口 {port})")
    print(f"  绑定地址: {host}")

    if not interactive:
        # 非交互模式：保持运行直到被终止
        try:
            while sim.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            sim.stop()
        return

    print("  按 Enter 停止模拟器")
    print("  在控制台输入命令改变模拟状态:")
    print("  ── 基本参数 ──")
    print("    speed <N>       车辆速度值 (0-65535)")
    print("    eb 0/1          紧急制动按钮锁定")
    print("    key 0/1         钥匙开关")
    print("  ── 指示灯(字节24) ──")
    print("    hscb 0/1        高断合指示灯")
    print("    bf 0/1          制动缓解不良指示灯")
    print("    dc 0/1          门关好指示灯")
    print("    nf 0/1          网络故障指示灯")
    print("    ar_avail 0/1    具备AR模式")
    print("  ── 模式标志(字节25) ──")
    print("    ato_avail 0/1   具备ATO模式")
    print("    ato_act 0/1     ATO已激活")
    print("    ar_act 0/1      AR已激活")
    print("    wash 0/1        洗车模式")
    print("  ── 按钮(字节28) ──")
    print("    eb_btn 0/1      紧急制动按钮锁定")
    print("    bus 0/1         母线控制按钮锁定")
    print("    fr 0/1          强迫缓解")
    print("    fp 0/1          强迫泵风")
    print("    emerg 0/1       应急指挥按钮锁定")
    print("    pk_apply 0/1    停放制动施加")
    print("    pk_rel 0/1      停放制动缓解")
    print("    horn 0/1        电笛")
    print("  ── 门控(字节29) ──")
    print("    ol 0/1          开左门")
    print("    or 0/1          开右门")
    print("    cl 0/1          关左门")
    print("    cr 0/1          关右门")
    print("  ── 开关/照明/手柄 ──")
    print("    light <N>       外部照明 (0=停止 1=自动 2=近光 4=远光)")
    print("    door_mode <N>   门模式 (0=半自动 1=手动 2=自动)")
    print("    dir <N>         方向手柄 (0=0位 1=向前 2=向后)")
    print("    handle <N>      主手柄 (0=0位 1=牵引 2=制动 4=快制)")
    print("    traction <N>    牵引极位 (0-25600, 100%=25600)")
    print("    brake <N>       制动极位 (0-25600, 100%=25600)")
    print("  ── 其他 ──")
    print("    alert 0/1       警惕标志")
    print("    alert_rel 0/1   警惕允许解除")
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

            if action == "quit" or action == "exit":
                break
            elif action == "speed" and len(parts) > 1:
                sim.vehicle_speed = int(parts[1])
                print(f"  车辆速度已设为 {parts[1]}")
            elif action == "eb" and len(parts) > 1:
                v = int(parts[1])
                sim.eb_button = v
                print(f"  紧急制动按钮: {'锁定' if v else '解除'}")
            elif action == "key" and len(parts) > 1:
                v = int(parts[1])
                sim.key_switch = v
                sim.key_status = v
                print(f"  钥匙开关: {'开' if v else '关'}")
            # 指示灯 (字节24)
            elif action == "hscb" and len(parts) > 1:
                sim.hscb = int(parts[1])
                print(f"  高断合指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "bf" and len(parts) > 1:
                sim.brake_fault_indicator = int(parts[1])
                print(f"  制动缓解不良指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "dc" and len(parts) > 1:
                sim.door_closed_indicator = int(parts[1])
                print(f"  门关好指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "nf" and len(parts) > 1:
                sim.net_fault_indicator = int(parts[1])
                print(f"  网络故障指示灯: {'亮' if int(parts[1]) else '灭'}")
            elif action == "ar_avail" and len(parts) > 1:
                sim.ar_available = int(parts[1])
                print(f"  具备AR模式: {'是' if int(parts[1]) else '否'}")
            # 模式标志 (字节25)
            elif action == "ato_avail" and len(parts) > 1:
                sim.ato_available = int(parts[1])
                print(f"  具备ATO模式: {'是' if int(parts[1]) else '否'}")
            elif action == "ato_act" and len(parts) > 1:
                sim.ato_active = int(parts[1])
                print(f"  ATO已激活: {'是' if int(parts[1]) else '否'}")
            elif action == "ar_act" and len(parts) > 1:
                sim.ar_active = int(parts[1])
                print(f"  AR已激活: {'是' if int(parts[1]) else '否'}")
            elif action == "wash" and len(parts) > 1:
                sim.wash_mode = int(parts[1])
                print(f"  洗车模式: {'是' if int(parts[1]) else '否'}")
            # 按钮 (字节28)
            elif action == "eb_btn" and len(parts) > 1:
                sim.eb_button = int(parts[1])
                print(f"  紧急制动按钮: {'锁定' if int(parts[1]) else '解除'}")
            elif action == "bus" and len(parts) > 1:
                sim.bus_ctrl = int(parts[1])
                print(f"  母线控制按钮: {'锁定' if int(parts[1]) else '解除'}")
            elif action == "fr" and len(parts) > 1:
                sim.forced_release = int(parts[1])
                print(f"  强迫缓解: {'触发' if int(parts[1]) else '复位'}")
            elif action == "fp" and len(parts) > 1:
                sim.forced_pump = int(parts[1])
                print(f"  强迫泵风: {'触发' if int(parts[1]) else '复位'}")
            elif action == "emerg" and len(parts) > 1:
                sim.emergency_cmd = int(parts[1])
                print(f"  应急指挥按钮: {'锁定' if int(parts[1]) else '解除'}")
            elif action == "pk_apply" and len(parts) > 1:
                sim.parking_apply = int(parts[1])
                print(f"  停放制动施加: {'触发' if int(parts[1]) else '复位'}")
            elif action == "pk_rel" and len(parts) > 1:
                sim.parking_release = int(parts[1])
                print(f"  停放制动缓解: {'触发' if int(parts[1]) else '复位'}")
            elif action == "horn" and len(parts) > 1:
                sim.horn = int(parts[1])
                print(f"  电笛: {'触发' if int(parts[1]) else '复位'}")
            # 门控 (字节29)
            elif action == "ol" and len(parts) > 1:
                sim.open_left_door = int(parts[1])
                print(f"  开左门: {'触发' if int(parts[1]) else '复位'}")
            elif action == "or" and len(parts) > 1:
                sim.open_right_door = int(parts[1])
                print(f"  开右门: {'触发' if int(parts[1]) else '复位'}")
            elif action == "cl" and len(parts) > 1:
                sim.close_left_door = int(parts[1])
                print(f"  关左门: {'触发' if int(parts[1]) else '复位'}")
            elif action == "cr" and len(parts) > 1:
                sim.close_right_door = int(parts[1])
                print(f"  关右门: {'触发' if int(parts[1]) else '复位'}")
            # 照明/门模式/手柄
            elif action == "light" and len(parts) > 1:
                sim.light_switch = int(parts[1])
                light_map = {0: "停止", 1: "自动", 2: "近光", 4: "远光"}
                print(f"  外部照明: {light_map.get(int(parts[1]), parts[1])}")
            elif action == "door_mode" and len(parts) > 1:
                sim.door_mode_switch = int(parts[1])
                dm_map = {0: "半自动", 1: "手动", 2: "自动"}
                print(f"  门模式: {dm_map.get(int(parts[1]), parts[1])}")
            elif action == "dir" and len(parts) > 1:
                sim.dir_handle = int(parts[1])
                dir_map = {0: "0位", 1: "向前", 2: "向后"}
                print(f"  方向手柄: {dir_map.get(int(parts[1]), parts[1])}")
            elif action == "handle" and len(parts) > 1:
                sim.main_handle = int(parts[1])
                h_map = {0: "0位", 1: "牵引", 2: "制动", 4: "快制"}
                print(f"  主手柄: {h_map.get(int(parts[1]), parts[1])}")
            elif action == "traction" and len(parts) > 1:
                sim.traction_level = int(parts[1])
                pct = int(parts[1]) / 256.0
                print(f"  牵引极位: {parts[1]} ({pct:.1f}%)")
            elif action == "brake" and len(parts) > 1:
                sim.brake_level = int(parts[1])
                pct = int(parts[1]) / 256.0
                print(f"  制动极位: {parts[1]} ({pct:.1f}%)")
            elif action == "alert" and len(parts) > 1:
                sim.alert_flag = int(parts[1])
                print(f"  警惕标志: {'触发' if int(parts[1]) else '复位'}")
            elif action == "alert_rel" and len(parts) > 1:
                sim.alert_release = int(parts[1])
                print(f"  警惕允许解除: {'允许' if int(parts[1]) else '不允许'}")
            elif action == "status":
                print(f"  时间: {sim.year:04d}-{sim.month:02d}-{sim.day:02d} "
                      f"{sim.hour:02d}:{sim.minute:02d}:{sim.second:02d}")
                print(f"  车辆速度: {sim.vehicle_speed}")
                print(f"  指示灯: hscb={sim.hscb} bf={sim.brake_fault_indicator} "
                      f"dc={sim.door_closed_indicator} nf={sim.net_fault_indicator}")
                print(f"  模式: ato_avail={sim.ato_available} ato_act={sim.ato_active} "
                      f"ar_act={sim.ar_active} wash={sim.wash_mode}")
                print(f"  按钮: eb={sim.eb_button} bus={sim.bus_ctrl} "
                      f"fr={sim.forced_release} fp={sim.forced_pump}")
                print(f"  门控: ol={sim.open_left_door} or={sim.open_right_door} "
                      f"cl={sim.close_left_door} cr={sim.close_right_door}")
                print(f"  照明={sim.light_switch} 门模式={sim.door_mode_switch}")
                print(f"  手柄: dir={sim.dir_handle} main={sim.main_handle} "
                      f"牵引={sim.traction_level}({sim.traction_level/256:.1f}%) "
                      f"制动={sim.brake_level}({sim.brake_level/256:.1f}%)")
                print(f"  钥匙开关={sim.key_switch} 警惕={sim.alert_flag} "
                      f"警惕解除={sim.alert_release}")
                if sim.last_upper_cmd:
                    print(f"  上位机指令: {sim.last_upper_cmd}")
                print(f"  连接状态: {'已连接' if sim.client_socket else '等待连接'}")
            else:
                print(f"  未知命令: {cmd}")
    except KeyboardInterrupt:
        print("\n正在停止...")
    finally:
        sim.stop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PLC 模拟器（文档 7.1 节 46字节小端序）")
    parser.add_argument("--port", type=int, default=PLC_PORT_A, help="监听端口")
    parser.add_argument("--local", action="store_true", help="仅绑定 127.0.0.1（无真实硬件时使用）")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式（默认后台运行）")
    args = parser.parse_args()

    run_plc_simulator(port=args.port, local_only=args.local, interactive=args.interactive)


if __name__ == "__main__":
    main()