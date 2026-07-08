/**
 * App.tsx — 应用主入口
 * NULL轨道交通仿真系统前端
 *
 * 架构：
 * - SimulationProvider: 全局状态管理 (Context + useReducer)
 * - MainLayout: 整体布局 (TopBar + MainView + Sidebar + StatusBar)
 * - 根据 activeView 切换五个视图页面
 */
import { SimulationProvider, useSimulationState } from './context/SimulationContext';
import { useWebSocket } from './hooks/useWebSocket';
import { useMockReplay } from './hooks/useMockReplay';
import { useBootstrap } from './hooks/useBootstrap';
import { useLineLayout } from './hooks/useLineLayout';
import { useFps } from './hooks/useFps';
import { USE_MOCK } from './utils/constants';
import MainLayout from './layouts/MainLayout';
import ErrorBoundary from './components/common/ErrorBoundary';

// 视图页面
import OverviewView from './pages/OverviewView';
import PowerView from './pages/PowerView';
import SignalView from './pages/SignalView';
import VehicleView from './pages/VehicleView';
import TrackView from './pages/TrackView';

// 侧边栏面板
import ControlPanel from './components/control/ControlPanel';
import ParamPanel from './components/param/ParamPanel';
import ExportPanel from './components/export/ExportPanel';

/** 内部应用组件（需要使用 hooks） */
function AppContent() {
  useBootstrap();
  useLineLayout();
  useFps();
  const { activeView } = useSimulationState();
  const ws = useWebSocket();
  const mock = useMockReplay();
  const { send } = USE_MOCK ? mock : ws;

  // 根据当前视图渲染对应页面
  const renderView = () => {
    switch (activeView) {
      case 'overview':
        return <OverviewView />;
      case 'power':
        return <PowerView />;
      case 'signal':
        return <SignalView />;
      case 'vehicle':
        return <VehicleView />;
      case 'track':
        return <TrackView />;
      default:
        return <OverviewView />;
    }
  };

  // 右侧边栏内容
  const sidebar = (
    <>
      <ControlPanel send={send} />
      <ParamPanel send={send} />
      <ExportPanel />
    </>
  );

  return (
    <MainLayout sidebar={sidebar}>
      {renderView()}
    </MainLayout>
  );
}

/** 应用根组件 */
export default function App() {
  return (
    <ErrorBoundary>
      <SimulationProvider>
        <AppContent />
      </SimulationProvider>
    </ErrorBoundary>
  );
}
