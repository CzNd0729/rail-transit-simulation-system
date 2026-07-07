/**
 * TopBar — 顶部栏组件
 * 基于《需求文档》3.2 顶部栏设计
 *
 * 功能：
 * - UI-TOP-01: 视图切换按钮组（综合/供电/信号/车辆/轨道）
 * - UI-TOP-02: 当前视图高亮
 * - UI-TOP-03: 仿真时钟显示 (HH:MM:SS)
 * - UI-TOP-04: 仿真速度倍率显示
 */
import { useSimulationState, useSimulationDispatch } from '../context/SimulationContext';
import { formatSimTime } from '../utils/format';
import { VIEW_CONFIG } from '../utils/constants';
import type { ViewType } from '../types/simulation';

export default function TopBar() {
  const { activeView, clock, connection } = useSimulationState();
  const dispatch = useSimulationDispatch();

  const handleViewChange = (view: ViewType) => {
    dispatch({ type: 'SET_VIEW', payload: view });
  };

  return (
    <header style={styles.topbar}>
      {/* 左侧：系统标题 */}
      <div style={styles.left}>
        <span style={styles.logo}>🚇</span>
        <span style={styles.title}>城市轨道交通运行仿真系统</span>
      </div>

      {/* 中间：视图切换按钮组 */}
      <nav style={styles.nav}>
        {(Object.entries(VIEW_CONFIG) as [ViewType, { label: string; icon: string }][]).map(
          ([key, config]) => (
            <button
              key={key}
              className={`btn ${activeView === key ? 'btn-primary' : ''}`}
              onClick={() => handleViewChange(key)}
              style={styles.viewBtn}
            >
              <span>{config.icon}</span>
              <span>{config.label}</span>
            </button>
          )
        )}
      </nav>

      {/* 右侧：仿真时钟 + 连接状态 */}
      <div style={styles.right}>
        <span style={styles.clock}>⏱ {formatSimTime(clock.elapsed)}</span>
        <span style={styles.multiplier}>{clock.speed_multiplier}×</span>
        <span
          style={{
            ...styles.connectionDot,
            backgroundColor:
              connection === 'connected'
                ? 'var(--color-success)'
                : connection === 'connecting'
                  ? 'var(--color-warning)'
                  : 'var(--color-error)',
          }}
          title={`连接状态: ${connection}`}
        />
      </div>
    </header>
  );
}

const styles: Record<string, React.CSSProperties> = {
  topbar: {
    height: 'var(--topbar-height)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    backgroundColor: 'var(--bg-dark)',
    borderBottom: '1px solid var(--border-color)',
    flexShrink: 0,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  logo: {
    fontSize: '20px',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
    whiteSpace: 'nowrap' as const,
  },
  nav: {
    display: 'flex',
    gap: '6px',
  },
  viewBtn: {
    fontSize: '12px',
    padding: '4px 10px',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  clock: {
    fontSize: '16px',
    fontFamily: 'monospace',
    color: 'var(--text-highlight)',
    fontWeight: 600,
  },
  multiplier: {
    fontSize: '13px',
    color: 'var(--color-primary)',
    fontWeight: 600,
    padding: '2px 6px',
    borderRadius: '4px',
    backgroundColor: 'rgba(24, 144, 255, 0.1)',
  },
  connectionDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    display: 'inline-block',
  },
};
