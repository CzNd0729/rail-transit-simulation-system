#!/usr/bin/env python3
"""
全链路联动测试（主入口）
===========================
模拟完整的驾驶循环，联动测试所有协议：

驾驶循环：初始上电 → 钥匙激活 → 模式选择 → 牵引加速 → 匀速巡航
         → 制动减速 → 站台停车 → 开门 → 关门 → 重新发车

测试链路：
  司机台操作 → ATP输入编码 → 总控数据库 → 信号系统
  → ATP/ATO输出编码 → 司机台显示（PLC+网络屏+信号屏）

测试模式：
  - 模拟模式（默认）：使用编解码验证，不依赖真实硬件
  - 硬件模式：连接真实PLC/网络屏/信号屏，发送真实报文
"""

import logging
import os
import sys
import time
from enum import IntEnum
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from driver_cab_test.config import (
    DRIVE_MODE, MAX_DRIVE_MODE, RUN_LEVEL,
    TRACTION_BRAKE, TRAIN_DIRECTION,
    SIGNAL_ASPECT, SWITCH_STATE,
    ATP_SAFE_INPUT, ATP_NONSAFE_INPUT, ATO_NONSAFE_INPUT,
    ATP_SAFE_OUTPUT, ATP_NONSAFE_OUTPUT, ATO_NONSAFE_OUTPUT,
    TEST_LOOP_COUNT,
)
from driver_cab_test.protocols import (
    pack_plc_to_upper, parse_plc_to_upper,
    pack_upper_to_plc, parse_upper_to_plc,
    pack_network_screen, parse_network_screen,
    pack_signal_screen, parse_signal_screen,
    _decode_bits, _encode_bits,
    encode_atp_safe_input, encode_atp_nonsafe_input, encode_ato_nonsafe_input,
    encode_atp_safe_output, encode_atp_nonsafe_output, encode_ato_nonsafe_output,
    pack_db_to_signal_cab_binary, parse_db_to_signal_cab_binary,
    pack_signal_to_db_cab_binary, parse_signal_to_db_cab_binary,
    pack_db_to_signal_train_data, parse_db_to_signal_train_data,
    pack_signal_to_db_train_data,
)

logging.basicConfig(
    level=logging.INFO,
    format="[全链路] %(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class TrainState(IntEnum):
    """列车运行阶段状态"""
    POWER_ON = 0       # 初始上电
    KEY_ACTIVATE = 1   # 钥匙激活
    MODE_SELECT = 2    # 模式选择
    ACCELERATE = 3     # 牵引加速
    CRUISE = 4         # 匀速巡航
    BRAKE = 5          # 制动减速
    STATION_STOP = 6   # 站台停车
    DOOR_OPEN = 7      # 开门
    DOOR_CLOSE = 8     # 关门
    RE_DEPART = 9      # 重新发车


class FullLoopTester:
    """全链路联动测试器"""

    def __init__(self):
        # 列车运行状态
        self.state = TrainState.POWER_ON
        self.speed_cm_s = 0
        self.target_speed_cm_s = 0
        self.position_cm = 0
        self.accel = 0
        self.door_open = False
        self.cab_active = False
        self.key_active = False
        self.eb_active = False
        self.ato_active = False
        self.traction_cut = True
        self.hold_brake = False
        self.mode = DRIVE_MODE["INIT"]
        self.run_level = RUN_LEVEL["INIT"]

        # 前方信号
        self.next_signal_aspect = SIGNAL_ASPECT["RED"]
        self.next_signal_id = 1
        self.target_distance_cm = 0
        self.permit_speed_cm_s = 8000  # 80km/h 默认限速

        # 站点信息
        self.stations = ["人民广场", "南京东路", "陆家嘴", "世纪大道"]
        self.current_station_idx = 0

        # 统计数据
        self.cycle_count = 0
        self.log_history = []

    def _get_current_station(self) -> str:
        """获取当前站名"""
        if self.current_station_idx < len(self.stations):
            return self.stations[self.current_station_idx]
        return "终点站"

    def _get_next_station(self) -> str:
        """获取下一站名"""
        idx = self.current_station_idx + 1
        if idx < len(self.stations):
            return self.stations[idx]
        return "--"

    # ---- 驾驶台操作（上行编码） ----

    def _cab_operation(self, atp_safe: dict, atp_nonsafe: dict, ato_nonsafe: dict) -> bytes:
        """模拟司机台操作，生成总控→信号 驾驶台开关量报文"""
        return pack_db_to_signal_cab_binary(
            train_id=1,
            atp_safe_input=encode_atp_safe_input(atp_safe),
            atp_nonsafe_input=encode_atp_nonsafe_input(atp_nonsafe),
            ato_nonsafe_input=encode_ato_nonsafe_input(ato_nonsafe),
        )

    # ---- 信号系统输出（下行编码） ----

    def _signal_output(self, atp_safe: dict, atp_nonsafe: dict, ato_nonsafe: dict,
                       vehicle: dict | None = None) -> bytes:
        """模拟信号系统输出，生成信号→总控 驾驶台开关量报文"""
        return pack_signal_to_db_cab_binary(
            train_id=1,
            atp_safe_output=encode_atp_safe_output(atp_safe),
            atp_nonsafe_output=encode_atp_nonsafe_output(atp_nonsafe),
            ato_nonsafe_output=encode_ato_nonsafe_output(ato_nonsafe),
            vehicle_output=_encode_bits(vehicle or {}, {"door_closed": 0x04000000}),
        )

    def _build_plc_data(self) -> bytes:
        """构建 PLC 下行数据"""
        return pack_plc_to_upper(
            train_id=1,
            speed_cm_s=self.speed_cm_s,
            accel=self.accel,
            master_controller=0x55 if self.state in (TrainState.ACCELERATE, TrainState.CRUISE) else 0,
            brake_pressure=0 if not self.hold_brake else 500,
            door_status=1 if self.door_open else 0,
            cab_active=1 if self.cab_active else 0,
            key_status=1 if self.key_active else 0,
            eb_status=1 if self.eb_active else 0,
            mode=self.mode,
        )

    def _build_network_screen(self) -> bytes:
        """构建网络屏显示数据"""
        return pack_network_screen(
            train_id=1,
            speed_km_h=self.speed_cm_s / 100.0,
            target_speed_km_h=self.target_speed_cm_s / 100.0,
            limit_speed_km_h=self.permit_speed_cm_s / 100.0,
            next_station=self._get_next_station(),
            door_status="开" if self.door_open else "关",
            mode_name={v: k for k, v in DRIVE_MODE.items()}.get(self.mode, "UNKNOWN"),
            voltage=1500.0,
            current=self.speed_cm_s * 0.02,  # 模拟电流随速度变化
            is_ato=self.ato_active,
            fault_info="紧急制动触发" if self.eb_active else "",
        )

    def _build_signal_screen(self) -> bytes:
        """构建信号屏（DMI）显示数据"""
        return pack_signal_screen(
            train_id=1,
            current_speed_cm_s=self.speed_cm_s,
            permit_speed_cm_s=self.permit_speed_cm_s,
            eb_trigger_speed_cm_s=self.permit_speed_cm_s + 1000,
            target_speed_cm_s=self.target_speed_cm_s,
            target_distance_cm=self.target_distance_cm,
            speed_change_distance_cm=max(0, self.target_distance_cm - 50000),
            current_mode=self.mode,
            max_mode=MAX_DRIVE_MODE["CBTC_FAM"],
            run_level=self.run_level,
            signal_aspect=self.next_signal_aspect,
            next_signal_id=self.next_signal_id,
            dmi_display=1 if self.key_active else 0,
        )

    # ---- 驾驶循环阶段 ----

    def _step_power_on(self):
        """阶段0: 初始上电"""
        self.state = TrainState.POWER_ON
        self.speed_cm_s = 0
        self.cab_active = False
        self.key_active = False
        self.eb_active = True
        self.traction_cut = True
        self.mode = DRIVE_MODE["INIT"]
        self.run_level = RUN_LEVEL["INIT"]
        self.door_open = False

        # 司机台操作：全部默认
        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": False, "key_active": False,
                "door_closed": False, "traction_cut": True,
                "train_complete": True, "eb_applied": True,
                "handle_zero_forward": False,
            },
            atp_nonsafe={"master_zero": False},
            ato_nonsafe={"battery_ok": True},
        )
        # 信号输出：全部默认
        sig_down = self._signal_output(
            atp_safe={"eb_output": True, "traction_cut_out": True},
            atp_nonsafe={},
            ato_nonsafe={},
        )
        logger.info(f"[上电] 初始状态, 紧急制动施加")
        return cab_up, sig_down

    def _step_key_activate(self):
        """阶段1: 钥匙激活"""
        self.state = TrainState.KEY_ACTIVATE
        self.cab_active = True
        self.key_active = True
        self.eb_active = False
        self.traction_cut = True
        self.mode = DRIVE_MODE["RM"]
        self.run_level = RUN_LEVEL["CBTC"]

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": True,
                "train_complete": True, "eb_applied": False,
                "handle_zero_forward": True, "confirm_btn": True,
                "dir_forward": True,
            },
            atp_nonsafe={"master_zero": True, "eum_active": False},
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": True,
                       "zero_speed": True, "train_start_light": True},
            atp_nonsafe={"ar_indicator": False},
            ato_nonsafe={"ato_active": False, "dir_forward": True},
        )
        logger.info(f"[激活] 驾驶室激活, 钥匙打开, 模式=RM, 列车完整")
        return cab_up, sig_down

    def _step_mode_select(self):
        """阶段2: 模式选择（切换到CM模式）"""
        self.state = TrainState.MODE_SELECT
        self.mode = DRIVE_MODE["CM"]
        self.traction_cut = False

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": False,
                "train_complete": True, "eb_applied": False,
                "handle_zero_forward": True, "dir_forward": True,
            },
            atp_nonsafe={"master_zero": True, "mode_up": True},
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": False,
                       "zero_speed": True, "ato_enable_1": True},
            atp_nonsafe={},
            ato_nonsafe={"dir_forward": True},
        )
        logger.info(f"[模式] 选择CM模式, 牵引接通, 信号允许发车")
        return cab_up, sig_down

    def _step_accelerate(self):
        """阶段3: 牵引加速"""
        self.state = TrainState.ACCELERATE
        self.speed_cm_s = 2000   # 20km/h
        self.accel = 100          # 1.0 m/s²
        self.target_speed_cm_s = 6000
        self.target_distance_cm = 300000
        self.next_signal_aspect = SIGNAL_ASPECT["GREEN"]
        self.next_signal_id = 5

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": False,
                "train_complete": True, "eb_applied": False,
                "handle_zero_forward": False, "dir_forward": True,
            },
            atp_nonsafe={"master_traction": True, "master_zero": False},
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": False,
                       "zero_speed": False, "train_start_light": False},
            atp_nonsafe={},
            ato_nonsafe={"dir_forward": True},
        )
        logger.info(f"[加速] speed={self.speed_cm_s/100:.0f}km/h, 绿灯, 目标距离={self.target_distance_cm/100:.0f}m")
        return cab_up, sig_down

    def _step_cruise(self):
        """阶段4: 匀速巡航"""
        self.state = TrainState.CRUISE
        self.speed_cm_s = 5500   # 55km/h
        self.accel = 0
        self.target_distance_cm = 150000
        self.position_cm += 10000

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": False,
                "train_complete": True, "eb_applied": False,
                "handle_zero_forward": True, "dir_forward": True,
            },
            atp_nonsafe={"master_zero": True},
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": False},
            atp_nonsafe={},
            ato_nonsafe={"dir_forward": True},
        )
        logger.info(f"[巡航] speed={self.speed_cm_s/100:.0f}km/h, 剩余距离={self.target_distance_cm/100:.0f}m")
        return cab_up, sig_down

    def _step_brake(self):
        """阶段5: 制动减速"""
        self.state = TrainState.BRAKE
        self.speed_cm_s = 3000   # 30km/h
        self.accel = -80          # -0.8 m/s²
        self.target_speed_cm_s = 0
        self.target_distance_cm = 30000
        self.next_signal_aspect = SIGNAL_ASPECT["RED_YELLOW"]
        self.next_signal_id = 8

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": False,
                "train_complete": True, "eb_applied": False,
                "handle_zero_forward": False, "dir_forward": True,
            },
            atp_nonsafe={"master_traction": False, "master_zero": False},
            ato_nonsafe={"battery_ok": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": False},
            atp_nonsafe={},
            ato_nonsafe={"brake_cmd": True, "dir_forward": True},
        )
        logger.info(f"[制动] speed={self.speed_cm_s/100:.0f}km/h, 红黄灯, 剩余={self.target_distance_cm/100:.0f}m")
        return cab_up, sig_down

    def _step_station_stop(self):
        """阶段6: 站台停车"""
        self.state = TrainState.STATION_STOP
        self.speed_cm_s = 0
        self.accel = 0
        self.target_speed_cm_s = 0
        self.target_distance_cm = 0
        self.hold_brake = True
        self.next_signal_aspect = SIGNAL_ASPECT["RED"]
        self.next_signal_id = 10

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": True,
                "train_complete": True, "eb_applied": False,
                "hold_brake": True, "handle_zero_forward": True,
                "dir_forward": True,
            },
            atp_nonsafe={"master_zero": True},
            ato_nonsafe={"battery_ok": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": True,
                       "zero_speed": True, "left_door_enable": True},
            atp_nonsafe={},
            ato_nonsafe={"hold_brake": True, "dir_forward": True},
        )
        logger.info(f"[停车] 已到站: {self._get_current_station()}, 零速, 保持制动")
        return cab_up, sig_down

    def _step_door_open(self):
        """阶段7: 开门"""
        self.state = TrainState.DOOR_OPEN
        self.door_open = True

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": False, "traction_cut": True,
                "train_complete": True, "eb_applied": False,
                "hold_brake": True, "handle_zero_forward": True,
                "dir_forward": True,
            },
            atp_nonsafe={
                "master_zero": True,
                "right_door_open": True,
                "left_door_open": True,
            },
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": True,
                       "zero_speed": True, "left_door_enable": True,
                       "right_door_enable": True},
            atp_nonsafe={},
            ato_nonsafe={"hold_brake": True, "open_left_door": True,
                         "open_right_door": True, "dir_forward": True},
        )
        logger.info(f"[开门] {self._get_current_station()} 站台侧开门")
        return cab_up, sig_down

    def _step_door_close(self):
        """阶段8: 关门"""
        self.state = TrainState.DOOR_CLOSE
        self.door_open = False

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": True,
                "train_complete": True, "eb_applied": False,
                "hold_brake": True, "handle_zero_forward": True,
                "dir_forward": True,
            },
            atp_nonsafe={
                "master_zero": True,
                "right_door_close": True,
                "left_door_close": True,
            },
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": True,
                       "zero_speed": True, "left_door_enable": False,
                       "right_door_enable": False},
            atp_nonsafe={},
            ato_nonsafe={"hold_brake": True, "close_left_door": True,
                         "close_right_door": True, "dir_forward": True},
        )
        logger.info(f"[关门] {self._get_current_station()} 门已关闭锁闭")
        return cab_up, sig_down

    def _step_re_depart(self):
        """阶段9: 重新发车"""
        self.state = TrainState.RE_DEPART
        self.hold_brake = False
        self.traction_cut = False
        self.speed_cm_s = 1000
        self.accel = 80
        self.target_speed_cm_s = 6000
        self.target_distance_cm = 400000
        self.next_signal_aspect = SIGNAL_ASPECT["GREEN"]
        self.next_signal_id = 15
        self.current_station_idx += 1

        cab_up = self._cab_operation(
            atp_safe={
                "cab_active": True, "key_active": True,
                "door_closed": True, "traction_cut": False,
                "train_complete": True, "eb_applied": False,
                "hold_brake": False, "handle_zero_forward": False,
                "dir_forward": True,
            },
            atp_nonsafe={"master_traction": True, "master_zero": False},
            ato_nonsafe={"battery_ok": True, "door_mode_am": True},
        )
        sig_down = self._signal_output(
            atp_safe={"eb_output": False, "traction_cut_out": False,
                       "zero_speed": False},
            atp_nonsafe={},
            ato_nonsafe={"hold_brake": False, "dir_forward": True},
        )
        logger.info(f"[发车] 驶向下一站: {self._get_next_station()}")
        return cab_up, sig_down

    # ---- 验证 ----

    def _verify(self, cab_up: bytes, sig_down: bytes, stage_name: str) -> bool:
        """验证上下行报文的一致性"""
        try:
            # 解析上行：司机台操作 → 信号系统
            cab_parsed = parse_db_to_signal_cab_binary(cab_up)

            # 解析下行：信号系统 → 司机台
            sig_parsed = parse_signal_to_db_cab_binary(sig_down)

            # 验证基本字段
            assert cab_parsed["train_id"] == 1
            assert sig_parsed["train_id"] == 1
            assert cab_parsed["header"] == (0xFF, 0xF1)
            assert sig_parsed["header"] == (0xFF, 0xF1)

            # 构建 PLC/网络屏/信号屏数据
            plc_data = self._build_plc_data()
            net_data = self._build_network_screen()
            sig_screen_data = self._build_signal_screen()

            # 验证各协议报文长度
            assert len(plc_data) == 46, f"PLC报文长度应为46, 实际{len(plc_data)}"
            assert len(net_data) == 572, f"网络屏报文长度应为572, 实际{len(net_data)}"
            assert len(sig_screen_data) == 66, f"信号屏报文长度应为66, 实际{len(sig_screen_data)}"

            # 解析信号屏，验证速度一致性
            sig_parsed2 = parse_signal_screen(sig_screen_data)
            assert sig_parsed2["current_speed_cm_s"] == self.speed_cm_s, \
                f"速度不一致: {sig_parsed2['current_speed_cm_s']} != {self.speed_cm_s}"

            # 记录
            self.log_history.append({
                "stage": stage_name,
                "state": self.state,
                "speed": self.speed_cm_s,
                "cab_active": self.cab_active,
                "eb": self.eb_active,
                "door": self.door_open,
                "mode": self.mode,
            })

            return True

        except AssertionError as e:
            logger.error(f"✗ 验证失败 [{stage_name}]: {e}")
            return False
        except Exception as e:
            logger.error(f"✗ 验证异常 [{stage_name}]: {e}")
            return False

    # ---- 运行 ----

    def run_full_loop(self, cycles: int = 1) -> bool:
        """运行完整驾驶循环"""
        overall_pass = True

        for cycle in range(cycles):
            logger.info("\n" + "=" * 70)
            logger.info(f"驾驶循环 #{cycle + 1}/{cycles}")
            logger.info("=" * 70)

            stages = [
                ("初始上电", self._step_power_on),
                ("钥匙激活", self._step_key_activate),
                ("模式选择", self._step_mode_select),
                ("牵引加速", self._step_accelerate),
                ("匀速巡航", self._step_cruise),
                ("制动减速", self._step_brake),
                ("站台停车", self._step_station_stop),
                ("开门", self._step_door_open),
                ("关门", self._step_door_close),
                ("重新发车", self._step_re_depart),
            ]

            for stage_name, stage_fn in stages:
                try:
                    cab_up, sig_down = stage_fn()
                    ok = self._verify(cab_up, sig_down, stage_name)
                    if not ok:
                        overall_pass = False
                except Exception as e:
                    logger.error(f"✗ 阶段[{stage_name}]异常: {e}", exc_info=True)
                    overall_pass = False

        return overall_pass

    def print_summary(self):
        """打印测试摘要"""
        logger.info("\n" + "=" * 70)
        logger.info("全链路测试摘要")
        logger.info("=" * 70)

        speeds = [h["speed"] / 100 for h in self.log_history]
        stages = [h["stage"] for h in self.log_history]

        logger.info(f"执行阶段: {' → '.join(stages)}")
        logger.info(f"速度变化: {min(speeds):.0f} ~ {max(speeds):.0f} km/h")
        logger.info(f"状态变化: {len(self.log_history)} 个阶段")

        # 验证关键状态转换
        has_eb = any(h["eb"] for h in self.log_history)
        has_door_open = any(h["door"] for h in self.log_history)

        if not has_eb:
            logger.info("✓ 紧急制动全程未异常触发")
        if has_door_open:
            logger.info("✓ 站台开门功能正常")
        if max(speeds) > 0:
            logger.info(f"✓ 列车成功运行: 最高速度 {max(speeds):.0f} km/h")

        # 打印时间线
        logger.info("\n状态时间线:")
        for h in self.log_history:
            mode_name = {v: k for k, v in DRIVE_MODE.items()}.get(h["mode"], "?")
            logger.info(f"  [{h['stage']:8s}] speed={h['speed']/100:6.1f}km/h  "
                        f"cab={h['cab_active']}  eb={h['eb']}  "
                        f"door={'开' if h['door'] else '关'}  mode={mode_name}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="司机台全链路联动测试")
    parser.add_argument("--cycles", type=int, default=1, help="驾驶循环次数")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 70)
    logger.info("司机台全链路联动测试开始")
    logger.info(f"驾驶循环次数: {args.cycles}")
    logger.info("=" * 70)

    tester = FullLoopTester()
    success = tester.run_full_loop(cycles=args.cycles)
    tester.print_summary()

    if success:
        logger.info("\n✓ 全链路联动测试通过")
    else:
        logger.error("\n✗ 全链路联动测试存在失败项目")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())