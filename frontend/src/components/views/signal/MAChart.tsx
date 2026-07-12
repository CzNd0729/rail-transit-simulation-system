/**
 * MAChart — 移动授权（MA）示意图
 * 基于《迭代二需求文档》UI-SIG-01（单列车简化版）
 */
import { useMemo } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import { MA_ENVELOPE_LENGTH } from '../../../utils/constants';
import { getSignalPhaseLabel, resolveSignalPhase } from '../../../utils/format';
import { resolveMaEnvelope } from '../../../utils/signalSelectors';

function pct(chainage: number, totalLength: number): string {
  if (totalLength <= 0) return '0%';
  return `${Math.min(100, Math.max(0, (chainage / totalLength) * 100))}%`;
}

export default function MAChart() {
  const { trains, signaling, lineLayout } = useSimulationState();
  const train = trains[0];
  const stations = lineLayout?.stations ?? mockLineData.stations;
  const totalLength = lineLayout?.total_length ?? mockLineData.total_length;

  const position = train?.position ?? 0;
  const maEntry = signaling.ma_profiles.find((m) => m.train_id === train?.id)
    ?? signaling.ma_profiles[0];
  const { envelopeEnd, safetyDistance } = resolveMaEnvelope(
    position,
    totalLength,
    maEntry,
    MA_ENVELOPE_LENGTH,
  );
  const envelopeWidth = Math.max(envelopeEnd - position, 0);
  const cmd = signaling.commands[0];

  const targetStation = useMemo(() => {
    if (!train) return stations[stations.length - 1] ?? null;
    if (train.target_station_id) {
      return stations.find((s) => s.id === train.target_station_id) ?? null;
    }
    if (train.distance_to_station > 0) {
      const chainage = position + train.distance_to_station;
      return stations.find((s) => Math.abs(s.chainage - chainage) < 1) ?? null;
    }
    const ahead = stations.find((s) => s.chainage > position + 1);
    return ahead ?? stations[stations.length - 1] ?? null;
  }, [train, stations, position]);

  const phase = resolveSignalPhase(
    cmd?.running_phase,
    train?.mode,
    cmd?.traction_level,
    cmd?.brake_level,
  );
  const phaseLabel = getSignalPhaseLabel(phase);

  const startStation = stations[0];
  const targetChainage = targetStation?.chainage ?? totalLength;

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">🛡️ 移动授权 (MA)</div>

      <div style={styles.schematic}>
        <div style={styles.trackBar}>
          <div
            style={{
              ...styles.envelope,
              left: pct(position, totalLength),
              width: pct(envelopeWidth, totalLength),
            }}
          />

          {stations.map((st) => (
            <div
              key={st.id}
              style={{
                ...styles.stationTick,
                left: pct(st.chainage, totalLength),
                borderColor: st.id === targetStation?.id ? '#52c41a' : '#3a3a5a',
              }}
              title={st.name}
            />
          ))}

          <div style={{ ...styles.trainMarker, left: pct(position, totalLength) }}>
            <span style={styles.trainIcon}>▶</span>
            <span style={styles.trainLabel}>列车</span>
          </div>
        </div>

        <div style={styles.labelRow}>
          <span style={styles.stationLabel}>{startStation?.name ?? '起点'}</span>
          <span style={{ flex: 1, textAlign: 'center', color: '#1890ff', fontSize: 11 }}>
            安全包络 {safetyDistance.toFixed(0)} m
          </span>
          <span style={{ ...styles.stationLabel, color: '#52c41a' }}>
            {targetStation?.name ?? '终点'}
          </span>
        </div>

        <div style={styles.directionRow}>
          <span style={styles.directionArrow}>→</span>
          <span style={styles.directionText}>
            {position.toFixed(0)} m → {targetChainage.toFixed(0)} m
          </span>
        </div>
      </div>

      <div style={styles.footer}>
        相位: {phaseLabel}
        {' · '}
        距目标站: {train ? `${train.distance_to_station.toFixed(0)} m` : '--'}
        {' · '}
        安全包络: {safetyDistance.toFixed(0)} m
        {maEntry ? ' · 后端 MA' : ' · 固定包络'}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  schematic: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    gap: 12,
    padding: '8px 12px',
    minHeight: 0,
  },
  trackBar: {
    position: 'relative',
    height: 36,
    background: '#1a2a3a',
    borderRadius: 6,
    border: '1px solid #2a4a6a',
  },
  envelope: {
    position: 'absolute',
    top: 4,
    bottom: 4,
    background: 'rgba(24, 144, 255, 0.28)',
    border: '1px dashed #1890ff',
    borderRadius: 4,
    pointerEvents: 'none',
  },
  stationTick: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: 2,
    marginLeft: -1,
    borderLeft: '2px solid',
    pointerEvents: 'none',
  },
  trainMarker: {
    position: 'absolute',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
    zIndex: 2,
  },
  trainIcon: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 28,
    height: 20,
    background: '#1890ff',
    border: '2px solid #69c0ff',
    borderRadius: 4,
    color: '#fff',
    fontSize: 10,
    lineHeight: 1,
  },
  trainLabel: {
    fontSize: 10,
    color: '#a0d8ff',
    whiteSpace: 'nowrap',
  },
  labelRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  stationLabel: {
    fontSize: 12,
    color: '#a0a0a0',
    fontWeight: 600,
  },
  directionRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    color: '#666',
    fontSize: 11,
  },
  directionArrow: {
    fontSize: 18,
    color: '#1890ff',
  },
  directionText: {
    fontFamily: 'monospace',
  },
  footer: {
    fontSize: 12,
    color: 'var(--text-secondary)',
    padding: '4px 8px',
    borderTop: '1px solid var(--border-color)',
  },
};
