/**
 * CollapsiblePanel — 可折叠面板组件
 * 点击三角切换展开/折叠，内容区 max-height 过渡动画
 */
import { useState } from 'react';

interface CollapsiblePanelProps {
  title: string;
  icon?: string;
  defaultOpen?: boolean;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}

export default function CollapsiblePanel({
  title,
  icon,
  defaultOpen = true,
  headerRight,
  children,
}: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button
          style={styles.toggle}
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Collapse' : 'Expand'}
        >
          <span
            style={{
              ...styles.arrow,
              transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)',
            }}
          >
            ▶
          </span>
          {icon && <span style={styles.icon}>{icon}</span>}
          <span style={styles.title}>{title}</span>
        </button>
        {headerRight && <div style={styles.headerRight}>{headerRight}</div>}
      </div>
      <div
        style={{
          ...styles.content,
          maxHeight: isOpen ? '2000px' : '0px',
        }}
      >
        {children}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--border-radius)',
    background: 'var(--bg-dark)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 12px',
    background: 'var(--bg-panel)',
    borderBottom: '1px solid var(--border-color)',
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: 'none',
    border: 'none',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    padding: 0,
    fontSize: '14px',
  },
  arrow: {
    display: 'inline-block',
    transition: 'transform 0.2s ease',
    fontSize: '10px',
  },
  icon: {
    fontSize: '16px',
  },
  title: {
    fontWeight: 500,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  content: {
    overflow: 'hidden',
    transition: 'max-height 0.2s ease-in-out',
  },
};
