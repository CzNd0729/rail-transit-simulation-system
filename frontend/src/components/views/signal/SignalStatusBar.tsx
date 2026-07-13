/**
 * SignalStatusBar — 信号视图底部状态条
 * 展示运行相位、紧急制动、ATS 时刻偏差、SIG-07 追踪间隔
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { useSelectedTrain } from '../../../hooks/useSelectedTrain';
import { getSignalPhaseLabel, resolveSignalPhase } from '../../../utils/format';
import { resolveLatestDeviation, resolveTrainInterval } from '../../../utils/signalSelectors';

export default function SignalStatusBar() {
  const { signaling } = useSimulationState();
  const train = useSelectedTrain();
  const trainId = train?.id ?? 'TRAIN_01';
  const cmd = signaling.commands.find((c) => c.train_id === trainId)
    ?? signaling.commands[0];
  const phase = resolveSignalPhase(
    cmd?.running_phase,
    train?.mode,
    cmd?.traction_level,
    cmd?.brake_level,
  );
  const deviation = resolveLatestDeviation(signaling.timetable_deviations, trainId);
  const interval = resolveTrainInterval(signaling.train_intervals, trainId);
  const ebActive = cmd?.emergency_brake === true;

  return (
    <div style={styles.bar}>
      <span>相位: <strong>{getSignalPhaseLabel(phase)}</strong></span>
      <span>牵引: {(cmd?.traction_level ?? 0).toFixed(2)}</span>
      <span>制动: {(cmd?.brake_level ?? 0).toFixed(2)}</span>
      <span style={{ color: ebActive ? '#ff4d4f' : '#52c41a' }}>
        {ebActive ? '⚠ 紧急制动' : '● 正常'}
      </span>
      {deviation && (
        <span>
          ATS 偏差: {deviation.delay_arrival >= 0 ? '+' : ''}
          {deviation.delay_arrival.toFixed(1)} s
          {' · '}站停 {deviation.adjusted_dwell.toFixed(0)} s
        </span>
      )}
      {interval && (
        <span style={{ color: interval.safe ? 'var(--text-secondary)' : '#ff4d4f' }}>
          追踪间隔: {interval.interval_m.toFixed(0)} m
          {' / '}≥{interval.min_interval_m.toFixed(0)} m
          {' · '}前车 {interval.leading_train_id}
          {' · '}{interval.safe ? '安全' : '不足'}
        </span>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 16,
    fontSize: 12,
    color: 'var(--text-secondary)',
    padding: '6px 12px',
    borderTop: '1px solid var(--border-color)',
    background: 'var(--panel-bg)',
    flexShrink: 0,
  },
};
