/**
 * SwitchStatus — 道岔状态图
 * 基于《需求文档》UI-TRK-03（迭代四）
 * 道岔定位/反位/转换中状态显示
 */
import { useSimulationState } from '../../../context/SimulationContext';

export default function SwitchStatus() {
  const { track } = useSimulationState();

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

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🔀 道岔状态</div>
      {track.switch_states.length === 0 ? (
        <div style={styles.empty}>暂无道岔数据</div>
      ) : (
        <div style={styles.grid}>
          {track.switch_states.map((sw) => (
            <div key={sw.id} style={styles.item}>
              <div style={styles.header}>
                <span style={styles.id}>{sw.id}</span>
                <span
                  style={{
                    ...styles.badge,
                    backgroundColor: stateColors[sw.state] || '#999',
                  }}
                >
                  {stateLabels[sw.state] || sw.state}
                </span>
              </div>
              <div style={styles.detail}>
                位置: {sw.chainage} m
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
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  id: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
  },
  badge: {
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '10px',
    color: '#fff',
    fontWeight: 600,
  },
  detail: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginTop: '4px',
  },
};
