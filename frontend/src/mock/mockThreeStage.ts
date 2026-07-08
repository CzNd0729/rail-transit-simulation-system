import type { TrainMode } from '../types/simulation';

/** 站台半长 (m)，与 MVP TRK-04 / mockTrackBlueprint 一致 */
export const PLATFORM_HALF_LENGTH = 15;

/** 进入恒速巡航的速度容差 (km/h) */
const CRUISE_ENTRY_MARGIN_KMH = 0.5;

export function decideMode(state: {
  speedKmh: number;
  position: number;
  nextStationChainage: number;
  vTarget: number;
  mass: number;
  maxBrakeForce: number;
}): { mode: TrainMode; cruiseHold: boolean } {
  const distToStation = state.nextStationChainage - state.position;

  if (state.speedKmh < 0.5) {
    if (distToStation <= PLATFORM_HALF_LENGTH) {
      return { mode: 'coasting', cruiseHold: false };
    }
    const aBrake = state.maxBrakeForce / state.mass;
    const vRefMs = state.vTarget / 3.6;
    const dBrake = aBrake > 0 ? (vRefMs * vRefMs) / (2 * aBrake) : 0;
    if (distToStation <= dBrake) {
      return { mode: 'braking', cruiseHold: false };
    }
    return { mode: 'traction', cruiseHold: false };
  }

  const aBrake = state.maxBrakeForce / state.mass;
  // 用目标速度算制动距离，避免减速过程中阈值缩小而退出制动
  const vRefMs = state.vTarget / 3.6;
  const dBrake = aBrake > 0 ? (vRefMs * vRefMs) / (2 * aBrake) : 0;

  if (distToStation <= dBrake) {
    return { mode: 'braking', cruiseHold: false };
  }

  if (state.speedKmh < state.vTarget - CRUISE_ENTRY_MARGIN_KMH) {
    return { mode: 'traction', cruiseHold: false };
  }

  return { mode: 'coasting', cruiseHold: true };
}
