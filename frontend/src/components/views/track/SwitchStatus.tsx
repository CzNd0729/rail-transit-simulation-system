/**
 * SwitchStatus — 道岔状态图
 * 优先使用 context 数据，空时 fallback 到 mockSwitches
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { mockSwitches } from '../../../data/mockLineData';
import type { Switch } from '../../../types/simulation';

const stateColors: Record<string, string> = {
  normal: '#52c41a',
  reverse: '#faad14',
  transitioning: '#1890ff',
};

const stateLabels: Record<string, string> = {
  normal: '定位',
  reverse: '反位',
  transitioning: '转换中',
};

const stateIcons: Record<string, string> = {
  normal: '→',
  reverse: '↗',
  transitioning: '⟳',
};

const typeLabels: Record<string, string> = {
  single: '单开',
  crossover: '交叉渡线',
};

export default function SwitchStatus() {
  const { track } = useSimulationState();

  // context 有数据则用，否则 fallback 到 mockSwitches
  const switches: Switch[] =
    track.switch_states.length > 0 ? track.switch_states : mockSwitches;

  return (
    <div className="panel" style={{ height: '100%', overflow: 'auto' }}>
      <div className="panel-title">🔀 道岔状态</div>
      <div style={styles.grid}>
        {switches.map((sw) => (
          <div key={sw.id} style={styles.item}>
            <div style={styles.header}>
              <span style={styles.id}>{sw.id}</span>
              <span style={styles.typeTag}>
                {typeLabels[sw.type] || sw.type}
              </span>
              <span
                style={{
                  ...styles.badge,
                  backgroundColor: stateColors[sw.state] || '#999',
                }}
              >
                <span style={{ marginRight: 3 }}>
                  {stateIcons[sw.state] || '?'}
                </span>
                {stateLabels[sw.state] || sw.state}
              </span>
            </div>
            <div style={styles.details}>
              <span>📍 {sw.chainage} m</span>
              <span>🔧 定位: {sw.normal_direction}</span>
              <span>🔁 反位: {sw.reverse_direction}</span>
              <span>⚠️ 侧向限速: {sw.lateral_speed_limit} km/h</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    padding: '8px 0',
  },
  item: {
    padding: '8px 10px',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    backgroundColor: 'var(--bg-dark)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  id: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
  },
  typeTag: {
    fontSize: '9px',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: 'var(--bg-darker)',
    color: 'var(--text-secondary)',
  },
  badge: {
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '10px',
    color: '#fff',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    marginLeft: 'auto',
  },
  details: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '2px 12px',
    marginTop: '6px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
};
