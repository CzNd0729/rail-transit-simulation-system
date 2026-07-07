/**
 * ModeIndicator — 工况指示器
 * 基于《需求文档》UI-VHC-03
 * 当前工况（牵引/惰行/制动）彩色标识
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { getModeLabel, getModeColor } from '../../../utils/format';

export default function ModeIndicator() {
  const { trains } = useSimulationState();
  const train = trains[0];

  const modes = ['traction', 'coasting', 'braking'] as const;

  return (
    <div className="panel">
      <div className="panel-title">⚙️ 工况指示</div>
      <div style={styles.container}>
        {modes.map((mode) => {
          const isActive = train?.mode === mode;
          return (
            <div
              key={mode}
              style={{
                ...styles.mode,
                backgroundColor: isActive ? getModeColor(mode) : 'var(--bg-dark)',
                borderColor: getModeColor(mode),
                opacity: isActive ? 1 : 0.4,
              }}
            >
              <span style={styles.label}>{getModeLabel(mode)}</span>
            </div>
          );
        })}

        {train && (
          <div style={styles.info}>
            <span style={styles.detail}>
              牵引级位: {train.power_demand > 0 ? '✓' : '-'}
            </span>
            <span style={styles.detail}>
              速度: {train.speed.toFixed(1)} km/h
            </span>
            <span style={styles.detail}>
              加速度: {train.acceleration.toFixed(2)} m/s²
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  mode: {
    padding: '8px 16px',
    borderRadius: '6px',
    border: '2px solid',
    transition: 'all 0.3s',
  },
  label: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#fff',
  },
  info: {
    display: 'flex',
    gap: '16px',
    marginLeft: 'auto',
  },
  detail: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
};
