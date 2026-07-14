import { createContext, useContext, type ReactNode } from 'react';

const ChartActiveContext = createContext(true);

/** keep-alive 隐藏页：active=false 时暂停 SimEChart 绘制 */
export function ChartLifecycleProvider({
  active,
  children,
}: {
  active: boolean;
  children: ReactNode;
}) {
  return (
    <ChartActiveContext.Provider value={active}>
      {children}
    </ChartActiveContext.Provider>
  );
}

export function useChartActive(): boolean {
  return useContext(ChartActiveContext);
}
