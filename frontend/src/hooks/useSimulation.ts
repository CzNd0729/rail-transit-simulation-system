/**
 * 仿真控制 Hook
 * 封装仿真控制指令发送和参数更新逻辑
 * 注意：不乐观更新 runState——按钮状态完全依赖服务端推送的 simulation_status
 */
import { useCallback } from 'react';
import { useSimulationDispatch, useSimulationState } from '../context/SimulationContext';
import { toApiParamUpdate } from '../utils/apiAdapter';
import { USE_MOCK } from '../utils/constants';
import { updateParams as apiUpdateParams } from '../services/api';
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
  const { runState } = useSimulationState();

  const startSimulation = useCallback(() => {
    dispatch({ type: 'RESET_RUN_DATA' });
    send({ type: 'sim_control', action: 'start' });
  }, [send, dispatch]);

  const pauseSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'pause' });
  }, [send]);

  const resumeSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'resume' });
  }, [send]);

  const stopSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'stop' });
  }, [send]);

  const stepSimulation = useCallback(() => {
    send({ type: 'sim_control', action: 'step' });
  }, [send]);

  const setView = useCallback((view: ViewType) => {
    dispatch({ type: 'SET_VIEW', payload: view });
  }, [dispatch]);

  const updateParams = useCallback(async (params: Partial<SimulationParams>) => {
    if (runState === 'running') return;
    dispatch({ type: 'UPDATE_PARAMS', payload: params });
    if (USE_MOCK) {
      send({ type: 'param_update', params });
    } else {
      // 真实后端：通过 REST API 提交参数
      try {
        await apiUpdateParams(toApiParamUpdate(params));
      } catch (err) {
        console.error('参数提交失败:', err);
      }
    }
  }, [dispatch, send, runState]);

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