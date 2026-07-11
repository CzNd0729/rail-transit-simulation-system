"""ATP 安全防护（SIG-04 单列车简化版）。"""

from __future__ import annotations

from sim_engine.core.config import AtpConfig
from sim_engine.signaling.models import MaProfile, SafetyStatus


class ATPController:
    """固定安全距离 MA + 超速防护；不计算动态 MA 速度曲线。"""

    def __init__(self, config: AtpConfig):
        self._config = config

    def atp_speed_limit(self, speed_limit_kmh: float) -> float:
        return speed_limit_kmh * (1.0 - self._config.overspeed_margin)

    def check_overspeed(self, speed_kmh: float, speed_limit_kmh: float) -> SafetyStatus:
        threshold = speed_limit_kmh * (1.0 + self._config.overspeed_margin)
        if speed_kmh > threshold:
            return SafetyStatus.EMERGENCY_BRAKE
        return SafetyStatus.NORMAL

    def ma_end_chainage(self, train_position: float, target_station_chainage: float | None) -> float:
        if target_station_chainage is None:
            return train_position
        return target_station_chainage

    def build_ma_profile(
        self,
        train_id: str,
        train_position: float,
        target_station_chainage: float | None,
    ) -> MaProfile:
        return MaProfile(
            train_id=train_id,
            ma_end_chainage=self.ma_end_chainage(train_position, target_station_chainage),
            safety_distance=self._config.safety_distance,
        )
