/**
 * App.tsx — 应用主入口
 * NULL轨道交通仿真系统前端
 */
import { useEffect, useState, type CSSProperties } from 'react';
import { SimulationProvider, useSimulationState } from './context/SimulationContext';
import { useWebSocket } from './hooks/useWebSocket';
import { useMockReplay } from './hooks/useMockReplay';
import { useBootstrap } from './hooks/useBootstrap';
import { useLineLayout } from './hooks/useLineLayout';
import { useFps } from './hooks/useFps';
import { USE_MOCK } from './utils/constants';
import MainLayout from './layouts/MainLayout';
import ErrorBoundary from './components/common/ErrorBoundary';
import ViewErrorBoundary from './components/common/ViewErrorBoundary';
import {
  ChartSwitchGateProvider,
  useChartSwitchGate,
} from './components/common/ChartSwitchGate';
import type { ViewType } from './types/simulation';

import OverviewView from './pages/OverviewView';
import PowerView from './pages/PowerView';
import SignalView from './pages/SignalView';
import VehicleView from './pages/VehicleView';
import TrackView from './pages/TrackView';
import ScenarioComparePage from './pages/ScenarioComparePage';

import ControlPanel from './components/control/ControlPanel';
import ParamPanel from './components/param/ParamPanel';
import ExportPanel from './components/export/ExportPanel';

/** 车辆/信号含大量 ECharts：访问过后 keep-alive，避免长跑后切换时批量 unload 触发 removeChild */
const KEEP_ALIVE_VIEWS = new Set<ViewType>(['vehicle', 'signal']);

const keptPaneStyle = (visible: boolean): CSSProperties => ({
  display: visible ? 'flex' : 'none',
  flexDirection: 'column',
  height: '100%',
  minHeight: 0,
});

function AppContent() {
  useBootstrap();
  useLineLayout();
  useFps();
  const { activeView } = useSimulationState();
  const { markSettling, endSwitch } = useChartSwitchGate();
  const ws = useWebSocket();
  const mock = useMockReplay();
  const { send } = USE_MOCK ? mock : ws;
  const [visitedKeepAlive, setVisitedKeepAlive] = useState<Set<ViewType>>(() => new Set());

  useEffect(() => {
    if (!KEEP_ALIVE_VIEWS.has(activeView)) return;
    setVisitedKeepAlive((prev) => {
      if (prev.has(activeView)) return prev;
      const next = new Set(prev);
      next.add(activeView);
      return next;
    });
  }, [activeView]);

  useEffect(() => {
    markSettling();
    const timer = window.setTimeout(() => {
      endSwitch();
    }, 80);
    return () => window.clearTimeout(timer);
  }, [activeView, markSettling, endSwitch]);

  const showVehicle = activeView === 'vehicle';
  const showSignal = activeView === 'signal';
  const showOther = !KEEP_ALIVE_VIEWS.has(activeView);
  const mountVehicle = visitedKeepAlive.has('vehicle') || showVehicle;
  const mountSignal = visitedKeepAlive.has('signal') || showSignal;

  const renderOtherView = () => {
    switch (activeView) {
      case 'overview':
        return <OverviewView />;
      case 'power':
        return <PowerView />;
      case 'track':
        return <TrackView />;
      case 'scenario':
        return <ScenarioComparePage />;
      default:
        return <OverviewView />;
    }
  };

  const sidebar = activeView === 'scenario' ? null : (
    <>
      <ControlPanel send={send} />
      <ParamPanel send={send} />
      <ExportPanel />
    </>
  );

  return (
    <MainLayout sidebar={sidebar}>
      {showOther && (
        <ViewErrorBoundary viewKey={activeView}>
          {renderOtherView()}
        </ViewErrorBoundary>
      )}
      {mountVehicle && (
        <div style={keptPaneStyle(showVehicle)} aria-hidden={!showVehicle}>
          <ViewErrorBoundary viewKey="vehicle">
            <VehicleView active={showVehicle} />
          </ViewErrorBoundary>
        </div>
      )}
      {mountSignal && (
        <div style={keptPaneStyle(showSignal)} aria-hidden={!showSignal}>
          <ViewErrorBoundary viewKey="signal">
            <SignalView active={showSignal} />
          </ViewErrorBoundary>
        </div>
      )}
    </MainLayout>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <SimulationProvider>
        <ChartSwitchGateProvider>
          <AppContent />
        </ChartSwitchGateProvider>
      </SimulationProvider>
    </ErrorBoundary>
  );
}
