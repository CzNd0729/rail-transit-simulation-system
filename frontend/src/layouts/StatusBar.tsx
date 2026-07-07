/**
 * StatusBar — 底部状态栏组件
 * 基于《需求文档》3.5 状态栏设计
 *
 * 功能：
 * - UI-BAR-01: 仿真时间
 * - UI-BAR-02: 帧率 (FPS)
 * - UI-BAR-03: 列车数量
 * - UI-BAR-04: 仿真速度倍率
 */
import { useSimulationState } from '../context/SimulationContext';
import { formatSimTime } from '../utils/format';
import { RUN_STATE_LABELS } from '../utils/constants';

export default function StatusBar() {
  const { clock, trains, fps, runState, connection } = useSimulationState();

  return (
    <footer style={styles.statusbar}>
      <div style={styles.section}>
        <StatusItem label="仿真时间" value={formatSimTime(clock.elapsed)} />
      </div>

      <div style={styles.divider} />

      <div style={styles.section}>
        <StatusItem label="状态" value={RUN_STATE_LABELS[runState] || runState} />
      </div>

      <div style={styles.divider} />

      <div style={styles.section}>
        <StatusItem label="FPS" value={`${fps}`} />
      </div>

      <div style={styles.divider} />

      <div style={styles.section}>
        <StatusItem label="列车数量" value={`${trains.length}`} />
      </div>

      <div style={styles.divider} />

      <div style={styles.section}>
        <StatusItem label="速度倍率" value={`${clock.speed_multiplier}×`} />
      </div>

      <div style={styles.spacer} />

      <div style={styles.section}>
        <StatusItem
          label="连接"
          value={connection === 'connected' ? '已连接' : connection === 'connecting' ? '连接中...' : '未连接'}
          color={
            connection === 'connected'
              ? 'var(--color-success)'
              : connection === 'connecting'
                ? 'var(--color-warning)'
                : 'var(--color-error)'
          }
        />
      </div>
    </footer>
  );
}

/** 状态栏单项 */
function StatusItem({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <span style={styles.item}>
      <span style={styles.label}>{label}:</span>
      <span style={{ ...styles.value, color: color || 'var(--text-highlight)' }}>
        {value}
      </span>
    </span>
  );
}

const styles: Record<string, React.CSSProperties> = {
  statusbar: {
    height: 'var(--statusbar-height)',
    display: 'flex',
    alignItems: 'center',
    padding: '0 16px',
    gap: '8px',
    backgroundColor: 'var(--bg-dark)',
    borderTop: '1px solid var(--border-color)',
    flexShrink: 0,
    fontSize: '12px',
  },
  section: {
    display: 'flex',
    alignItems: 'center',
  },
  divider: {
    width: '1px',
    height: '16px',
    backgroundColor: 'var(--border-color)',
  },
  spacer: {
    flex: 1,
  },
  item: {
    display: 'flex',
    gap: '4px',
  },
  label: {
    color: 'var(--text-secondary)',
  },
  value: {
    fontFamily: 'monospace',
    fontWeight: 500,
  },
};
