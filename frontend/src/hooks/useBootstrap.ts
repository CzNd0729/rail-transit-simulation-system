import { useEffect } from 'react';
import { getParams } from '../services/api';
import { useSimulationDispatch } from '../context/SimulationContext';
import { parseApiParams } from '../utils/apiAdapter';
import { USE_MOCK } from '../utils/constants';

export function useBootstrap() {
  const dispatch = useSimulationDispatch();

  useEffect(() => {
    if (USE_MOCK) return;

    getParams()
      .then((raw) => {
        const params = parseApiParams(raw as unknown as Record<string, unknown>);
        dispatch({ type: 'INIT_PARAMS', payload: params });
      })
      .catch((err) => {
        console.warn('[Bootstrap] 无法加载后端参数，使用默认值', err);
      });
  }, [dispatch]);
}
