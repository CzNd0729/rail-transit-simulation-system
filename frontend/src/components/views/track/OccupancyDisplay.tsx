/**
 * OccupancyDisplay — 区段占用状态显示
 * 基于《需求文档》UI-TRK-02（迭代三）
 * 轨道区段占用/空闲可视化
 */
import { useSimulationState } from '../../../context/SimulationContext';

export default function OccupancyDisplay() {
  const { track } = useSimulationState();

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🔲 区段占用状态</div>
      {track.occupancy.length === 0 ? (
        <div style={styles.empty}>暂无区段占用数据</div>
      ) : (
        <div style={styles.grid}>
          {track.occupancy.map((circuit) => (
            <div
              key={circuit.id}
              style={{
                ...styles.section,
                backgroundColor: circuit.occupied ? 'var(--color-error)' : 'var(--bg-dark)',
                borderColor: circuit.occupied ? 'var(--color-error)' : 'var(--border-color)',
              }}
            >
              <span style={styles.id}>{circuit.id}</span>
              <span style={styles.status}>
                {circuit.occupied ? '占用' : '空闲'}
              </span>
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
    flexWrap: 'wrap',
    gap: '6px',
    padding: '8px 0',
  },
  section: {
    padding: '6px 10px',
    borderRadius: '4px',
    border: '1px solid',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    minWidth: '60px',
    transition: 'all 0.2s',
  },
  id: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
  },
  status: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#fff',
  },
};
