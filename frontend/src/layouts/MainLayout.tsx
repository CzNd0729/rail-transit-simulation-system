/**
 * MainLayout — 整体布局组件
 * 基于《需求文档》3.1 界面布局设计
 *
 * 布局结构：
 * ┌──────────────────────────────────────┐
 * │            TopBar (顶部栏)           │
 * ├────────────────────┬─────────────────┤
 * │                    │  Right Sidebar  │
 * │    Main View       │  (控制面板)     │
 * │    (主视图区域)     │                │
 * │                    │                │
 * ├────────────────────┴─────────────────┤
 * │          StatusBar (状态栏)          │
 * └──────────────────────────────────────┘
 */
import type { ReactNode } from 'react';
import TopBar from './TopBar';
import StatusBar from './StatusBar';

interface MainLayoutProps {
  children: ReactNode;          // 主视图区域内容
  sidebar: ReactNode | null;    // 右侧控制面板（null 时全屏显示主视图）
}

export default function MainLayout({ children, sidebar }: MainLayoutProps) {
  return (
    <div style={styles.container}>
      {/* 顶部栏 */}
      <TopBar />

      {/* 中间区域：主视图 + 右侧面板 */}
      <div style={styles.content}>
        <div style={styles.mainView}>
          {children}
        </div>
        {sidebar && (
          <aside style={styles.sidebar}>
            {sidebar}
          </aside>
        )}
      </div>

      {/* 底部状态栏 */}
      <StatusBar />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    width: '100vw',
    overflow: 'hidden',
  },
  content: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  mainView: {
    flex: 1,
    overflow: 'auto',
    padding: '12px',
    backgroundColor: 'var(--bg-main)',
  },
  sidebar: {
    width: 'var(--sidebar-width)',
    minWidth: '280px',
    overflow: 'auto',
    padding: '12px',
    backgroundColor: 'var(--bg-panel)',
    borderLeft: '1px solid var(--border-color)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
};
