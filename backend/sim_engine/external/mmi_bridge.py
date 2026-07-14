"""信号屏 (MMI) TCP 桥接层 — 发送信号/速度信息。

数据流:
  我们 ──TCP 66B──→ 信号屏 (速度/信号/模式信息)

文档: 外部系统对接方案 4.5 节
"""

from __future__ import annotations

import logging
import socket
import struct
import time
from datetime import datetime
from typing import Optional

from .protocol import (
    SIGNAL_SCREEN_DEVICE_IP, SIGNAL_SCREEN_PORT,
    SIGNAL_SCREEN_LEN, SIGNAL_SCREEN_OFFSET, SIGNAL_SCREEN_HEADER_ID,
    SIGNAL_RUN_DIR, SIGNAL_MODE_MAP,
    CONNECT_TIMEOUT, RECV_TIMEOUT,
)

logger = logging.getLogger(__name__)


# ====================================================================
# 上位机 → 信号屏 (66字节) 打包
# ====================================================================

def pack_signal_screen(
    # -- 报文头 --
    timestamp_ms: int = 0,
    verify_type: int = 0, verify_code: int = 0,
    protocol_id: int = 0, msg_id: int = 0,
    # -- 时间 --
    year: int = 2025, month: int = 1, day: int = 1,
    hour: int = 0, minute: int = 0, second: int = 0,
    # -- 站信息 --
    curr_station_id: int = 0,
    next_station_id: int = 0,
    end_station_id: int = 0,
    # -- 状态 --
    cm_state: int = 0,
    mm_state: int = 0,
    ctc_state: int = 0,
    run_direction: int = 0,      # 0=上行 1=下行
    # -- 运行数据 --
    speed: float = 0.0,          # km/h
    acceleration: float = 0.0,   # m/s²
    traction_cut: int = 0,       # 牵引切除 0/1
    speed_limit: int = 0,        # km/h
    mode: int = 0,               # 驾驶模式 (RM/SM/AR/ATO/DTO)
    traction_state: int = 0,     # 牵引状态 0/1
    brake_state: int = 0,        # 制动状态 0/1
    eb_state: int = 0,           # 紧急制动 0/1
    event_id: int = 0,
    signal_state: int = 0,       # 信号状态 BIT0-3
    train_id: int = 1,
    dist_to_station: float = 0.0, # 距下一站距离 (m)
) -> bytes:
    """打包 上位机 → 信号屏 显示数据 (66字节, 小端序)。

    文档: 外部系统对接方案 4.5 节
    """
    off = SIGNAL_SCREEN_OFFSET
    data = bytearray(SIGNAL_SCREEN_LEN)

    # -- 报文头 (24字节) --
    struct.pack_into("<I", data, off["identify"], SIGNAL_SCREEN_HEADER_ID)
    struct.pack_into("<H", data, off["total_len"], SIGNAL_SCREEN_LEN)
    struct.pack_into("<H", data, off["data_len"], SIGNAL_SCREEN_LEN - 24)
    struct.pack_into("<Q", data, off["timestamp"], timestamp_ms & 0xFFFFFFFFFFFFFFFF)
    struct.pack_into("<H", data, off["verify_type"], verify_type & 0xFFFF)
    struct.pack_into("<H", data, off["verify_code"], verify_code & 0xFFFF)
    struct.pack_into("<H", data, off["protocol_id"], protocol_id & 0xFFFF)
    struct.pack_into("<H", data, off["msg_id"], msg_id & 0xFFFF)

    # -- 时间 --
    struct.pack_into("<H", data, off["year"], year & 0xFFFF)
    struct.pack_into("<H", data, off["month"], month & 0xFFFF)
    struct.pack_into("<H", data, off["day"], day & 0xFFFF)
    struct.pack_into("<H", data, off["hour"], hour & 0xFFFF)
    struct.pack_into("<H", data, off["minute"], minute & 0xFFFF)
    struct.pack_into("<H", data, off["second"], second & 0xFFFF)

    # -- 站信息 (3字节) --
    data[off["curr_station_id"]] = curr_station_id & 0xFF
    data[off["next_station_id"]] = next_station_id & 0xFF
    data[off["end_station_id"]] = end_station_id & 0xFF

    # -- 状态 (4字节) --
    data[off["cm_state"]] = cm_state & 0xFF
    data[off["mm_state"]] = mm_state & 0xFF
    data[off["ctc_state"]] = ctc_state & 0xFF
    data[off["run_direction"]] = run_direction & 0xFF
    data[off["reserved_43"]] = 0

    # -- 运行数据 (20字节) --
    struct.pack_into("<f", data, off["speed"], float(speed))
    struct.pack_into("<f", data, off["acceleration"], float(acceleration))
    struct.pack_into("<H", data, off["traction_cut"], traction_cut & 0xFFFF)
    struct.pack_into("<H", data, off["speed_limit"], speed_limit & 0xFFFF)
    data[off["mode"]] = mode & 0xFF
    data[off["traction_state"]] = traction_state & 0xFF
    data[off["brake_state"]] = brake_state & 0xFF
    data[off["eb_state"]] = eb_state & 0xFF
    data[off["event_id"]] = event_id & 0xFF
    data[off["signal_state"]] = signal_state & 0xFF
    struct.pack_into("<H", data, off["train_id"], train_id & 0xFFFF)
    struct.pack_into("<f", data, off["dist_to_station"], float(dist_to_station))

    return bytes(data)


# ====================================================================
# 信号屏桥接客户端
# ====================================================================

class MmiBridge:
    """信号屏 (MMI) TCP 通信桥接。

    连接到信号屏设备，按需发送66字节信号/速度报文。

    用法:
        bridge = MmiBridge()
        bridge.connect()
        bridge.send_from_state(state)
    """

    def __init__(self, host: str = SIGNAL_SCREEN_DEVICE_IP, port: int = SIGNAL_SCREEN_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self._connected = False

        self.last_sent_data: Optional[bytes] = None
        self.last_send_time: Optional[float] = None
        self.send_count = 0

    @property
    def connected(self) -> bool:
        return self._connected and self.sock is not None

    def connect(self) -> bool:
        """连接信号屏。"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(CONNECT_TIMEOUT)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(RECV_TIMEOUT)
            self._connected = True
            logger.info(f"信号屏已连接: {self.host}:{self.port}")
            return True
        except socket.timeout:
            msg = f"信号屏 {self.host}:{self.port} 连接超时 (>{CONNECT_TIMEOUT}s)"
            logger.error(msg)
            print(f"  ⚠ {msg}")
            self.sock = None
            self._connected = False
            return False
        except ConnectionRefusedError:
            msg = f"信号屏 {self.host}:{self.port} 拒绝连接 (服务未启动?)"
            logger.error(msg)
            print(f"  ⚠ {msg}")
            self.sock = None
            self._connected = False
            return False
        except socket.gaierror as e:
            msg = f"信号屏 {self.host}:{self.port} 地址解析失败: {e}"
            logger.error(msg)
            print(f"  ⚠ {msg}")
            self.sock = None
            self._connected = False
            return False
        except OSError as e:
            msg = f"信号屏 {self.host}:{self.port} 连接异常 (OSError: {e})"
            logger.error(msg)
            print(f"  ⚠ {msg}")
            self.sock = None
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"信号屏连接失败 {self.host}:{self.port}: {e}")
            print(f"  ⚠ 信号屏 {self.host}:{self.port} 未知错误: {e}")
            self.sock = None
            self._connected = False
            return False

    def disconnect(self):
        """断开信号屏连接。"""
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        logger.info("信号屏已断开")

    def send(self, data: bytes) -> bool:
        """发送一帧信号屏数据 (66字节)。

        Args:
            data: 66字节的完整报文。

        Returns:
            True 发送成功, False 失败。
        """
        if not self.sock or not self._connected:
            return False
        try:
            self.sock.sendall(data)
            self.last_sent_data = data
            self.last_send_time = time.time()
            self.send_count += 1
            return True
        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.error(f"信号屏发送失败: {e}")
            self._connected = False
            return False

    def send_from_state(self, state: dict) -> bool:
        """从仿真状态字典构建并发送信号屏报文。

        Args:
            state: 包含以下键的字典:
                - speed (km/h), acceleration (m/s²), speed_limit (km/h)
                - mode (驾驶模式编码), eb_state, traction_state, brake_state
                - curr_station_id, next_station_id, end_station_id
                - run_direction, dist_to_station (m), train_id

        Returns:
            True 发送成功, False 失败。
        """
        now = datetime.now()
        data = pack_signal_screen(
            timestamp_ms=int(time.time() * 1000),
            year=now.year, month=now.month, day=now.day,
            hour=now.hour, minute=now.minute, second=now.second,
            curr_station_id=state.get("curr_station_id", 0),
            next_station_id=state.get("next_station_id", 0),
            end_station_id=state.get("end_station_id", 0),
            cm_state=state.get("cm_state", 0),
            mm_state=state.get("mm_state", 0),
            ctc_state=state.get("ctc_state", 0),
            run_direction=state.get("run_direction", 0),
            speed=state.get("speed", 0.0),
            acceleration=state.get("acceleration", 0.0),
            traction_cut=state.get("traction_cut", 0),
            speed_limit=state.get("speed_limit", 0),
            mode=state.get("mode", 0),
            traction_state=state.get("traction_state", 0),
            brake_state=state.get("brake_state", 0),
            eb_state=state.get("eb_state", 0),
            event_id=state.get("event_id", 0),
            signal_state=state.get("signal_state", 0),
            train_id=state.get("train_id", 1),
            dist_to_station=state.get("dist_to_station", 0.0),
        )
        return self.send(data)

    def is_connected(self) -> bool:
        return self.connected