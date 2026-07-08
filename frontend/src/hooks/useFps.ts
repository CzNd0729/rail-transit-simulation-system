import { useEffect } from 'react';
import { useSimulationDispatch } from '../context/SimulationContext';

export function useFps() {
  const dispatch = useSimulationDispatch();

  useEffect(() => {
    let frames = 0;
    let last = performance.now();
    let raf = 0;

    const tick = (now: number) => {
      frames++;
      if (now - last >= 1000) {
        dispatch({ type: 'SET_FPS', payload: frames });
        frames = 0;
        last = now;
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [dispatch]);
}
