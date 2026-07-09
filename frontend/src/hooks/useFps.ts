/**
 * useFPS — 实时帧率计算 Hook
 * 通过 requestAnimationFrame 计算每秒帧数，更新到 context
 */
import { useEffect } from 'react';
import { useSimulationDispatch } from '../context/SimulationContext';

export function useFps() {
  const dispatch = useSimulationDispatch();

  useEffect(() => {
    let frames = 0;
    let lastTime = performance.now();
    let raf: number;

    const tick = (now: number) => {
      frames++;
      if (now - lastTime >= 1000) {
        dispatch({ type: 'SET_FPS', payload: frames });
        frames = 0;
        lastTime = now;
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [dispatch]);
}
