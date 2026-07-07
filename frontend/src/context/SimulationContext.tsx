/**
 * 仿真状态管理 — React Context + useReducer
 * 基于《详细设计文档》5.2 状态管理设计
 */
import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from 'react';
import type {
  AppState,
  RunState,
  ViewType,
  SimulationSnapshot,
  SimulationParams,
} from '../types/simulation';

// ==================== 初始状态 ====================

const initialState: AppState = {
  connection: 'disconnected',
  runState: 'idle',
  activeView: 'overview',
  clock: { elapsed: 0, speed_multiplier: 1 },
  trains: [],
  power: {
    substations: [],
    voltage_profile: [],
    total_consumption: 0,
    total_regeneration: 0,
    regeneration_rate: 0,
  },
  signaling: {
    commands: [],
    emergency_brake: [],
    train_intervals: [],
  },
  track: {
    occupancy: [],
    switch_states: [],
  },
  params: {
    vehicle: {},
    track: {},
    power: {},
    signal: {},
  },
  stats: {
    total_distance: 0,
    avg_speed: 0,
    max_speed: 0,
    total_energy_consumption: 0,
    total_regeneration: 0,
    trip_time: 0,
    stop_count: 0,
  },
  events: [],
  fps: 0,
};

// ==================== Action 类型 ====================

export type SimulationAction =
  | { type: 'WS_CONNECTED' }
  | { type: 'WS_DISCONNECTED' }
  | { type: 'WS_CONNECTING' }
  | { type: 'RUNTIME_UPDATE'; payload: SimulationSnapshot }
  | { type: 'SET_VIEW'; payload: ViewType }
  | { type: 'SET_RUN_STATE'; payload: RunState }
  | { type: 'UPDATE_PARAMS'; payload: Partial<SimulationParams> }
  | { type: 'RESET_STATE' }
  | { type: 'SET_FPS'; payload: number };

// ==================== Reducer ====================

function simulationReducer(state: AppState, action: SimulationAction): AppState {
  switch (action.type) {
    case 'WS_CONNECTED':
      return { ...state, connection: 'connected' };

    case 'WS_DISCONNECTED':
      return { ...state, connection: 'disconnected' };

    case 'WS_CONNECTING':
      return { ...state, connection: 'connecting' };

    case 'RUNTIME_UPDATE': {
      const snapshot = action.payload;
      return {
        ...state,
        clock: snapshot.clock,
        trains: snapshot.trains,
        power: snapshot.power,
        signaling: snapshot.signaling,
        track: snapshot.track,
        events: [...state.events, ...snapshot.events].slice(-500), // 保留最近 500 条
      };
    }

    case 'SET_VIEW':
      return { ...state, activeView: action.payload };

    case 'SET_RUN_STATE':
      return { ...state, runState: action.payload };

    case 'UPDATE_PARAMS':
      return {
        ...state,
        params: {
          ...state.params,
          ...action.payload,
        },
      };

    case 'RESET_STATE':
      return { ...initialState };

    case 'SET_FPS':
      return { ...state, fps: action.payload };

    default:
      return state;
  }
}

// ==================== Context ====================

const SimulationStateContext = createContext<AppState>(initialState);
const SimulationDispatchContext = createContext<Dispatch<SimulationAction>>(() => {});

/** 仿真状态 Provider */
export function SimulationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(simulationReducer, initialState);

  return (
    <SimulationStateContext.Provider value={state}>
      <SimulationDispatchContext.Provider value={dispatch}>
        {children}
      </SimulationDispatchContext.Provider>
    </SimulationStateContext.Provider>
  );
}

/** 获取仿真状态 */
export function useSimulationState(): AppState {
  return useContext(SimulationStateContext);
}

/** 获取 dispatch 函数 */
export function useSimulationDispatch(): Dispatch<SimulationAction> {
  return useContext(SimulationDispatchContext);
}
