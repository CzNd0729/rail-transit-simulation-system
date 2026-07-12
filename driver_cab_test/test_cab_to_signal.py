#!/usr/bin/env python3
"""
测试：司机台 → 信号系统（控制上行）
========================================
模拟司机在驾驶台的操作，验证控制指令上行到信号系统的正确性。

场景1: 司机钥匙激活（开钥匙→驾驶室激活→ATP安全输入置位）
场景2: 司控器牵引操作（手柄牵引位→牵引命令→百分比编码）
场景3: 紧急制动按钮（按下紧急制动按钮→ATP安全输入置位）
场景4: ATO启动（按下ATO启动按钮→模式切换→ATO非安全输入）
场景5: 车门控制（开/关门按钮→ATP非安全输入位变化）
场景6: 组合操作（完整发车流程：钥匙→模式→牵引→加速）
"""

import socket
import time
import logging
import os
import sys
from typing import Optional

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from driver_cab_test.config import (
    PLC_SERVER_IP, PLC_PORT_A,
    PLC_TO_UPPER_LEN, UPPER_TO_PLC_LEN,
    TEST_TIMEOUT, DRIVE_MODE,
    ATP_SAFE_INPUT, ATP_NONSAFE_INPUT, ATO_NONSAFE_INPUT,
)
from driver_cab_test.protocols import (
    pack_plc_to_upper, parse_plc_to_upper,
    pack_upper_to_plc, parse_upper_to_plc,
    encode_atp_safe_input, encode_atp_nonsafe_input, encode_ato_nonsafe_input,
    pack_db_to_signal_cab_binary, parse_db_to_signal_cab_binary,
    _decode_bits,
)

logging.basicConfig(
    level=logging.INFO,
    format="[测试-司机台→信号] %(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class CabToSignalTester:
    """司机台 → 信号系统 上行测试器"""

    def __init__(self):
        self.plc_sock: Optional[socket.socket] = None
        self.test_results = []

    def connect_plc(self, host: str = PLC_SERVER_IP, port: int = PLC_PORT_A) -> bool:
        try:
            self.plc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.plc_sock.settimeout(TEST_TIMEOUT)
            self.plc_sock.connect((host, port))
            logger.info(f"PLC 连接成功: {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"PLC 连接失败: {e}")
            return False

    def disconnect(self):
        if self.plc_sock:
            try:
                self.plc_sock.close()
            except Exception:
                pass
            self.plc_sock = None

    def send_plc(self, cmd: bytes) -> bool:
        if not self.plc_sock:
            return False
        try:
            self.plc_sock.sendall(cmd)
            return True
        except Exception as e:
            logger.warning(f"发送PLC指令失败: {e}")
            return False

    def recv_plc(self) -> Optional[dict]:
        if not self.plc_sock:
            return None
        try:
            data = self.plc_sock.recv(PLC_TO_UPPER_LEN)
            if len(data) >= PLC_TO_UPPER_LEN:
                return parse_plc_to_upper(data[:PLC_TO_UPPER_LEN])
        except socket.timeout:
            pass
        except Exception as e:
            logger.warning(f"接收PLC数据失败: {e}")
        return None

    def _simulate_cab_operation(self, bits: dict) -> tuple[int, int, int]:
        """
        模拟司机台操作，生成 ATP 安全输入/非安全输入/ATO非安全输入的 UINT32 值
        """
        atp_safe = encode_atp_safe_input(bits.get("atp_safe", {}))
        atp_nonsafe = encode_atp_nonsafe_input(bits.get("atp_nonsafe", {}))
        ato_nonsafe = encode_ato_nonsafe_input(bits.get("ato_nonsafe", {}))
        return atp_safe, atp_nonsafe, ato_nonsafe

    def _build_cab_upper_to_plc(self, **kwargs) -> bytes:
        """构建上位机→PLC 控制报文"""
        return pack_upper_to_plc(**kwargs)

    # ---- 测试场景 ----

    def test_scene_1_key_activation(self) -> bool:
        """场景1: 司机钥匙激活"""
        logger.info("=" * 50)
        logger.info("场景1: 司机钥匙激活")
        logger.info("=" * 50)

        # 模拟司机操作：插入钥匙，激活驾驶室
        cab_bits = {
            "atp_safe": {
                "cab_active": True,        # 本端驾驶室激活
                "key_active": True,        # 本端司机钥匙激活
                "train_complete": True,    # 列车完整
                "handle_zero_forward": True,  # 手柄零位+方向向前
                "eb_applied": False,
                "door_closed": True,
                "traction_cut": True,      # 牵引已切断（初始）
            },
            "atp_nonsafe": {
                "master_zero": True,       # 司控器在零位
                "eum_active": False,
            },
            "ato_nonsafe": {
                "battery_ok": True,        # 蓄电池正常
            },
        }

        atp_safe, atp_nonsafe, ato_nonsafe = self._simulate_cab_operation(cab_bits)
        logger.info(f"ATP安全输入: 0x{atp_safe:08x}")
        logger.info(f"ATP非安全输入: 0x{atp_nonsafe:08x}")

        # 解码验证各比特位
        safe_bits = _decode_bits(atp_safe, ATP_SAFE_INPUT)
        assert safe_bits["cab_active"] == True, "驾驶室应激活"
        assert safe_bits["key_active"] == True, "钥匙应激活"
        assert safe_bits["train_complete"] == True, "列车应完整"
        assert safe_bits["handle_zero_forward"] == True, "手柄应在零位且方向向前"
        assert safe_bits["eb_applied"] == False, "不应有紧急制动"

        # 构建 PLC 上行报文
        # 钥匙激活后，PLC 状态应更新
        cmd = self._build_cab_upper_to_plc(
            header=0xDCBA,
            traction_cmd=0,  # 无牵引
            traction_pct=0,
            brake_pct=0,
            target_speed_cm_s=0,
        )
        self.send_plc(cmd)

        # 构建总控→信号 驾驶台开关量报文
        raw = pack_db_to_signal_cab_binary(
            train_id=1,
            atp_safe_input=atp_safe,
            atp_nonsafe_input=atp_nonsafe,
            ato_nonsafe_input=ato_nonsafe,
        )
        parsed = parse_db_to_signal_cab_binary(raw)
        logger.info(f"驾驶台开关量解析: cab_active={parsed['atp_safe_bits']['cab_active']}, "
                    f"key_active={parsed['atp_safe_bits']['key_active']}, "
                    f"door_closed={parsed['atp_safe_bits']['door_closed']}")

        time.sleep(0.2)
        plc_resp = self.recv_plc()
        if plc_resp:
            logger.info(f"PLC响应: train_id={plc_resp['train_id']}, "
                        f"speed={plc_resp['speed_cm_s']}cm/s")

        logger.info("✓ 场景1 通过: 司机钥匙激活编码正确")
        return True

    def test_scene_2_master_controller_traction(self) -> bool:
        """场景2: 司控器牵引操作"""
        logger.info("=" * 50)
        logger.info("场景2: 司控器牵引操作")
        logger.info("=" * 50)

        # 模拟司机推动手柄到牵引位，50%牵引
        cab_bits = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "train_complete": True,
                "door_closed": True,
                "traction_cut": False,       # 牵引已接通
                "eb_applied": False,
                "handle_zero_forward": False, # 手柄不在零位
            },
            "atp_nonsafe": {
                "master_traction": True,      # 司控器在牵引位
                "master_zero": False,         # 不在零位
            },
            "ato_nonsafe": {
                "battery_ok": True,
            },
        }

        atp_safe, atp_nonsafe, ato_nonsafe = self._simulate_cab_operation(cab_bits)

        # 编码验证
        safe_bits = _decode_bits(atp_safe, ATP_SAFE_INPUT)
        assert safe_bits["traction_cut"] == False, "牵引应已接通"
        assert safe_bits["handle_zero_forward"] == False, "手柄不应在零位"

        # 构建 PLC 上行报文：牵引50%
        cmd = self._build_cab_upper_to_plc(
            traction_cmd=0x55,  # 牵引
            traction_pct=50,
            brake_pct=0,
            target_speed_cm_s=5000,  # 50km/h
        )
        self.send_plc(cmd)

        # 构建 ATP 非安全输入中包含司控器牵引位
        raw = pack_db_to_signal_cab_binary(
            train_id=1,
            atp_safe_input=atp_safe,
            atp_nonsafe_input=atp_nonsafe,
            ato_nonsafe_input=ato_nonsafe,
        )
        parsed = parse_db_to_signal_cab_binary(raw)
        logger.info(f"牵引操作: master_traction={parsed['atp_nonsafe_bits']['master_traction']}, "
                    f"traction_cut={parsed['atp_safe_bits']['traction_cut']}")

        # 验证牵引百分比编码
        plc_cmd = parse_upper_to_plc(cmd)
        assert plc_cmd["traction_cmd"] == 0x55, "牵引命令应为0x55"
        assert plc_cmd["traction_pct"] == 50, "牵引百分比应为50%"
        assert plc_cmd["target_speed_cm_s"] == 5000, "目标速度应为5000cm/s"
        logger.info(f"PLC上行报文: cmd=0x{plc_cmd['traction_cmd']:02x}, "
                    f"pct={plc_cmd['traction_pct']}%, "
                    f"target={plc_cmd['target_speed_cm_s']}cm/s")

        logger.info("✓ 场景2 通过: 司控器牵引操作编码正确")
        return True

    def test_scene_3_emergency_brake_btn(self) -> bool:
        """场景3: 紧急制动按钮按下"""
        logger.info("=" * 50)
        logger.info("场景3: 紧急制动按钮按下")
        logger.info("=" * 50)

        # 模拟司机按下紧急制动按钮
        cab_bits = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "eb_applied": True,         # 紧急制动施加
                "traction_cut": True,       # 牵引切断
                "door_closed": True,
                "train_complete": True,
                "handle_zero_forward": False,
                "brake_fault": False,
            },
            "atp_nonsafe": {
                "master_zero": True,
            },
            "ato_nonsafe": {
                "battery_ok": True,
            },
        }

        atp_safe, atp_nonsafe, ato_nonsafe = self._simulate_cab_operation(cab_bits)

        safe_bits = _decode_bits(atp_safe, ATP_SAFE_INPUT)
        assert safe_bits["eb_applied"] == True, "紧急制动应施加"
        assert safe_bits["traction_cut"] == True, "牵引应切断"

        # 构建 PLC 上行报文：紧急制动，制动100%
        cmd = self._build_cab_upper_to_plc(
            traction_cmd=0xAA,  # 制动
            traction_pct=0,
            brake_pct=100,
            target_speed_cm_s=0,
            eb_reset=0,  # 未复位
        )
        self.send_plc(cmd)

        raw = pack_db_to_signal_cab_binary(
            train_id=1,
            atp_safe_input=atp_safe,
            atp_nonsafe_input=atp_nonsafe,
            ato_nonsafe_input=ato_nonsafe,
        )
        parsed = parse_db_to_signal_cab_binary(raw)
        logger.info(f"紧急制动: eb_applied={parsed['atp_safe_bits']['eb_applied']}, "
                    f"traction_cut={parsed['atp_safe_bits']['traction_cut']}")

        # 验证PLC报文
        plc_cmd = parse_upper_to_plc(cmd)
        assert plc_cmd["brake_pct"] == 100, "制动百分比应为100%"
        logger.info(f"PLC上行报文: cmd=0x{plc_cmd['traction_cmd']:02x}, "
                    f"brake={plc_cmd['brake_pct']}%")

        logger.info("✓ 场景3 通过: 紧急制动按钮编码正确")
        return True

    def test_scene_4_ato_start(self) -> bool:
        """场景4: ATO启动"""
        logger.info("=" * 50)
        logger.info("场景4: ATO启动")
        logger.info("=" * 50)

        # 模拟司机按下ATO启动按钮，切换到AM模式
        cab_bits = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "door_closed": True,
                "train_complete": True,
                "traction_cut": False,
                "eb_applied": False,
                "handle_zero_forward": True,
            },
            "atp_nonsafe": {
                "ato_start_btn": True,     # ATO启动按钮按下
                "master_zero": True,
            },
            "ato_nonsafe": {
                "battery_ok": True,
                "door_mode_am": True,      # 门模式AM
            },
        }

        atp_safe, atp_nonsafe, ato_nonsafe = self._simulate_cab_operation(cab_bits)

        nonsafe_bits = _decode_bits(atp_nonsafe, ATP_NONSAFE_INPUT)
        assert nonsafe_bits["ato_start_btn"] == True, "ATO启动按钮应按下"

        ato_bits = _decode_bits(ato_nonsafe, ATO_NONSAFE_INPUT)
        assert ato_bits["door_mode_am"] == True, "门模式应为AM"

        # 构建 PLC 上行报文
        cmd = self._build_cab_upper_to_plc(
            traction_cmd=0x55,
            traction_pct=80,
            brake_pct=0,
            target_speed_cm_s=6000,
            ato_cmd=1,  # ATO使能
        )
        self.send_plc(cmd)

        raw = pack_db_to_signal_cab_binary(
            train_id=1,
            atp_safe_input=atp_safe,
            atp_nonsafe_input=atp_nonsafe,
            ato_nonsafe_input=ato_nonsafe,
        )
        parsed = parse_db_to_signal_cab_binary(raw)
        logger.info(f"ATO启动: ato_start_btn={parsed['atp_nonsafe_bits']['ato_start_btn']}, "
                    f"door_mode_am={parsed['ato_nonsafe_bits']['door_mode_am']}")

        logger.info("✓ 场景4 通过: ATO启动操作编码正确")
        return True

    def test_scene_5_door_control(self) -> bool:
        """场景5: 车门控制"""
        logger.info("=" * 50)
        logger.info("场景5: 车门控制")
        logger.info("=" * 50)

        # 开门操作
        open_bits = {
            "atp_nonsafe": {
                "right_door_open": True,   # 右门开门按钮按下
                "left_door_open": False,
                "left_door_close": False,
                "right_door_close": False,
            },
        }

        _, atp_nonsafe_open, _ = self._simulate_cab_operation({
            "atp_nonsafe": open_bits["atp_nonsafe"],
        })

        open_decoded = _decode_bits(atp_nonsafe_open, ATP_NONSAFE_INPUT)
        assert open_decoded["right_door_open"] == True, "右门开门按钮应按下"
        assert open_decoded["left_door_open"] == False, "左门开门按钮不应按下"
        logger.info(f"开门操作: right_door_open={open_decoded['right_door_open']}")

        # 关门操作
        close_bits = {
            "atp_nonsafe": {
                "right_door_open": False,
                "right_door_close": True,  # 右门关门按钮按下
                "left_door_close": True,   # 左门关门按钮按下
            },
        }

        _, atp_nonsafe_close, _ = self._simulate_cab_operation({
            "atp_nonsafe": close_bits["atp_nonsafe"],
        })

        close_decoded = _decode_bits(atp_nonsafe_close, ATP_NONSAFE_INPUT)
        assert close_decoded["right_door_close"] == True, "右门关门按钮应按下"
        assert close_decoded["left_door_close"] == True, "左门关门按钮应按下"
        assert close_decoded["right_door_open"] == False, "开门按钮应释放"
        logger.info(f"关门操作: right_door_close={close_decoded['right_door_close']}, "
                    f"left_door_close={close_decoded['left_door_close']}")

        # 验证编码不冲突（同一UINT32中不同位互不影响）
        # 开门时 0x00002000 置位，关门时 0x00004000 置位
        assert atp_nonsafe_open != atp_nonsafe_close, "开门和关门的编码应不同"
        logger.info(f"开门编码: 0x{atp_nonsafe_open:08x}, 关门编码: 0x{atp_nonsafe_close:08x}")

        logger.info("✓ 场景5 通过: 车门控制编码正确，位互不冲突")
        return True

    def test_scene_6_full_departure(self) -> bool:
        """场景6: 完整发车流程（组合操作）"""
        logger.info("=" * 50)
        logger.info("场景6: 完整发车流程")
        logger.info("=" * 50)

        # 阶段1: 初始状态
        logger.info("  阶段1: 初始状态")
        phase1 = {
            "atp_safe": {
                "cab_active": False,
                "key_active": False,
                "door_closed": False,
                "traction_cut": True,
                "train_complete": True,
                "eb_applied": True,
                "handle_zero_forward": False,
            },
            "atp_nonsafe": {"master_zero": False},
            "ato_nonsafe": {"battery_ok": True},
        }
        p1_atp_safe, p1_atp_ns, p1_ato = self._simulate_cab_operation(phase1)
        p1_decoded = _decode_bits(p1_atp_safe, ATP_SAFE_INPUT)
        assert p1_decoded["cab_active"] == False
        assert p1_decoded["eb_applied"] == True
        logger.info(f"    初始: cab={p1_decoded['cab_active']}, eb={p1_decoded['eb_applied']}")

        # 阶段2: 插入钥匙，激活驾驶室
        logger.info("  阶段2: 钥匙激活")
        phase2 = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "door_closed": True,
                "traction_cut": True,
                "train_complete": True,
                "eb_applied": False,
                "handle_zero_forward": True,
                "confirm_btn": True,  # 确认按钮
            },
            "atp_nonsafe": {"master_zero": True},
            "ato_nonsafe": {"battery_ok": True},
        }
        p2_atp_safe, p2_atp_ns, p2_ato = self._simulate_cab_operation(phase2)
        p2_decoded = _decode_bits(p2_atp_safe, ATP_SAFE_INPUT)
        assert p2_decoded["cab_active"] == True
        assert p2_decoded["key_active"] == True
        assert p2_decoded["eb_applied"] == False
        assert p2_decoded["confirm_btn"] == True
        logger.info(f"    激活: cab={p2_decoded['cab_active']}, key={p2_decoded['key_active']}, "
                    f"eb={p2_decoded['eb_applied']}")

        # 阶段3: 推动手柄牵引
        logger.info("  阶段3: 牵引加速")
        phase3 = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "door_closed": True,
                "traction_cut": False,
                "train_complete": True,
                "eb_applied": False,
                "handle_zero_forward": False,
                "dir_forward": True,
            },
            "atp_nonsafe": {
                "master_traction": True,
                "master_zero": False,
            },
            "ato_nonsafe": {"battery_ok": True},
        }
        p3_atp_safe, p3_atp_ns, p3_ato = self._simulate_cab_operation(phase3)
        p3_decoded = _decode_bits(p3_atp_safe, ATP_SAFE_INPUT)
        assert p3_decoded["traction_cut"] == False, "牵引接通"
        assert p3_decoded["dir_forward"] == True, "方向向前"
        p3_ns_decoded = _decode_bits(p3_atp_ns, ATP_NONSAFE_INPUT)
        assert p3_ns_decoded["master_traction"] == True, "司控器牵引位"
        logger.info(f"    牵引: traction_cut={p3_decoded['traction_cut']}, "
                    f"dir_forward={p3_decoded['dir_forward']}, "
                    f"master_traction={p3_ns_decoded['master_traction']}")

        # 阶段4: 巡航
        logger.info("  阶段4: 巡航")
        phase4 = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "door_closed": True,
                "traction_cut": False,
                "train_complete": True,
                "eb_applied": False,
                "handle_zero_forward": True,  # 回到零位巡航
                "dir_forward": True,
            },
            "atp_nonsafe": {"master_zero": True},
            "ato_nonsafe": {"battery_ok": True},
        }
        p4_atp_safe, p4_atp_ns, p4_ato = self._simulate_cab_operation(phase4)
        p4_decoded = _decode_bits(p4_atp_safe, ATP_SAFE_INPUT)
        assert p4_decoded["handle_zero_forward"] == True
        logger.info(f"    巡航: handle_zero={p4_decoded['handle_zero_forward']}")

        # 阶段5: 制动停车
        logger.info("  阶段5: 制动停车")
        phase5 = {
            "atp_safe": {
                "cab_active": True,
                "key_active": True,
                "door_closed": True,
                "traction_cut": True,
                "train_complete": True,
                "eb_applied": False,
                "hold_brake": True,  # 保持制动
                "handle_zero_forward": True,
                "dir_forward": True,
            },
            "atp_nonsafe": {
                "master_zero": True,
            },
            "ato_nonsafe": {"battery_ok": True},
        }
        p5_atp_safe, p5_atp_ns, p5_ato = self._simulate_cab_operation(phase5)
        p5_decoded = _decode_bits(p5_atp_safe, ATP_SAFE_INPUT)
        assert p5_decoded["hold_brake"] == True, "保持制动应施加"
        assert p5_decoded["traction_cut"] == True, "牵引应切断"
        logger.info(f"    停车: hold_brake={p5_decoded['hold_brake']}, "
                    f"traction_cut={p5_decoded['traction_cut']}")

        # 验证各阶段编码互不相同
        encodings = [p1_atp_safe, p2_atp_safe, p3_atp_safe, p4_atp_safe, p5_atp_safe]
        assert len(set(encodings)) == 5, "各阶段ATP安全输入编码应互不相同"
        logger.info(f"    各阶段编码唯一性验证通过")

        logger.info("✓ 场景6 通过: 完整发车流程各阶段编码正确，互不冲突")
        return True

    def run_all(self, connect: bool = True):
        """运行所有测试场景"""
        passed = 0
        failed = 0

        # 先运行编解码测试（不需要网络连接）
        tests_no_net = [
            ("场景6: 完整发车流程", self.test_scene_6_full_departure),
            ("场景5: 车门控制", self.test_scene_5_door_control),
            ("场景1: 司机钥匙激活", self.test_scene_1_key_activation),
            ("场景2: 司控器牵引操作", self.test_scene_2_master_controller_traction),
            ("场景3: 紧急制动按钮", self.test_scene_3_emergency_brake_btn),
            ("场景4: ATO启动", self.test_scene_4_ato_start),
        ]

        for name, test_fn in tests_no_net:
            logger.info(f"\n{'='*60}")
            logger.info(f"运行: {name}")
            logger.info(f"{'='*60}")
            try:
                if test_fn():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error(f"✗ {name} 异常: {e}", exc_info=True)
                failed += 1

        # 需要网络连接的测试
        if connect and self.connect_plc():
            # 发送PLC报文验证实际通信
            logger.info("\n--- PLC通信验证 ---")
            cmd = self._build_cab_upper_to_plc(
                traction_cmd=0x55, traction_pct=30, target_speed_cm_s=3000
            )
            self.send_plc(cmd)
            time.sleep(0.2)
            resp = self.recv_plc()
            if resp:
                logger.info(f"PLC通信正常: speed={resp['speed_cm_s']}cm/s")
            self.disconnect()

        total = passed + failed
        logger.info("\n" + "=" * 60)
        logger.info(f"测试完成: {passed}/{total} 通过, {failed} 失败")
        logger.info("=" * 60)

        return failed == 0


def main():
    tester = CabToSignalTester()
    success = tester.run_all(connect=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()