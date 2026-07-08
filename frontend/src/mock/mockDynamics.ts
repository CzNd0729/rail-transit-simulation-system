import type { TrainMode, VehicleParams } from '../types/simulation';

const G = 9.81;
const RHO = 1.2;

export function kmhToMs(v: number) { return v / 3.6; }
export function msToKmh(v: number) { return v * 3.6; }

export function computeMass(vehicle: VehicleParams, passengerLoadRatio: number): number {
  const passengers = vehicle.passenger_capacity * passengerLoadRatio * 60;
  return vehicle.empty_mass + passengers;
}

export function computeDavisResistance(speedMs: number, mass: number, vehicle: VehicleParams): number {
  const A = vehicle.davis_A * mass * G;
  const B = vehicle.davis_B * mass * G;
  const C = 0.5 * RHO * vehicle.davis_C_drag_coeff * vehicle.davis_C_front_area;
  return A + B * speedMs + C * speedMs * speedMs;
}

export function computeGradeResistance(gradientPermil: number, mass: number): number {
  return mass * G * (gradientPermil / 1000);
}

export function lookupTractionForce(speedKmh: number, vehicle: VehicleParams): number {
  const curve = [...vehicle.traction_curve].sort((a, b) => a.speed - b.speed);
  if (curve.length === 0) return vehicle.max_traction_force;

  let percent = curve[0].force_percent;
  for (let i = 1; i < curve.length; i++) {
    if (speedKmh <= curve[i].speed) {
      const prev = curve[i - 1];
      const span = curve[i].speed - prev.speed;
      const t = span > 0 ? (speedKmh - prev.speed) / span : 0;
      percent = prev.force_percent + t * (curve[i].force_percent - prev.force_percent);
      return vehicle.max_traction_force * percent;
    }
    percent = curve[i].force_percent;
  }
  return vehicle.max_traction_force * percent;
}

export function computeAcceleration(args: {
  mode: TrainMode;
  speedKmh: number;
  mass: number;
  vehicle: VehicleParams;
  gradient: number;
  cruiseHold?: boolean;
}): number {
  const v = kmhToMs(args.speedKmh);
  const resist = computeDavisResistance(v, args.mass, args.vehicle)
    + computeGradeResistance(args.gradient, args.mass);

  if (args.mode === 'stopped') {
    return 0;
  }

  // 已停车时不施加制动力，避免速度钳位在 0 仍输出负加速度
  if (args.speedKmh < 0.5 && args.mode === 'braking') {
    return 0;
  }

  if (args.cruiseHold) {
    const maxTraction = lookupTractionForce(args.speedKmh, args.vehicle);
    const force = Math.min(resist, maxTraction);
    return (force - resist) / args.mass;
  }

  let force = 0;
  if (args.mode === 'traction') force = lookupTractionForce(args.speedKmh, args.vehicle);
  if (args.mode === 'braking') force = -args.vehicle.max_brake_force;
  return (force - resist) / args.mass;
}
