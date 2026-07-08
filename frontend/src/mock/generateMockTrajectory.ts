import { MOCK_STATIONS, getSegmentAt } from './mockTrackBlueprint';
import { computeMass, computeAcceleration, msToKmh, kmhToMs } from './mockDynamics';
import { decideMode, PLATFORM_HALF_LENGTH } from './mockThreeStage';
import type { MockReplayFrame, MockSimInput } from '../types/simulation';

const DT = 0.1;
const MAX_STEPS = 60_000;

function shouldArriveAtStation(speedKmh: number, position: number, stationChainage: number): boolean {
  return speedKmh < 0.5 && Math.abs(position - stationChainage) <= PLATFORM_HALF_LENGTH;
}

function appendDwellFrames(
  frames: MockReplayFrame[],
  t: number,
  stationChainage: number,
  dwellTime: number,
  mass: number,
  passengerCount: number,
): number {
  const dwellSteps = Math.round(dwellTime / DT);
  for (let d = 0; d < dwellSteps; d++) {
    frames.push({
      t: Math.round(t * 10) / 10,
      position: stationChainage,
      speed: 0,
      acceleration: 0,
      mode: 'coasting',
      mass,
      passenger_count: passengerCount,
      pantograph_voltage: 1500,
      power_demand: 0,
    });
    t += DT;
  }
  return t;
}

export function generateMockTrajectory(input: MockSimInput): MockReplayFrame[] {
  const frames: MockReplayFrame[] = [];
  const mass = computeMass(input.vehicle, input.passenger_load_ratio);
  const passengerCount = Math.round(input.vehicle.passenger_capacity * input.passenger_load_ratio);

  let t = 0;
  let position = MOCK_STATIONS[0].chainage;
  let speedKmh = 0;
  let stationIdx = 0;

  for (let step = 0; step < MAX_STEPS; step++) {
    const nextStation = MOCK_STATIONS[stationIdx + 1];
    if (!nextStation) break;

    const seg = getSegmentAt(position, input.track.gradient);
    const speedLimit = input.track.speed_limit ?? seg.speed_limit;
    const vTarget = speedLimit * input.signal.target_speed_ratio;
    const gradient = seg.id === 'SEC02' ? input.track.gradient : seg.gradient;

    const distToStation = nextStation.chainage - position;

    const { mode, cruiseHold } = decideMode({
      speedKmh,
      position,
      nextStationChainage: nextStation.chainage,
      vTarget,
      mass,
      maxBrakeForce: input.vehicle.max_brake_force,
    });

    if (cruiseHold) {
      speedKmh = vTarget;
    }

    if (mode === 'braking' && distToStation <= 30 && speedKmh < 2) {
      position = nextStation.chainage;
      speedKmh = 0;
    }

    let acceleration = computeAcceleration({
      mode, speedKmh, mass, vehicle: input.vehicle, gradient, cruiseHold,
    });

    if (cruiseHold || (mode === 'braking' && speedKmh === 0)) {
      acceleration = 0;
    }

    frames.push({
      t: Math.round(t * 10) / 10,
      position: Math.round(position * 10) / 10,
      speed: Math.round(speedKmh * 10) / 10,
      acceleration: Math.round(acceleration * 100) / 100,
      mode,
      mass,
      passenger_count: passengerCount,
      pantograph_voltage: 1500,
      power_demand: mode === 'traction' ? 3200 : 0,
    });

    const vMs = kmhToMs(speedKmh);
    const vNext = Math.max(0, vMs + acceleration * DT);
    speedKmh = msToKmh(vNext);
    position += ((kmhToMs(speedKmh) + vMs) / 2) * DT;
    t += DT;

    if (shouldArriveAtStation(speedKmh, position, nextStation.chainage)) {
      position = nextStation.chainage;
      speedKmh = 0;

      t = appendDwellFrames(
        frames, t, nextStation.chainage, input.signal.dwell_time, mass, passengerCount,
      );

      stationIdx++;
      if (stationIdx >= MOCK_STATIONS.length - 1) break;
    }
  }

  return frames;
}
