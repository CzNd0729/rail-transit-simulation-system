/**
 * StationInfoCard — 车站信息浮动卡片
 * 悬停或点击车站时显示的详细信息面板 (HTML 浮层)
 */
import type { StationLayout } from '../../../types/simulation';
import { formatSimTime } from '../../../utils/format';

interface StationInfoCardProps {
  station: StationLayout;
  /** 卡片定位 (屏幕像素, 由父组件计算) */
  position: { x: number; y: number };
  /** 关闭卡片 */
  onClose: () => void;
}

export default function StationInfoCard({ station, position, onClose }: StationInfoCardProps) {
  const trackSummary = station.tracks
    .map(t => `${t.name}:${t.occupied ? '占用' : '空闲'}`)
    .join('  ');

  return (
    <div
      style={{
        ...styles.card,
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* 头部 */}
      <div style={styles.header}>
        <span style={styles.title}>🏢 {station.name}</span>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {/* 基本信息 */}
      <div style={styles.row}>
        <span style={styles.label}>公里标:</span>
        <span>K{(station.chainage / 1000).toFixed(3).replace('.', '+')}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>站长:</span>
        <span>{station.length}m</span>
        <span style={{ marginLeft: 12 }}>{station.tracks.length}条股道</span>
      </div>

      {/* 时间信息 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>到达:</span>
        <span>{station.arrival_time != null ? formatSimTime(station.arrival_time) : '--:--:--'}</span>
        <span style={{ marginLeft: 12, color: '#a0a0a0' }}>出发:</span>
        <span>{station.departure_time != null ? formatSimTime(station.departure_time) : '--:--:--'}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>停站:</span>
        <span>{station.dwell_time_actual != null ? `${station.dwell_time_actual.toFixed(0)}s` : '--'}</span>
      </div>

      {/* 占用信息 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>站台占用:</span>
        <div style={styles.barContainer}>
          <div
            style={{
              ...styles.barFill,
              width: `${station.occupancy_rate * 100}%`,
            }}
          />
        </div>
        <span style={{ marginLeft: 8 }}>{(station.occupancy_rate * 100).toFixed(0)}%</span>
      </div>
      <div style={styles.trackStatus}>
        {trackSummary}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    position: 'absolute',
    zIndex: 100,
    backgroundColor: 'var(--bg-dark)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '12px',
    minWidth: '240px',
    fontSize: '12px',
    color: '#e0e0e0',
    boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
    pointerEvents: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  title: {
    fontWeight: 600,
    fontSize: '14px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#808080',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '0 4px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '4px',
  },
  label: {
    color: '#808080',
    marginRight: '8px',
    minWidth: '60px',
  },
  divider: {
    height: '1px',
    backgroundColor: 'var(--border-color)',
    margin: '8px 0',
  },
  barContainer: {
    flex: 1,
    height: '6px',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: '#1890ff',
    borderRadius: '3px',
    transition: 'width 0.3s',
  },
  trackStatus: {
    fontSize: '11px',
    color: '#a0a0a0',
    marginTop: '4px',
    lineHeight: '1.6',
  },
};
