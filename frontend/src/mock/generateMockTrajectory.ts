import { MOCK_STATIONS, getSegmentAt } from './mockTrackBlueprint';
import { computeMass, computeAcceleration, msToKmh, kmhToMs } from './mockDynamics';
import { decideMode, PLATFORM_HALF_LENGTH } from './mockThreeStage';
import type { MockReplayFrame, MockSimInput, TrainMode } from '../types/simulation';

const DT = 0.1;
const MAX_STEPS = 60_000;

function signalFrameFields(
  mode: TrainMode,
  speedKmh: number,
  position: number,
  targetStation: { id: string; chainage: number },
): Pick<MockReplayFrame, 'running_phase' | 'distance_to_station' | 'target_station_id' | 'traction_level' | 'brake_level'> {
  const distance = Math.max(0, targetStation.chainage - position);
  let running_phase: string;
  if (speedKmh < 0.5 && distance < 20) running_phase = 'dwell';
  else if (mode === 'braking') running_phase = 'braking';
  else if (mode === 'traction') running_phase = 'traction';
  else running_phase = 'coasting';

  return {
    running_phase,
    distance_to_station: Math.round(distance),
    target_station_id: targetStation.id,
    traction_level: mode === 'traction' ? 0.8 : 0,
    brake_level: mode === 'braking' ? 0.5 : 0,
  };
}

function shouldArriveAtStation(speedKmh: number, position: number, stationChainage: number): boolean {
  return speedKmh < 0.5 && Math.abs(position - stationChainage) <= PLATFORM_HALF_LENGTH;
}

function appendDwellFrames(
  frames: MockReplayFrame[],
  t: number,
  stationChainage: number,
  targetStation: { id: string; chainage: number },
  dwellTime: number,
  mass: number,
  passengerCount: number,
  prevAccel: number,
): { t: number; prevAccel: number } {
  const dwellSteps = Math.round(dwellTime / DT);
  let accel = prevAccel;
  for (let d = 0; d < dwellSteps; d++) {
    const jerk = DT > 0 ? (0 - accel) / DT : 0;
    frames.push({
      t: Math.round(t * 10) / 10,
      position: stationChainage,
      speed: 0,
      acceleration: 0,
      jerk: Math.round(jerk * 100) / 100,
      mode: 'coasting',
      mass,
      passenger_count: passengerCount,
      pantograph_voltage: 1500,
      power_demand: 0,
      running_phase: 'dwell',
      distance_to_station: Math.max(0, Math.round(targetStation.chainage - stationChainage)),
      target_station_id: targetStation.id,
      traction_level: 0,
      brake_level: 0,
    });
    accel = 0;
    t += DT;
  }
  return { t, prevAccel: 0 };
}

export function generateMockTrajectory(input: MockSimInput): MockReplayFrame[] {
  const frames: MockReplayFrame[] = [];
  const mass = computeMass(input.vehicle, input.passenger_load_ratio);
  const passengerCount = Math.round(input.vehicle.passenger_capacity * input.passenger_load_ratio);

  let t = 0;
  let position = MOCK_STATIONS[0].chainage;
  let speedKmh = 0;
  let stationIdx = 0;
  let prevAccel = 0;

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

    const jerk = DT > 0 ? (acceleration - prevAccel) / DT : 0;

    frames.push({
      t: Math.round(t * 10) / 10,
      position: Math.round(position * 10) / 10,
      speed: Math.round(speedKmh * 10) / 10,
      acceleration: Math.round(acceleration * 100) / 100,
      jerk: Math.round(jerk * 100) / 100,
      mode,
      mass,
      passenger_count: passengerCount,
      pantograph_voltage: 1500,
      power_demand: mode === 'traction' ? 3200 : 0,
      ...signalFrameFields(mode, speedKmh, position, nextStation),
    });
    prevAccel = acceleration;

    const vMs = kmhToMs(speedKmh);
    const vNext = Math.max(0, vMs + acceleration * DT);
    speedKmh = msToKmh(vNext);
    position += ((kmhToMs(speedKmh) + vMs) / 2) * DT;
    t += DT;

    if (shouldArriveAtStation(speedKmh, position, nextStation.chainage)) {
      position = nextStation.chainage;
      speedKmh = 0;

      const targetAfterDwell = MOCK_STATIONS[stationIdx + 2] ?? nextStation;
      const dwell = appendDwellFrames(
        frames, t, nextStation.chainage, targetAfterDwell, input.signal.dwell_time, mass, passengerCount, prevAccel,
      );
      t = dwell.t;
      prevAccel = dwell.prevAccel;

      stationIdx++;
      if (stationIdx >= MOCK_STATIONS.length - 1) break;
    }
  }

  return frames;
}
