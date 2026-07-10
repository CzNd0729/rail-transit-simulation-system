/**
 * SubstationPanel — 变电所状态面板
 * 基于《需求文档》UI-PWR-02
 * 各变电所输出电流/功率/能耗
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { formatPower } from '../../../utils/format';

export default function SubstationPanel() {
  const { power } = useSimulationState();

  const powerData = power;

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🏭 变电所状态</div>
      {powerData.substations.length === 0 ? (
        <div style={styles.empty}>暂无变电所数据</div>
      ) : (
        <div style={styles.grid}>
          {powerData.substations.map((sub) => (
            <div key={sub.id} style={styles.card}>
              <div style={styles.name}>{sub.name}</div>
              <div style={styles.row}>
                <span style={styles.label}>位置:</span>
                <span style={styles.value}>{sub.chainage} m</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>输出电流:</span>
                <span style={styles.value}>{sub.output_current.toFixed(1)} A</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>输出功率:</span>
                <span style={styles.value}>{formatPower(sub.output_power)}</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>额定容量:</span>
                <span style={styles.value}>{formatPower(sub.rated_power)}</span>
              </div>
              <div style={styles.row}>
                <span style={styles.label}>负载率:</span>
                <span style={styles.value}>
                  {((sub.output_power / sub.rated_power) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      {/* 能耗统计 */}
      <div style={styles.statsSection}>
        <div style={styles.statsTitle}>📊 能耗统计</div>
        <div style={styles.statsRow}>
          <span style={styles.label}>总牵引能耗:</span>
          <span style={styles.value}>{powerData.total_consumption.toFixed(2)} kWh</span>
        </div>
        <div style={styles.statsRow}>
          <span style={styles.label}>总再生电量:</span>
          <span style={styles.value}>{powerData.total_regeneration.toFixed(2)} kWh</span>
        </div>
        <div style={styles.statsRow}>
          <span style={styles.label}>再生利用率:</span>
          <span style={styles.value}>{(powerData.regeneration_rate * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  empty: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    padding: '20px',
    fontSize: '13px',
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  card: {
    padding: '10px',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    backgroundColor: 'var(--bg-dark)',
  },
  name: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
    marginBottom: '6px',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '2px 0',
    fontSize: '12px',
  },
  label: {
    color: 'var(--text-secondary)',
  },
  value: {
    color: 'var(--text-primary)',
    fontFamily: 'monospace',
  },
  statsSection: {
    marginTop: '12px',
    padding: '10px',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    backgroundColor: 'var(--bg-dark)',
  },
  statsTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
    marginBottom: '8px',
  },
  statsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
    fontSize: '12px',
  },
};
