/**
 * MAChart — 移动授权（MA）示意图
 * 基于《迭代二需求文档》UI-SIG-01（单列车简化版）
 */
import { useMemo } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import { MA_ENVELOPE_LENGTH } from '../../../utils/constants';
import { getSignalPhaseLabel, resolveSignalPhase } from '../../../utils/format';

export default function MAChart() {
  const { trains, signaling, lineLayout } = useSimulationState();
  const train = trains[0];
  const stations = lineLayout?.stations ?? mockLineData.stations;
  const totalLength = lineLayout?.total_length ?? mockLineData.total_length;

  const position = train?.position ?? 0;
  const envelopeEnd = Math.min(position + MA_ENVELOPE_LENGTH, totalLength);
  const cmd = signaling.commands[0];

  const targetChainage = useMemo(() => {
    if (!train) return totalLength;
    if (train.target_station_id) {
      const st = stations.find((s) => s.id === train.target_station_id);
      if (st) return st.chainage;
    }
    if (train.distance_to_station > 0) {
      return position + train.distance_to_station;
    }
    return totalLength;
  }, [train, stations, position, totalLength]);

  const phase = resolveSignalPhase(
    cmd?.running_phase,
    train?.mode,
    cmd?.traction_level,
    cmd?.brake_level,
  );
  const phaseLabel = getSignalPhaseLabel(phase);

  const trackY = 50;
  const trackH = 12;

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">🛡️ 移动授权 (MA)</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <svg
          viewBox={`0 0 ${totalLength} 100`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: 'calc(100% - 8px)' }}
        >
          <rect
            x={0}
            y={trackY}
            width={totalLength}
            height={trackH}
            fill="#1a2a3a"
            stroke="#2a4a6a"
            strokeWidth={1}
          />

          <rect
            x={position}
            y={trackY - 4}
            width={Math.max(envelopeEnd - position, 0)}
            height={trackH + 8}
            fill="rgba(24, 144, 255, 0.25)"
            stroke="#1890ff"
            strokeWidth={1}
            strokeDasharray="8 4"
          />

          {stations.map((st) => (
            <g key={st.id}>
              <line
                x1={st.chainage}
                y1={20}
                x2={st.chainage}
                y2={80}
                stroke="#3a3a5a"
                strokeWidth={1}
                strokeDasharray="4 4"
              />
              <text
                x={st.chainage}
                y={16}
                fill="#a0a0a0"
                fontSize={totalLength / 80}
                textAnchor="middle"
              >
                {st.name}
              </text>
            </g>
          ))}

          <line
            x1={targetChainage}
            y1={trackY - 8}
            x2={targetChainage}
            y2={trackY + trackH + 8}
            stroke="#52c41a"
            strokeWidth={2}
          />

          <rect
            x={position - 20}
            y={trackY - 2}
            width={40}
            height={trackH + 4}
            fill="#1890ff"
            stroke="#69c0ff"
            strokeWidth={1}
            rx={2}
          />
          <text
            x={position}
            y={trackY + trackH / 2 + 3}
            fill="#fff"
            fontSize={totalLength / 100}
            textAnchor="middle"
          >
            🚃
          </text>
        </svg>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '4px 8px' }}>
        相位: {phaseLabel}
        {' · '}
        距目标站: {train ? `${train.distance_to_station.toFixed(0)} m` : '--'}
        {' · '}
        安全包络: {MA_ENVELOPE_LENGTH} m
      </div>
    </div>
  );
}
