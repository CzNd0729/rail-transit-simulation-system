import type {
  MaProfileEntry,
  SpeedLimitEntry,
  TimetableDeviationEntry,
  TrainTrackingInterval,
} from '../types/simulation';

export interface MaEnvelope {
  envelopeStart: number;
  envelopeEnd: number;
  safetyDistance: number;
}

export function resolveMaEnvelope(
  position: number,
  totalLength: number,
  maProfile?: MaProfileEntry,
  fallbackLength = 300,
): MaEnvelope {
  const safetyDistance = maProfile?.safety_distance ?? fallbackLength;
  const envelopeEnd = maProfile
    ? Math.min(maProfile.ma_end_chainage, totalLength)
    : Math.min(position + fallbackLength, totalLength);
  return {
    envelopeStart: position,
    envelopeEnd,
    safetyDistance,
  };
}

export function resolveAtpSpeedLimit(
  speedLimits: SpeedLimitEntry[],
  trainId: string,
  fallbackLimit: number,
): number {
  const entry = speedLimits.find((s) => s.train_id === trainId);
  return entry?.atp_limit ?? fallbackLimit;
}

export function resolveLatestDeviation(
  deviations: TimetableDeviationEntry[],
  trainId: string,
): TimetableDeviationEntry | null {
  const matched = deviations.filter((d) => d.train_id === trainId);
  if (matched.length === 0) return null;
  return matched[matched.length - 1];
}

export function resolveTrainInterval(
  intervals: TrainTrackingInterval[],
  trainId: string,
): TrainTrackingInterval | null {
  return intervals.find((iv) => iv.train_id === trainId) ?? null;
}
