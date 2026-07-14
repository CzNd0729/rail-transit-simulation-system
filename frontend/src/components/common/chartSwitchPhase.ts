export type ChartSwitchPhase = 'idle' | 'switching' | 'settling';

export function canPaintCharts(phase: ChartSwitchPhase): boolean {
  return phase === 'idle' || phase === 'settling';
}

export function nextPhaseAfterBegin(_phase: ChartSwitchPhase): ChartSwitchPhase {
  return 'switching';
}

export function nextPhaseAfterSettle(_phase: ChartSwitchPhase): ChartSwitchPhase {
  return 'settling';
}

export function nextPhaseAfterEnd(_phase: ChartSwitchPhase): ChartSwitchPhase {
  return 'idle';
}
