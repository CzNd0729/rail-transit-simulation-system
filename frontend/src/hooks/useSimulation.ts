/**
 * 仿真控制 Hook
 * 封装仿真控制指令发送和参数更新逻辑
 */
import { useCallback } from 'react';
import { useSimulationDispatch } from '../context/SimulationContext';
import type { SimulationParams, ViewType } from '../types/simulation';

interface UseSimulationReturn {
  /** 启动仿真 */
  startSimulation: () => void;
  /** 暂停仿真 */
  pauseSimulation: () => void;
  /** 继续仿真 */
  resumeSimulation: () => void;
  /** 停止仿真 */
  stopSimulation: () => void;
  /** 单步执行 */
  stepSimulation: () => void;
  /** 切换视图 */
  setView: (view: ViewType) => void;
  /** 更新参数 */
  updateParams: (params: Partial<SimulationParams>) => void;
  /** 发送 WebSocket 消息 */
  send: (data: object) => void;
}

/**
 * 仿真控制 Hook
 * @param send WebSocket 发送函数
 */
export function useSimulation(send: (data: object) => void): UseSimulationReturn {
  const dispatch = useSimulationDispatch();

  const startSimulation = useCallback(() => {
    dispatch({ type: 'CLEAR_CHART_HISTORY' });
    send({ type: 'sim_control', action: 'start' });
    dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
  }, [send, dispatch]);

  const pauseSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'pause' });
    dispatch({ type: 'SET_RUN_STATE', payload: 'paused' });
  }, [send, dispatch]);

  const resumeSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'resume' });
    dispatch({ type: 'SET_RUN_STATE', payload: 'running' });
  }, [send, dispatch]);

  const stopSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'stop' });
    dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
    dispatch({ type: 'CLEAR_CHART_HISTORY' });
  }, [send, dispatch]);

  const stepSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'step' });
  }, [send]);

  const setView = useCallback((view: ViewType) => {
    dispatch({ type: 'SET_VIEW', payload: view });
  }, [dispatch]);

  const updateParams = useCallback((params: Partial<SimulationParams>) => {
    dispatch({ type: 'UPDATE_PARAMS', payload: params });
    send({ type: 'param_update', params });
  }, [dispatch, send]);

  return {
    startSimulation,
    pauseSimulation,
    resumeSimulation,
    stopSimulation,
    stepSimulation,
    setView,
    updateParams,
    send,
  };
}
