import type { VehicleParams } from '../types/simulation';

/** 默认车辆参数 — 对齐迭代一 MVP 验收场景 1 + API 文档 3.1 */
export const DEFAULT_VEHICLE_PARAMS: VehicleParams = {
  id: 'TYPE_A',
  name: 'A型车',
  empty_mass: 200_000,
  passenger_capacity: 1500,
  max_speed: 80,
  max_traction_force: 400_000,
  max_brake_force: 350_000,
  davis_A: 0.01,
  davis_B: 0.0001,
  davis_C_front_area: 10,
  davis_C_drag_coeff: 0.5,
  curve_resist_coeff: 600,
  tunnel_resist_factor: 1.2,
  regeneration_efficiency: 0.3,
  traction_curve: [
    { speed: 0, force_percent: 1.0, sort_order: 0 },
    { speed: 40, force_percent: 1.0, sort_order: 1 },
    { speed: 80, force_percent: 0.5, sort_order: 2 },
  ],
};
