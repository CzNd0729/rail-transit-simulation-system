import { describe, it, expect } from 'vitest';
import { computeMass, computeAcceleration } from './mockDynamics';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';

describe('computeAcceleration respects mass', () => {
  it('heavier train has lower traction acceleration', () => {
    const light = { ...DEFAULT_VEHICLE_PARAMS, empty_mass: 200_000 };
    const heavy = { ...DEFAULT_VEHICLE_PARAMS, empty_mass: 220_000 };
    const aLight = computeAcceleration({
      mode: 'traction', speedKmh: 20, mass: computeMass(light, 0.6), vehicle: light, gradient: 0,
    });
    const aHeavy = computeAcceleration({
      mode: 'traction', speedKmh: 20, mass: computeMass(heavy, 0.6), vehicle: heavy, gradient: 0,
    });
    expect(aHeavy).toBeLessThan(aLight);
  });

  it('larger frontal area increases resistance deceleration', () => {
    const small = { ...DEFAULT_VEHICLE_PARAMS, davis_C_front_area: 8 };
    const large = { ...DEFAULT_VEHICLE_PARAMS, davis_C_front_area: 14 };
    const m = computeMass(small, 0.6);
    const aSmall = computeAcceleration({
      mode: 'coasting', speedKmh: 60, mass: m, vehicle: small, gradient: 0,
    });
    const aLarge = computeAcceleration({
      mode: 'coasting', speedKmh: 60, mass: m, vehicle: large, gradient: 0,
    });
    expect(aLarge).toBeLessThan(aSmall);
  });

  it('lower max traction reduces acceleration', () => {
    const base = DEFAULT_VEHICLE_PARAMS;
    const weak = { ...base, max_traction_force: 300_000 };
    const m = computeMass(base, 0.6);
    const aBase = computeAcceleration({
      mode: 'traction', speedKmh: 10, mass: m, vehicle: base, gradient: 0,
    });
    const aWeak = computeAcceleration({
      mode: 'traction', speedKmh: 10, mass: m, vehicle: weak, gradient: 0,
    });
    expect(aWeak).toBeLessThan(aBase);
  });

  it('cruise hold balances resistance on uphill', () => {
    const vehicle = DEFAULT_VEHICLE_PARAMS;
    const mass = computeMass(vehicle, 0.6);
    const a = computeAcceleration({
      mode: 'coasting',
      speedKmh: 64,
      mass,
      vehicle,
      gradient: 30,
      cruiseHold: true,
    });
    expect(Math.abs(a)).toBeLessThan(0.001);
  });
});
