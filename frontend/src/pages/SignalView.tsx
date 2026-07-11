/**
 * SignalView — 信号视图（迭代二单车简化版）
 *
 * - UI-SIG-01: 移动授权示意图 — 列车位置 + 固定 300m 安全包络 + 目标站台
 * - UI-SIG-02: 速度包络线 — 区段限速 + 三段式目标速度 + 实际速度
 * - UI-SIG-03: 运行图 — 单列车时间-距离轨迹
 * - UI-SIG-04~06: 留待迭代三/四
 */
import MAChart from '../components/views/signal/MAChart';
import SpeedEnvelope from '../components/views/signal/SpeedEnvelope';
import TimetableChart from '../components/views/signal/TimetableChart';

export default function SignalView() {
  return (
    <div style={styles.container}>
      {/* 左列：MA 与速度包络线同宽 */}
      <div style={styles.leftColumn}>
        <div style={styles.maSection}>
          <div style={styles.panelFill}>
            <MAChart />
          </div>
        </div>
        <div style={styles.envelopeSection}>
          <div style={styles.panelFill}>
            <SpeedEnvelope />
          </div>
        </div>
      </div>

      <div style={styles.rightColumn}>
        <div style={styles.panelFill}>
          <TimetableChart />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'row',
    gap: '12px',
    height: '100%',
    minHeight: 0,
  },
  leftColumn: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    minWidth: 0,
    minHeight: 0,
  },
  rightColumn: {
    flex: 1,
    minWidth: 0,
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
  },
  maSection: {
    flex: '0 0 38%',
    minHeight: 140,
    maxHeight: 220,
    display: 'flex',
    flexDirection: 'column',
  },
  envelopeSection: {
    flex: 1,
    minHeight: 0,
    display: 'flex',
    flexDirection: 'column',
  },
  panelFill: {
    flex: 1,
    minHeight: 0,
    height: '100%',
    width: '100%',
  },
};
