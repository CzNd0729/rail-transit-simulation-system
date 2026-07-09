/**
 * ViewportControls — 视口控制栏
 * 缩放滑块 + 跟随锁定按钮 + 全线总览按钮
 * 半透明背景 + 毛玻璃效果
 */
interface ViewportControlsProps {
  zoom: number;
  maxZoom: number;
  followMode: boolean;
  onZoomChange: (z: number) => void;
  onToggleFollow: () => void;
  onFitAll: () => void;
}

export default function ViewportControls({
  zoom,
  maxZoom,
  followMode,
  onZoomChange,
  onToggleFollow,
  onFitAll,
}: ViewportControlsProps) {
  return (
    <div style={styles.container}>
      <button
        style={styles.btn}
        onClick={() => onZoomChange(Math.max(1, zoom - 0.5))}
        title="缩小"
      >
        −
      </button>
      <input
        type="range"
        min={1}
        max={maxZoom}
        step={0.1}
        value={zoom}
        onChange={(e) => onZoomChange(parseFloat(e.target.value))}
        style={styles.slider}
        title={`缩放: ${zoom.toFixed(1)}×`}
      />
      <button
        style={styles.btn}
        onClick={() => onZoomChange(Math.min(maxZoom, zoom + 0.5))}
        title="放大"
      >
        +
      </button>

      <span style={styles.zoomLabel}>{zoom.toFixed(1)}×</span>

      <div style={styles.separator} />

      <button
        style={{
          ...styles.btn,
          backgroundColor: followMode ? 'rgba(24, 144, 255, 0.3)' : 'transparent',
          color: followMode ? '#1890ff' : '#a0a0a0',
        }}
        onClick={onToggleFollow}
        title={followMode ? '取消跟随' : '锁定跟随'}
      >
        {followMode ? '📍' : '📌'}
      </button>

      <button
        style={styles.btn}
        onClick={onFitAll}
        title="全线总览"
      >
        🔍
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
  },
  btn: {
    background: 'none',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: '#e0e0e0',
    cursor: 'pointer',
    padding: '2px 8px',
    fontSize: '14px',
    lineHeight: '1.4',
  },
  slider: {
    width: '80px',
    height: '4px',
    accentColor: '#1890ff',
  },
  zoomLabel: {
    color: '#a0a0a0',
    fontSize: '11px',
    minWidth: '32px',
    textAlign: 'center' as const,
  },
  separator: {
    width: '1px',
    height: '16px',
    backgroundColor: 'var(--border-color)',
    margin: '0 2px',
  },
};
