"""总控数据库节点 UDP 桥接层 — 高频数据交换。

**已弃用** — 外部系统接入方案已废弃，后端默认直接对接前端。
保留此文件仅作参考，不再维护。

数据流:
  我们 ──UDP 20ms(480B)──→ 总控节点 (速度/加速度/里程)
  总控节点 ──UDP 20ms(320B)──→ 我们 (外部指令/参考信息)

文档: 外部系统对接方案 4.1 节（已废弃）
"""

from __future__ import annotations

import logging
import socket
import struct
import threading
import time
from typing import Callable, Optional

from .protocol import (
    DB_NODE_IP, DB_NODE_PORT,
    VEHICLE_MODEL_IP, VEHICLE_MODEL_PORT,
    UDP_TRAIN_DATA_TO_DB_LEN, UDP_DB_TO_TRAIN_LEN,
)

logger = logging.getLogger(__name__)


# ====================================================================
# 编解码
# ====================================================================

def pack_train_data_to_db(
    trains: list[dict],
    buffer_size: int = UDP_TRAIN_DATA_TO_DB_LEN,
) -> bytes:
    """打包 你 → 总控节点 的列车数据 (480字节)。

    每列车: 加速度(m/s²) + 速度(m/s) + 累计里程(m) = 24字节
    最多20列车 = 480字节

    Args:
        trains: 列车信息列表，每项 dict:
            - acceleration: float (m/s²)
            - speed: float (m/s)
            - position: float (m)

    Returns:
        480字节的 UDP 报文。
    """
    data = bytearray(buffer_size)
    offset = 0
    for t in trains[:20]:
        if offset + 24 > buffer_size:
            break
        struct.pack_into("<d", data, offset, float(t.get("acceleration", 0.0)))
        struct.pack_into("<d", data, offset + 8, float(t.get("speed", 0.0)))
        struct.pack_into("<d", data, offset + 16, float(t.get("position", 0.0)))
        offset += 24
    return bytes(data)


def parse_db_command(data: bytes) -> dict:
    """解析 总控节点 → 你 的指令数据 (320字节)。

    每列车: 指令(int) + 加减速百分比(float) = 16字节
    最多20列车 = 320字节

    Args:
        data: 320字节的 UDP 报文。

    Returns:
        dict: 包含指令列表的字典。
    """
    result = {"trains": []}
    for i in range(20):
        offset = i * 16
        if offset + 16 > len(data):
            break
        cmd = struct.unpack_from("<d", data, offset)[0]
        pct = struct.unpack_from("<d", data, offset + 8)[0]
        result["trains"].append({
            "index": i,
            "command": int(cmd),
            "command_str": {1: "加速", 2: "减速", 0: "惰行"}.get(int(cmd), f"未知({int(cmd)})"),
            "percentage": pct,
        })
    return result


# ====================================================================
# UDP 桥接客户端
# ====================================================================

class UdpBridge:
    """总控数据库节点 UDP 通信桥接。

    每20ms发送列车状态数据，同时接收外部系统的指令参考信息。

    用法:
        bridge = UdpBridge()
        bridge.start()
        bridge.update_trains(trains_data)  # 每仿真步调用
        cmd = bridge.get_latest_command()   # 获取最新外部指令
    """

    def __init__(
        self,
        local_ip: str = VEHICLE_MODEL_IP,
        local_port: int = VEHICLE_MODEL_PORT,
        remote_ip: str = DB_NODE_IP,
        remote_port: int = DB_NODE_PORT,
    ):
        self.local_addr = (local_ip, local_port)
        self.remote_addr = (remote_ip, remote_port)
        self.sock: Optional[socket.socket] = None
        self.running = False

        # 最新的待发送数据
        self._send_data: bytes = b""

        # 最近接收的指令
        self.last_command: Optional[dict] = None
        self.last_recv_time: Optional[float] = None

        # 回调: 收到新指令时触发
        self.on_command: Optional[Callable[[dict], None]] = None

        # 统计
        self.send_count = 0
        self.recv_count = 0

    def start(self) -> bool:
        """启动 UDP 收发。"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(0.01)  # 10ms 超时，不阻塞主循环
            self.sock.bind(self.local_addr)
            self.running = True

            recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
            send_thread = threading.Thread(target=self._send_loop, daemon=True)
            recv_thread.start()
            send_thread.start()

            logger.info(
                f"UDP 桥接已启动: 本地 {self.local_addr[0]}:{self.local_addr[1]} "
                f"→ 远程 {self.remote_addr[0]}:{self.remote_addr[1]}"
            )
            return True
        except Exception as e:
            logger.error(f"UDP 桥接启动失败: {e}")
            self.sock = None
            self.running = False
            return False

    def stop(self):
        """停止 UDP 收发。"""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("UDP 桥接已停止")

    def update_trains(self, trains: list[dict]):
        """更新待发送的列车数据 (下次发送循环会发出)。

        Args:
            trains: 列车状态列表，每项包含 acceleration/speed/position。
        """
        self._send_data = pack_train_data_to_db(trains)

    def _send_loop(self):
        """发送线程: 每20ms发送一次。"""
        interval = 0.020  # 20ms
        while self.running:
            if self.sock and self._send_data:
                try:
                    self.sock.sendto(self._send_data, self.remote_addr)
                    self.send_count += 1
                except OSError as e:
                    logger.error(f"UDP 发送失败: {e}")
            time.sleep(interval)

    def _recv_loop(self):
        """接收线程: 持续接收外部指令。"""
        while self.running:
            if not self.sock:
                break
            try:
                data, addr = self.sock.recvfrom(4096)
                if len(data) >= UDP_DB_TO_TRAIN_LEN:
                    parsed = parse_db_command(data[:UDP_DB_TO_TRAIN_LEN])
                    self.last_command = parsed
                    self.last_recv_time = time.time()
                    self.recv_count += 1
                    if self.on_command:
                        self.on_command(parsed)
            except socket.timeout:
                continue
            except OSError:
                break

    def get_latest_command(self) -> Optional[dict]:
        """获取最近一次外部指令。"""
        return self.last_command

    def is_connected(self) -> bool:
        """UDP 是无连接的，只要 socket 存在就算就绪。"""
        return self.sock is not None