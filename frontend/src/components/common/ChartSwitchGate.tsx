import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  canPaintCharts,
  nextPhaseAfterBegin,
  nextPhaseAfterEnd,
  nextPhaseAfterSettle,
  type ChartSwitchPhase,
} from './chartSwitchPhase';

interface ChartSwitchGateValue {
  phase: ChartSwitchPhase;
  canPaint: boolean;
  beginSwitch: () => void;
  markSettling: () => void;
  endSwitch: () => void;
}

const ChartSwitchGateContext = createContext<ChartSwitchGateValue | null>(null);

export function ChartSwitchGateProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<ChartSwitchPhase>('idle');

  const beginSwitch = useCallback(() => {
    setPhase((p) => nextPhaseAfterBegin(p));
  }, []);

  const markSettling = useCallback(() => {
    setPhase((p) => nextPhaseAfterSettle(p));
  }, []);

  const endSwitch = useCallback(() => {
    setPhase((p) => nextPhaseAfterEnd(p));
  }, []);

  const value = useMemo(
    (): ChartSwitchGateValue => ({
      phase,
      canPaint: canPaintCharts(phase),
      beginSwitch,
      markSettling,
      endSwitch,
    }),
    [phase, beginSwitch, markSettling, endSwitch],
  );

  return (
    <ChartSwitchGateContext.Provider value={value}>
      {children}
    </ChartSwitchGateContext.Provider>
  );
}

export function useChartSwitchGate(): ChartSwitchGateValue {
  const ctx = useContext(ChartSwitchGateContext);
  if (!ctx) {
    return {
      phase: 'idle',
      canPaint: true,
      beginSwitch: () => undefined,
      markSettling: () => undefined,
      endSwitch: () => undefined,
    };
  }
  return ctx;
}
