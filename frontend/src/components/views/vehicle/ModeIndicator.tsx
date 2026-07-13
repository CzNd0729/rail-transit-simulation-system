/**
 * ModeIndicator — 工况指示器
 * 基于《需求文档》UI-VHC-03
 * 当前工况（牵引/惰行/制动）彩色标识
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { useSelectedTrain } from '../../../hooks/useSelectedTrain';
import { getModeLabel, getModeColor, getDisplayMode, VEHICLE_CHART_DECIMALS } from '../../../utils/format';

export default function ModeIndicator() {
  const { signaling } = useSimulationState();
  const train = useSelectedTrain();
  const cmd = signaling.commands.find((c) => c.train_id === train?.id)
    ?? signaling.commands[0];
  const displayMode = getDisplayMode(train?.mode, train?.speed ?? 0, cmd?.running_phase);

  const modes = ['traction', 'coasting', 'braking', 'stopped'] as const;

  return (
    <div className="panel">
      <div className="panel-title">⚙️ 工况指示</div>
      <div style={styles.container}>
        {modes.map((mode) => {
          const isActive = displayMode === mode;
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
              加速度: {train.acceleration.toFixed(VEHICLE_CHART_DECIMALS)} m/s²
            </span>
            <span style={styles.detail}>
              冲击率: {train.jerk.toFixed(VEHICLE_CHART_DECIMALS)} m/s³
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
    borderWidth: '2px',
    borderStyle: 'solid',
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
