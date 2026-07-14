/**
 * SignalView — 信号视图（迭代二单车简化版）
 */
import MAChart from '../components/views/signal/MAChart';
import SpeedEnvelope from '../components/views/signal/SpeedEnvelope';
import TimetableChart from '../components/views/signal/TimetableChart';
import SignalStatusBar from '../components/views/signal/SignalStatusBar';
import { ChartLifecycleProvider } from '../components/common/ChartLifecycleContext';

export default function SignalView({ active = true }: { active?: boolean }) {
  return (
    <ChartLifecycleProvider active={active}>
      <div style={styles.container}>
        <div style={styles.mainRow}>
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
        <SignalStatusBar />
      </div>
    </ChartLifecycleProvider>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
    height: '100%',
    minHeight: 0,
  },
  mainRow: {
    flex: 1,
    display: 'flex',
    flexDirection: 'row',
    gap: '12px',
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
