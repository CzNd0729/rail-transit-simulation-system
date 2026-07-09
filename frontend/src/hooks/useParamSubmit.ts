/**
 * useParamSubmit — 参数提交到后端 REST API
 * 封装 PUT /params 调用，成功后更新本地 context
 */
import { useCallback } from 'react';
import { useSimulationDispatch } from '../context/SimulationContext';
import { updateParams } from '../services/api';
import type { SimulationParams } from '../types/simulation';

export function useParamSubmit() {
  const dispatch = useSimulationDispatch();

  const submitParams = useCallback(async (params: Partial<SimulationParams>) => {
    try {
      const updated = await updateParams(params);
      dispatch({ type: 'UPDATE_PARAMS', payload: updated });
    } catch (err) {
      console.error('参数提交失败:', err);
    }
  }, [dispatch]);

  return { submitParams };
}
