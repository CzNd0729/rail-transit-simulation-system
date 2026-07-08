import type { MockReplayScenario, SimulationSnapshot, SpeedMultiplier } from '../types/simulation';
import { frameToSnapshot } from '../utils/frameToSnapshot';

export interface MockReplayerCallbacks {
  onTick: (snapshot: SimulationSnapshot) => void;
  onComplete: () => void;
}

export interface MockReplayer {
  start: () => void;
  pause: () => void;
  resume: () => void;
  stop: () => void;
  step: () => void;
  setSpeedMultiplier: (m: SpeedMultiplier) => void;
  loadScenario: (scenario: MockReplayScenario) => void;
  getFrameIndex: () => number;
  getTotalFrames: () => number;
}

const EMPTY_SCENARIO: MockReplayScenario = {
  meta: { name: 'empty', description: '', timeStep: 0.1, totalDuration: 0 },
  vehicleParams: {} as MockReplayScenario['vehicleParams'],
  frames: [],
};

export function createMockReplayer(
  initial: MockReplayScenario = EMPTY_SCENARIO,
  callbacks: MockReplayerCallbacks,
): MockReplayer {
  let scenario = initial;
  let frameIndex = 0;
  let speedMultiplier: SpeedMultiplier = 1;
  let timer: ReturnType<typeof setInterval> | null = null;
  let running = false;

  const getIntervalMs = () => scenario.meta.timeStep * 1000 / speedMultiplier;

  const emitFrame = () => {
    if (frameIndex >= scenario.frames.length) {
      pause();
      callbacks.onComplete();
      return;
    }
    const frame = scenario.frames[frameIndex];
    callbacks.onTick(frameToSnapshot(frame, speedMultiplier));
    frameIndex++;
    if (frameIndex >= scenario.frames.length) {
      pause();
      callbacks.onComplete();
    }
  };

  const pause = () => {
    running = false;
    if (timer) { clearInterval(timer); timer = null; }
  };

  const start = () => {
    if (scenario.frames.length === 0) return;
    if (frameIndex >= scenario.frames.length) frameIndex = 0;
    running = true;
    timer = setInterval(emitFrame, getIntervalMs());
  };

  const resume = () => {
    if (!running && frameIndex < scenario.frames.length) start();
  };

  const stop = () => {
    pause();
    frameIndex = 0;
  };

  const step = () => {
    pause();
    emitFrame();
  };

  const setSpeedMultiplier = (m: SpeedMultiplier) => {
    speedMultiplier = m;
    if (running) { pause(); start(); }
  };

  const loadScenario = (next: MockReplayScenario) => {
    pause();
    scenario = next;
    frameIndex = 0;
  };

  return {
    start, pause, resume, stop, step,
    setSpeedMultiplier, loadScenario,
    getFrameIndex: () => frameIndex,
    getTotalFrames: () => scenario.frames.length,
  };
}
