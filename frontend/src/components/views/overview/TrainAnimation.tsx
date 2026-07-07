/**
 * TrainAnimation — 列车位置实时动画
 * 基于《需求文档》UI-VW-02
 * 列车图标沿线路移动，使用 Canvas 或 CSS 动画
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { getModeColor } from '../../../utils/format';

export default function TrainAnimation() {
  const { trains } = useSimulationState();

  // TODO: 根据实际线路总长计算比例位置
  const totalLength = 3200; // 临时硬编码，后续从配置读取

  return (
    <div className="panel" style={styles.container}>
      <div className="panel-title">🚇 列车位置</div>
      <div style={styles.track}>
        {/* 线路基准线 */}
        <div style={styles.rail} />

        {/* 车站标记 */}
        {[0, 1500, 3200].map((pos, i) => (
          <div
            key={i}
            style={{
              ...styles.stationMark,
              left: `${(pos / totalLength) * 100}%`,
            }}
            title={['A站', 'B站', 'C站'][i]}
          >
            <div style={styles.stationDot} />
            <span style={styles.stationLabel}>{['A', 'B', 'C'][i]}</span>
          </div>
        ))}

        {/* 列车图标 */}
        {trains.map((train) => {
          const posPercent = Math.min((train.position / totalLength) * 100, 100);
          return (
            <div
              key={train.id}
              style={{
                ...styles.trainIcon,
                left: `${posPercent}%`,
                backgroundColor: getModeColor(train.mode),
              }}
              title={`${train.id}: ${train.speed.toFixed(1)} km/h, ${train.position.toFixed(0)} m`}
            >
              🚇
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: '80px',
  },
  track: {
    position: 'relative',
    height: '40px',
    marginTop: '8px',
  },
  rail: {
    position: 'absolute',
    top: '50%',
    left: 0,
    right: 0,
    height: '3px',
    backgroundColor: '#2a2a4a',
    transform: 'translateY(-50%)',
    borderRadius: '2px',
  },
  stationMark: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    zIndex: 1,
  },
  stationDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: '#fff',
    border: '2px solid #1890ff',
  },
  stationLabel: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
    marginTop: '2px',
  },
  trainIcon: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    zIndex: 2,
    transition: 'left 0.1s linear',
    boxShadow: '0 2px 6px rgba(0,0,0,0.4)',
  },
};
