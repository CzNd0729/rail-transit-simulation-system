import { useSimulationState } from '../../context/SimulationContext';
import { formatEnergy, formatSimTime } from '../../utils/format';

export default function RunSummaryPanel() {
  const { runState, stats } = useSimulationState();
  const visible = runState === 'stopped' && stats.trip_time > 0;

  if (!visible) return null;

  return (
    <div
      className="panel"
      style={styles.panel}
    >
      <div className="panel-title">📊 运行摘要</div>
      <div style={styles.row}>
        <span style={styles.label}>总时长</span>
        <span style={styles.value}>{formatSimTime(stats.trip_time)}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>平均速度</span>
        <span style={styles.value}>{stats.avg_speed.toFixed(1)} km/h</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>最高速度</span>
        <span style={styles.value}>{stats.max_speed.toFixed(1)} km/h</span>
      </div>
      <div
        style={{
          ...styles.row,
          visibility: stats.total_energy_consumption > 0 ? 'visible' : 'hidden',
        }}
      >
        <span style={styles.label}>牵引能耗</span>
        <span style={styles.value}>
          {stats.total_energy_consumption > 0
            ? formatEnergy(stats.total_energy_consumption)
            : '--'}
        </span>
      </div>
      <div
        style={{
          ...styles.row,
          visibility: stats.total_regeneration > 0 ? 'visible' : 'hidden',
        }}
      >
        <span style={styles.label}>再生电量</span>
        <span style={styles.value}>
          {stats.total_regeneration > 0
            ? formatEnergy(stats.total_regeneration)
            : '--'}
        </span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    marginBottom: '8px',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '12px',
    padding: '4px 0',
  },
  label: {
    color: 'var(--text-secondary)',
  },
  value: {
    fontFamily: 'monospace',
    fontWeight: 500,
    color: 'var(--text-highlight)',
  },
};
