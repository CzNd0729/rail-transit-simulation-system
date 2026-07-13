"""外部系统通信模块单元测试。

测试编解码的正确性，包括边界条件和异常情况。
"""

from __future__ import annotations

import struct

from sim_engine.external.protocol import (
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    NETWORK_SCREEN_LEN, NETWORK_SCREEN_REQUEST_LEN,
    SIGNAL_SCREEN_LEN,
    NETWORK_SCREEN_OFFSET,
)
from sim_engine.external.plc_bridge import (
    parse_plc_to_upper, pack_upper_to_plc,
    PLC_HEADER_ID,
)
from sim_engine.external.hmi_bridge import (
    pack_network_screen, parse_network_screen_request,
)
from sim_engine.external.mmi_bridge import pack_signal_screen
from sim_engine.external.udp_bridge import (
    pack_train_data_to_db, parse_db_command,
)
from sim_engine.external.bridge import ExternalBridge


def _make_plc_data() -> bytes:
    data = bytearray(PLC_TO_UPPER_LEN)
    struct.pack_into("<I", data, 0, PLC_HEADER_ID)
    struct.pack_into("<H", data, 4, PLC_TO_UPPER_LEN)
    struct.pack_into("<H", data, 6, 22)
    struct.pack_into("<H", data, 8, 2026)
    struct.pack_into("<H", data, 10, 7)
    struct.pack_into("<H", data, 12, 13)
    struct.pack_into("<H", data, 14, 15)
    struct.pack_into("<H", data, 16, 30)
    struct.pack_into("<H", data, 18, 0)
    data[24] = 0x02 | 0x20   # hscb + door_closed
    data[25] = 0x01 | 0x04   # ato_available + ato_active
    struct.pack_into("<H", data, 26, 6000)
    data[28] = 0x01          # eb_button
    data[29] = 0x01          # open_left_door
    struct.pack_into("<H", data, 36, 1)
    struct.pack_into("<H", data, 38, 1)
    struct.pack_into("<H", data, 40, 12800)
    struct.pack_into("<H", data, 42, 0)
    return bytes(data)


# ========== PLC 协议测试 ==========

def test_plc_parse_normal():
    data = _make_plc_data()
    parsed = parse_plc_to_upper(data)
    assert parsed["identify_ok"] is True
    assert parsed["year"] == 2026
    assert parsed["month"] == 7
    assert parsed["day"] == 13
    assert parsed["vehicle_speed"] == 6000
    assert parsed["hscb"] is True
    assert parsed["door_closed_indicator"] is True
    assert parsed["ato_available"] is True
    assert parsed["ato_active"] is True
    assert parsed["eb_button_locked"] is True
    assert parsed["open_left_door"] is True
    assert parsed["dir_handle_str"] == "向前"
    assert parsed["main_handle_str"] == "牵引"
    assert abs(parsed["traction_level_pct"] - 50.0) < 0.1
    assert parsed["brake_level_pct"] == 0.0


def test_plc_parse_too_short():
    try:
        parse_plc_to_upper(b"")
        assert False, "应抛出 ValueError"
    except ValueError:
        pass


def test_plc_parse_all_zeros():
    """所有字段为 0 的边界情况。"""
    data = bytearray(PLC_TO_UPPER_LEN)
    struct.pack_into("<I", data, 0, PLC_HEADER_ID)
    struct.pack_into("<H", data, 4, PLC_TO_UPPER_LEN)
    struct.pack_into("<H", data, 6, 22)
    parsed = parse_plc_to_upper(bytes(data))
    assert parsed["identify_ok"] is True
    assert parsed["vehicle_speed"] == 0
    assert parsed["hscb"] is False


def test_plc_pack_upper():
    data = pack_upper_to_plc(
        year=2026, month=7, day=13,
        hour=15, minute=30, second=0,
        hscb=1, door_closed=1,
        ato_available=1, ato_active=1,
        vehicle_speed=6000,
    )
    assert len(data) == UPPER_TO_PLC_LEN
    ident = struct.unpack_from("<I", data, 0)[0]
    assert ident == PLC_HEADER_ID
    speed = struct.unpack_from("<H", data, 26)[0]
    assert speed == 6000


def test_plc_parse_bad_identify():
    """错误的标识符。"""
    data = bytearray(PLC_TO_UPPER_LEN)
    struct.pack_into("<I", data, 0, 0xDEADBEEF)
    struct.pack_into("<H", data, 4, PLC_TO_UPPER_LEN)
    parsed = parse_plc_to_upper(bytes(data))
    assert parsed["identify_ok"] is False


# ========== 网络屏协议测试 ==========

def test_hmi_pack_normal():
    data = pack_network_screen(
        year=2026, month=7, day=13,
        speed=60.0, acceleration=0.5,
        power_pull=2000, net_pressure=1500, speed_limit=80,
        curr_station_id=3, next_station_id=4,
        train_no=1,
    )
    assert len(data) == NETWORK_SCREEN_LEN
    speed = struct.unpack_from("<f", data, NETWORK_SCREEN_OFFSET["speed"])[0]
    assert abs(speed - 60.0) < 0.01
    accel = struct.unpack_from("<f", data, NETWORK_SCREEN_OFFSET["acceleration"])[0]
    assert abs(accel - 0.5) < 0.01
    station_id = data[NETWORK_SCREEN_OFFSET["curr_station_id"]]
    assert station_id == 3


def test_hmi_pack_defaults():
    """默认值打包，应不报错。"""
    data = pack_network_screen()
    assert len(data) == NETWORK_SCREEN_LEN
    speed = struct.unpack_from("<f", data, NETWORK_SCREEN_OFFSET["speed"])[0]
    assert speed == 0.0
    net_p = struct.unpack_from("<H", data, NETWORK_SCREEN_OFFSET["net_pressure"])[0]
    assert net_p == 1500


def test_hmi_pack_max_values():
    """边界最大值。"""
    data = pack_network_screen(
        speed=65504.0,
        power_pull=65535,
        speed_limit=65535,
        net_pressure=65535,
        train_no=65535,
    )
    assert len(data) == NETWORK_SCREEN_LEN


def test_hmi_request_parse():
    """网络屏 → 上位机 牵引切除请求。"""
    req = bytearray(NETWORK_SCREEN_REQUEST_LEN)
    struct.pack_into("<I", req, 0, 0x55AA55AA)
    struct.pack_into("<H", req, 4, NETWORK_SCREEN_REQUEST_LEN)
    struct.pack_into("<H", req, 6, 2)
    req[24] = 0x04
    parsed = parse_network_screen_request(bytes(req))
    assert parsed["identify_ok"] is True
    assert parsed["pull_cut"]["car_3"] is True
    assert parsed["pull_cut"]["car_1"] is False


def test_hmi_request_too_short():
    try:
        parse_network_screen_request(b"")
        assert False
    except ValueError:
        pass


# ========== 信号屏协议测试 ==========

def test_mmi_pack_normal():
    data = pack_signal_screen(
        speed=60.0, acceleration=0.5,
        speed_limit=80, mode=3,
        train_id=1, dist_to_station=500.0,
        curr_station_id=3,
    )
    assert len(data) == SIGNAL_SCREEN_LEN
    speed = struct.unpack_from("<f", data, 44)[0]
    assert abs(speed - 60.0) < 0.01
    dist = struct.unpack_from("<f", data, 64)[0]
    assert abs(dist - 500.0) < 0.01
    station_id = data[36]
    assert station_id == 3


def test_mmi_pack_defaults():
    data = pack_signal_screen()
    assert len(data) == SIGNAL_SCREEN_LEN


def test_mmi_direction_encoding():
    """上行/下行方向编码。"""
    data_down = pack_signal_screen(run_direction=1, train_id=1)
    data_up = pack_signal_screen(run_direction=0, train_id=1)
    assert data_down[42] == 1
    assert data_up[42] == 0


# ========== UDP 协议测试 ==========

def test_udp_pack_single_train():
    trains = [{"acceleration": 0.5, "speed": 16.67, "position": 1000.0}]
    data = pack_train_data_to_db(trains)
    assert len(data) == 480
    accel = struct.unpack_from("<d", data, 0)[0]
    speed = struct.unpack_from("<d", data, 8)[0]
    pos = struct.unpack_from("<d", data, 16)[0]
    assert abs(accel - 0.5) < 0.001
    assert abs(speed - 16.67) < 0.01
    assert abs(pos - 1000.0) < 0.1


def test_udp_pack_multiple_trains():
    trains = [
        {"acceleration": 0.5, "speed": 16.67, "position": 1000.0},
        {"acceleration": 0.0, "speed": 0.0, "position": 500.0},
    ]
    data = pack_train_data_to_db(trains)
    accel2 = struct.unpack_from("<d", data, 24)[0]
    assert accel2 == 0.0


def test_udp_pack_empty():
    data = pack_train_data_to_db([])
    assert len(data) == 480
    val = struct.unpack_from("<d", data, 0)[0]
    assert val == 0.0


def test_udp_parse_command():
    data = bytearray(320)
    struct.pack_into("<d", data, 0, 1.0)
    struct.pack_into("<d", data, 8, 80.0)
    struct.pack_into("<d", data, 16, 2.0)
    struct.pack_into("<d", data, 24, 50.0)
    parsed = parse_db_command(bytes(data))
    assert len(parsed["trains"]) == 20
    assert parsed["trains"][0]["command"] == 1
    assert parsed["trains"][0]["command_str"] == "加速"
    assert abs(parsed["trains"][0]["percentage"] - 80.0) < 0.01
    assert parsed["trains"][1]["command"] == 2
    assert parsed["trains"][1]["command_str"] == "减速"


def test_udp_parse_empty():
    """空数据解析。"""
    parsed = parse_db_command(b"")
    assert len(parsed["trains"]) == 0


# ========== 桥接器集成测试 ==========

def test_bridge_simulation_mode():
    bridge = ExternalBridge(use_real_hardware=False)
    assert bridge.plc is not None
    assert bridge.hmi is not None
    assert bridge.mmi is not None
    assert bridge.udp is not None

    plc_input = bridge.get_plc_input()
    assert plc_input["connected"] is False
    assert plc_input["eb_button"] is False
    assert plc_input["traction_level_pct"] == 0.0

    bridge.set_sim_plc_input(eb_button=True, dir_handle=1, traction_level_pct=50.0)
    plc_input = bridge.get_plc_input()
    assert plc_input["eb_button"] is True
    assert plc_input["dir_handle"] == 1
    assert plc_input["traction_level_pct"] == 50.0