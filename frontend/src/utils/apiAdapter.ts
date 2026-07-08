import type {
  ApiSimulationSnapshot,
  SimulationParams,
  SimulationSnapshot,
  SimulationStats,
  TrainState,
} from '../types/simulation';

const VEHICLE_KEY_MAP: Record<string, string> = {
  empty_mass: 'emptyMass',
  passenger_capacity: 'passengerCapacity',
  max_speed: 'maxSpeed',
  max_traction_force: 'maxTractionForce',
  max_brake_force: 'maxBrakeForce',
  davis_A: 'davisA',
  davis_B: 'davisB',
  davis_C_front_area: 'davisCFrontArea',
  davis_C_drag_coeff: 'davisCDragCoeff',
  curve_resist_coeff: 'curveResistCoeff',
  tunnel_resist_factor: 'tunnelResistFactor',
  regeneration_efficiency: 'regenerationEfficiency',
};

const VEHICLE_KEY_REVERSE = Object.fromEntries(
  Object.entries(VEHICLE_KEY_MAP).map(([snake, camel]) => [camel, snake]),
);

function mapTrain(t: ApiSimulationSnapshot['trains'][0]): TrainState {
  return {
    id: t.id,
    position: t.position,
    speed: t.speed,
    acceleration: t.acceleration,
    mode: t.mode,
    mass: t.mass,
    passenger_count: t.passengerCount,
    door_status: t.doorStatus,
    pantograph_voltage: t.pantographVoltage,
    power_demand: t.powerDemand,
    fault_alarm: t.faultAlarm,
  };
}

export function parseServerSnapshot(raw: ApiSimulationSnapshot): SimulationSnapshot {
  return {
    clock: {
      elapsed: raw.clock.elapsed,
      speed_multiplier: raw.clock.speedMultiplier,
    },
    trains: raw.trains.map(mapTrain),
    power: {
      substations: [],
      voltage_profile: [],
      total_consumption: raw.power.totalConsumption,
      total_regeneration: raw.power.totalRegeneration,
      regeneration_rate: 0,
    },
    signaling: { commands: [], emergency_brake: [], train_intervals: [] },
    track: { occupancy: [], switch_states: [] },
    events: raw.events ?? [],
  };
}

export function toApiParamUpdate(params: Partial<SimulationParams>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  if (params.vehicle) {
    const v: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(params.vehicle)) {
      if (val === undefined) continue;
      v[VEHICLE_KEY_MAP[k] ?? k] = val;
    }
    result.vehicle = v;
  }
  if (params.signal) {
    result.signal = {
      ...(params.signal.dwell_time !== undefined && { dwellTime: params.signal.dwell_time }),
      ...(params.signal.target_speed_ratio !== undefined && {
        targetSpeedRatio: params.signal.target_speed_ratio,
      }),
      ...(params.signal.departure_interval !== undefined && {
        departureInterval: params.signal.departure_interval,
      }),
    };
  }
  if (params.track) {
    result.track = {
      ...(params.track.gradient !== undefined && { gradient: params.track.gradient }),
      ...(params.track.curvature !== undefined && { curvature: params.track.curvature }),
      ...(params.track.speed_limit !== undefined && { speedLimit: params.track.speed_limit }),
    };
  }
  return result;
}

export function parseApiParams(raw: Record<string, unknown>): Partial<SimulationParams> {
  const result: Partial<SimulationParams> = {};

  const vehicleRaw = raw.vehicle as Record<string, unknown> | undefined;
  if (vehicleRaw) {
    const vehicle: SimulationParams['vehicle'] = {};
    for (const [k, val] of Object.entries(vehicleRaw)) {
      if (val === undefined) continue;
      const snakeKey = VEHICLE_KEY_REVERSE[k] ?? k;
      (vehicle as Record<string, unknown>)[snakeKey] = val;
    }
    result.vehicle = vehicle;
  }

  const trackRaw = raw.track as Record<string, unknown> | undefined;
  if (trackRaw) {
    result.track = {
      ...(trackRaw.gradient !== undefined && { gradient: trackRaw.gradient as number }),
      ...(trackRaw.curvature !== undefined && { curvature: trackRaw.curvature as number }),
      ...(trackRaw.speedLimit !== undefined && { speed_limit: trackRaw.speedLimit as number }),
    };
  }

  const powerRaw = raw.power as Record<string, unknown> | undefined;
  if (powerRaw) {
    result.power = {
      ...(powerRaw.pantographVoltage !== undefined && {
        pantograph_voltage: powerRaw.pantographVoltage as number,
      }),
      ...(powerRaw.substationCapacity !== undefined && {
        substation_capacity: powerRaw.substationCapacity as number,
      }),
    };
  }

  const signalRaw = raw.signal as Record<string, unknown> | undefined;
  if (signalRaw) {
    result.signal = {
      ...(signalRaw.dwellTime !== undefined && { dwell_time: signalRaw.dwellTime as number }),
      ...(signalRaw.departureInterval !== undefined && {
        departure_interval: signalRaw.departureInterval as number,
      }),
      ...(signalRaw.targetSpeedRatio !== undefined && {
        target_speed_ratio: signalRaw.targetSpeedRatio as number,
      }),
    };
  }

  return result;
}

export function parseSimulationSummary(raw: Record<string, unknown>): Partial<SimulationStats> {
  return {
    trip_time: Number(raw.totalTime ?? raw.total_time ?? 0),
    avg_speed: Number(raw.avgSpeed ?? raw.avg_speed ?? 0),
    max_speed: Number(raw.maxSpeed ?? raw.max_speed ?? 0),
  };
}
