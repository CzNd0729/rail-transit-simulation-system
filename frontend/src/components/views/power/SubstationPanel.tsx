/**
 * SubstationPanel — 变电所状态面板
 * 基于《需求文档》UI-PWR-02
 * 各变电所输出电流/功率/能耗
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { formatPower } from '../../../utils/format';

export default function SubstationPanel() {
  const { power } = useSimulationState();

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🏭 变电所状态</div>
      {power.substations.length === 0 ? (
        <div style={styles.empty}>暂无变电所数据</div>
      ) : (
        <div style={styles.grid}>
          {power.substations.map((sub) => (
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
                <span style={styles.label}>额定电压:</span>
                <span style={styles.value}>{sub.rated_voltage} V</span>
              </div>
            </div>
          ))}
        </div>
      )}
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
};
