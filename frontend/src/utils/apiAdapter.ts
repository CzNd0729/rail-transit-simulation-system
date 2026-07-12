import type {
  ApiControlCommand,
  ApiSimulationSnapshot,
  SimulationParams,
  SimulationSnapshot,
  SimulationStats,
  Switch,
  TrackCircuit,
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
    jerk: t.jerk ?? 0,
    mode: t.mode,
    mass: t.mass,
    passenger_count: t.passengerCount,
    door_status: t.doorStatus,
    pantograph_voltage: t.pantographVoltage,
    power_demand: t.powerDemand,
    distance_to_station: t.distanceToStation ?? 0,
    target_station_id: t.targetStationId ?? '',
    direction: t.direction ?? 'up',
    fault_alarm: t.faultAlarm,
  };
}

function mapControlCommand(c: ApiControlCommand) {
  return {
    train_id: c.trainId,
    traction_level: c.tractionLevel,
    brake_level: c.brakeLevel,
    emergency_brake: c.emergencyBrake,
    running_phase: c.runningPhase,
  };
}

function mapMaProfile(entry: NonNullable<ApiSimulationSnapshot['signaling']['maProfile']>[0]) {
  return {
    train_id: entry.trainId,
    ma_end_chainage: entry.maEndChainage,
    safety_distance: entry.safetyDistance,
  };
}

function mapSpeedLimit(entry: NonNullable<ApiSimulationSnapshot['signaling']['speedLimits']>[0]) {
  return {
    train_id: entry.trainId,
    permanent_limit: entry.permanentLimit,
    atp_limit: entry.atpLimit,
  };
}

function mapTimetableDeviation(
  entry: NonNullable<ApiSimulationSnapshot['signaling']['timetableDeviation']>[0],
) {
  return {
    train_id: entry.trainId,
    station_id: entry.stationId,
    delay_arrival: entry.delayArrival,
    nominal_dwell: entry.nominalDwell,
    adjusted_dwell: entry.adjustedDwell,
  };
}

function mapTrainInterval(
  entry: NonNullable<ApiSimulationSnapshot['signaling']['trainIntervals']>[0],
) {
  return {
    train_id: entry.trainId,
    leading_train_id: entry.leadingTrainId,
    interval_m: entry.intervalM,
    min_interval_m: entry.minIntervalM,
    safe: entry.safe,
  };
}

export function parseServerSnapshot(raw: ApiSimulationSnapshot): SimulationSnapshot {
  const controlCommands = raw.signaling?.controlCommands ?? [];
  return {
    clock: {
      elapsed: raw.clock.elapsed,
      speed_multiplier: raw.clock.speedMultiplier,
    },
    trains: raw.trains.map(mapTrain),
    power: {
      substations: (raw.power.substations ?? []).map(s => ({
        id: s.id,
        name: s.name,
        chainage: s.chainage,
        rated_voltage: s.ratedVoltage,
        rated_power: s.ratedPower,
        output_current: s.outputCurrent,
        output_power: s.outputPower,
      })),
      voltage_profile: (raw.power.voltageProfile ?? []).map(v => ({
        chainage: v.chainage,
        voltage: v.voltage,
      })),
      total_consumption: raw.power.totalConsumption,
      total_regeneration: raw.power.totalRegeneration,
      regeneration_rate: 0,
    },
    signaling: {
      commands: controlCommands.map(mapControlCommand),
      emergency_brake: [],
      train_intervals: (raw.signaling?.trainIntervals ?? []).map(mapTrainInterval),
      ma_profiles: (raw.signaling?.maProfile ?? []).map(mapMaProfile),
      speed_limits: (raw.signaling?.speedLimits ?? []).map(mapSpeedLimit),
      timetable_deviations: (raw.signaling?.timetableDeviation ?? []).map(mapTimetableDeviation),
    },
    track: {
      occupancy: ((raw.track?.occupancy ?? []) as Record<string, unknown>[]).map(
        (o): TrackCircuit => ({
          id: String(o.circuitId ?? ''),
          start_chainage: Number(o.startChainage ?? 0),
          end_chainage: Number(o.endChainage ?? 0),
          direction: (o.direction as TrackCircuit['direction']) ?? 'down',
          occupied: Boolean(o.occupied),
        }),
      ),
      switch_states: ((raw.track?.switchStates ?? []) as Record<string, unknown>[]).map(
        (s): Switch => ({
          id: String(s.switchId ?? ''),
          chainage: Number(s.chainage ?? 0),
          type: (s.type as Switch['type']) ?? 'single',
          normal_direction: String(s.normalDirection ?? 'main'),
          reverse_direction: String(s.reverseDirection ?? 'siding'),
          lateral_speed_limit: Number(s.lateralSpeedLimit ?? 30),
          state: (s.state as Switch['state']) ?? 'normal',
        }),
      ),
    },
    events: raw.events ?? [],
  };
}

export function toApiParamUpdate(params: Partial<SimulationParams>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  if (params.vehicle) {
    const v: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(params.vehicle)) {
      if (val === undefined) continue;
      if (k === 'traction_curve' && Array.isArray(val)) {
        v.tractionCurve = val.map((p) => ({
          speed: p.speed,
          forcePercent: p.force_percent,
        }));
        continue;
      }
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
      ...(params.track.segment_id !== undefined && { segmentId: params.track.segment_id }),
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
      if (k === 'tractionCurve' && Array.isArray(val)) {
        vehicle.traction_curve = val.map((p, i) => {
          const point = p as Record<string, unknown>;
          return {
            speed: Number(point.speed),
            force_percent: Number(point.forcePercent ?? point.force_percent),
            sort_order: i,
          };
        });
        continue;
      }
      const snakeKey = VEHICLE_KEY_REVERSE[k] ?? k;
      (vehicle as Record<string, unknown>)[snakeKey] = val;
    }
    result.vehicle = vehicle;
  }

  const trackRaw = raw.track as Record<string, unknown> | undefined;
  if (trackRaw) {
    result.track = {
      ...(trackRaw.segmentId !== undefined && { segment_id: String(trackRaw.segmentId) }),
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
