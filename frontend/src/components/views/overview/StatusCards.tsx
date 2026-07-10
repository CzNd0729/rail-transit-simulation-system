/**
 * StatusCards — 关键状态速览卡片
 * 基于《需求文档》UI-VW-04
 * 4 个小卡片：当前速度、网压、工况、距站台距离
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { formatSpeed, formatVoltage, getModeLabel, getModeColor } from '../../../utils/format';

export default function StatusCards() {
  const { trains, lineLayout } = useSimulationState();
  const train = trains[0]; // 默认显示第一列车

  // 距站台距离显示
  let distanceText = '--';
  let distanceColor = '#808080';
  if (train && train.target_station_id) {
    const station = lineLayout?.stations.find(s => s.id === train.target_station_id);
    const stationName = station?.name ?? train.target_station_id;
    const d = train.distance_to_station;
    if (d > 0) {
      distanceText = `距 ${stationName} ${d.toFixed(1)}m`;
    } else if (d === 0) {
      distanceText = `已到 ${stationName}`;
    } else {
      distanceText = `已过 ${stationName} ${Math.abs(d).toFixed(1)}m`;
    }
    distanceColor = Math.abs(d) <= 1.0 ? '#52c41a' : '#ff4d4f';
  }

  const cards = [
    {
      label: '当前速度',
      value: train ? formatSpeed(train.speed) : '-- km/h',
      icon: '🏎️',
      color: '#1890ff',
    },
    {
      label: '受电弓电压',
      value: train ? formatVoltage(train.pantograph_voltage) : '-- V',
      icon: '⚡',
      color: '#faad14',
    },
    {
      label: '当前工况',
      value: train ? getModeLabel(train.mode) : '--',
      icon: '⚙️',
      color: train ? getModeColor(train.mode) : '#999',
    },
    {
      label: '距站台',
      value: distanceText,
      icon: '📍',
      color: distanceColor,
    },
  ];

  return (
    <div style={styles.container}>
      {cards.map((card, i) => (
        <div key={i} className="panel" style={styles.card}>
          <div style={styles.icon}>{card.icon}</div>
          <div style={styles.info}>
            <div style={styles.label}>{card.label}</div>
            <div style={{ ...styles.value, color: card.color }}>{card.value}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    gap: '8px',
    flex: 1,
  },
  card: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 12px',
  },
  icon: {
    fontSize: '22px',
  },
  info: {
    display: 'flex',
    flexDirection: 'column',
  },
  label: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
  value: {
    fontSize: '16px',
    fontWeight: 600,
    fontFamily: 'monospace',
  },
};