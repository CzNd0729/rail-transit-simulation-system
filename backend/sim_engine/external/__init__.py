"""
外部系统通信层（PLC / 网络屏 / 信号屏 / 总控节点 UDP）。

**已弃用** — 外部系统接入方案已废弃，后端默认直接对接前端。
保留此包仅作参考，不再维护。

功能:
  提供与真实司机台 PLC、网络屏（HMI）、信号屏（MMI）以及总控数据库节点
  的 TCP/UDP 通信能力，将外部输入注入仿真引擎，并将引擎状态输出到外设。

用法（仅作历史参考）:
    from sim_engine.external.bridge import ExternalBridge
    bridge = ExternalBridge(use_real_hardware=False)
    bridge.start_all()
    bridge.update_from_engine(snapshot, sim_params)
    plc_input = bridge.get_plc_input()
"""

from . import plc_bridge, hmi_bridge, mmi_bridge, udp_bridge
from .bridge import ExternalBridge
from .plc_bridge import (
    PlcBridge, parse_plc_to_upper, pack_plc_to_upper,
    pack_upper_to_plc, parse_upper_to_plc,
)
from .plc_simulator import PlcSimulator
from .hmi_bridge import HmiBridge, pack_network_screen, parse_network_screen_request
from .mmi_bridge import MmiBridge, pack_signal_screen
from .udp_bridge import UdpBridge, pack_train_data_to_db, parse_db_command

__all__ = [
    "ExternalBridge",
    "PlcBridge", "PlcSimulator",
    "parse_plc_to_upper", "pack_plc_to_upper",
    "pack_upper_to_plc", "parse_upper_to_plc",
    "HmiBridge", "pack_network_screen", "parse_network_screen_request",
    "MmiBridge", "pack_signal_screen",
    "UdpBridge", "pack_train_data_to_db", "parse_db_command",
]