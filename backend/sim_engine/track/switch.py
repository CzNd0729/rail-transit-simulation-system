"""道岔管理器（TRK-06/TRK-08/TRK-09）。

管理道岔定位/反位状态的切换，模拟机械转换时延。
"""

from __future__ import annotations

from .models import Switch


class SwitchManager:
    """道岔状态管理器。

    每个道岔有三种状态：normal（定位）、reverse（反位）、
    transitioning（转换中）。切换需经过 3 秒转换时延。
    """

    def __init__(self, switches: list[Switch]):
        self._switches = {s.id: s for s in switches}

    # ── TRK-08：道岔状态查询 ──

    def query(self, switch_id: str) -> Switch | None:
        """查询道岔当前状态。返回 None 表示道岔不存在。"""
        return self._switches.get(switch_id)

    # ── TRK-09：道岔控制接口 ──

    def set_state(self, switch_id: str, target: str) -> bool:
        """设置道岔目标状态，启动转换时延。

        Args:
            switch_id: 道岔 ID
            target: "normal" 或 "reverse"

        Returns:
            True 表示已接受指令并开始转换，False 表示拒绝
            （道岔不存在、无效目标、已在转换中、已是目标状态）。
        """
        sw = self._switches.get(switch_id)
        if sw is None:
            return False
        if target not in ("normal", "reverse"):
            return False
        if sw.state == "transitioning":
            return False
        if sw.state == target:
            return False
        sw.state = "transitioning"
        sw.transition_elapsed = 0.0
        sw._target_state = target
        return True

    # ── 转换时延推进 ──

    def update(self, dt: float) -> None:
        """推进所有转换中道岔的 elapsed 时间。

        应在每个仿真步调用一次。
        """
        for sw in self._switches.values():
            if sw.state != "transitioning":
                continue
            sw.transition_elapsed += dt
            if sw.transition_elapsed >= sw.transition_time:
                sw.state = sw._target_state
                sw.transition_elapsed = sw.transition_time

    # ── 序列化 ──

    def switch_list(self) -> list[dict]:
        """返回道岔状态列表，供 snapshot 序列化。

        格式与 API 文档附录 B 对齐：
            {"switchId", "chainage", "type", "normalDirection",
             "reverseDirection", "lateralSpeedLimit", "state",
             "transitionElapsed", "transitionTime"}
        """
        return [
            {
                "switchId": s.id,
                "chainage": s.chainage,
                "type": s.switch_type,
                "normalDirection": s.normal_direction,
                "reverseDirection": s.reverse_direction,
                "lateralSpeedLimit": s.lateral_speed_limit,
                "state": s.state,
                "transitionElapsed": s.transition_elapsed,
                "transitionTime": s.transition_time,
            }
            for s in self._switches.values()
        ]
