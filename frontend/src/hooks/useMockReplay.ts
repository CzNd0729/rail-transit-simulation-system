import { useEffect, useRef, useCallback } from 'react';
import { useSimulationDispatch, useSimulationState } from '../context/SimulationContext';
import { createMockReplayer, type MockReplayer } from '../services/mockReplayer';
import { generateMockTrajectory } from '../mock/generateMockTrajectory';
import { DEFAULT_VEHICLE_PARAMS } from '../data/mockVehicleParams';
import type { MockReplayScenario, MockSimInput, SimulationParams, SpeedMultiplier } from '../types/simulation';

function buildScenarioFromParams(params: SimulationParams): MockReplayScenario {
  const input: MockSimInput = {
    vehicle: { ...DEFAULT_VEHICLE_PARAMS, ...params.vehicle },
    track: {
      gradient: params.track.gradient ?? 30,
      curvature: params.track.curvature ?? 1200,
      speed_limit: params.track.speed_limit ?? 80,
    },
    signal: {
      dwell_time: params.signal.dwell_time ?? 30,
      target_speed_ratio: params.signal.target_speed_ratio ?? 0.8,
    },
    passenger_load_ratio: 0.6,
  };
  const frames = generateMockTrajectory(input);
  return {
    meta: {
      name: 'generated',
      description: '参数驱动生成',
      timeStep: 0.1,
      totalDuration: frames.at(-1)?.t ?? 0,
    },
    vehicleParams: input.vehicle,
    frames,
  };
}

export function useMockReplay() {
  const dispatch = useSimulationDispatch();
  const { params } = useSimulationState();
  const paramsRef = useRef(params);
  paramsRef.current = params;
  const replayerRef = useRef<MockReplayer | null>(null);

  useEffect(() => {
    dispatch({ type: 'WS_CONNECTED' });

    replayerRef.current = createMockReplayer(undefined, {
      onTick: (snapshot) => {
        dispatch({ type: 'RUNTIME_UPDATE', payload: snapshot });
      },
      onComplete: () => {
        dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
      },
    });

    return () => {
      replayerRef.current?.stop();
      dispatch({ type: 'WS_DISCONNECTED' });
    };
  }, [dispatch]);

  const send = useCallback((data: object) => {
    const replayer = replayerRef.current;
    if (!replayer) return;
    const msg = data as Record<string, unknown>;

    if (msg.type === 'sim_control') {
      const action = msg.action as string;
      switch (action) {
        case 'start':
          dispatch({ type: 'CLEAR_CHART_HISTORY' });
          replayer.loadScenario(buildScenarioFromParams(paramsRef.current));
          dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
          replayer.start();
          break;
        case 'pause':
          replayer.pause();
          dispatch({ type: 'SET_RUN_STATE', payload: 'paused' });
          break;
        case 'resume':
          replayer.resume();
          dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
          break;
        case 'stop':
          replayer.stop();
          dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
          break;
        case 'step':
          replayer.step();
          break;
      }
    }

    if (msg.type === 'speed_multiplier') {
      replayer.setSpeedMultiplier(msg.value as SpeedMultiplier);
    }

    if (msg.type === 'param_update') {
      dispatch({ type: 'UPDATE_PARAMS', payload: msg.params as Partial<SimulationParams> });
    }
  }, [dispatch]);

  return { send };
}
