"""列车运行阻力计算（VHC-03 ~ VHC-06）。

约定：返回值为力 (N)，正值表示阻碍前进方向的力。坡度阻力在下坡时为负
（助力）。速度对外单位 km/h，内部换算为 m/s 参与计算。
"""

from __future__ import annotations

import math

from .models import AIR_DENSITY, GRAVITY, VehicleParams

KMH_TO_MS = 1.0 / 3.6


def davis_resistance(params: VehicleParams, mass: float, speed_kmh: float) -> float:
    """Davis 基本阻力（VHC-03）。

    公式::

        R = (A + B·v) · m·g + 0.5·ρ·Cd·Af·v²

    其中 A、B 为归一化经验系数，v 为 m/s。
    """
    v = abs(speed_kmh) * KMH_TO_MS
    rolling = (params.davis_a + params.davis_b * v) * mass * GRAVITY
    aero = 0.5 * AIR_DENSITY * params.davis_c_drag_coeff * params.davis_c_front_area * v * v
    return rolling + aero


def gradient_resistance(mass: float, gradient_permille: float) -> float:
    """坡度附加阻力（VHC-04）。

    ``R_g = m·g·sin(θ) ≈ m·g·(gradient/1000)``，上坡为正、下坡为负。
    """
    return mass * GRAVITY * (gradient_permille / 1000.0)


def curve_resistance(
    mass: float, curvature_radius: float, coeff: float = 600.0
) -> float:
    """弯道附加阻力（VHC-05）。

    采用经验比阻力 ``r_c(‰) = k / R``，再换算为力::

        R_c = m·g·(k / R) / 1000

    直线（半径为 0 或负）时无弯道阻力。
    """
    if curvature_radius is None or curvature_radius <= 0 or math.isinf(curvature_radius):
        return 0.0
    specific_permille = coeff / curvature_radius
    return mass * GRAVITY * (specific_permille / 1000.0)


def tunnel_resistance(davis_value: float, is_tunnel: bool, factor: float) -> float:
    """隧道附加空气阻力（VHC-06）。

    以 Davis 基本阻力为基准，隧道内额外增加 ``(factor - 1) · R_davis``。
    非隧道段为 0。
    """
    if not is_tunnel:
        return 0.0
    return (factor - 1.0) * davis_value
