/**
 * SubsystemIndicators — 子系统状态指示器
 * 基于《需求文档》UI-VW-05（迭代三）
 * 供电/信号/轨道/车辆各系统状态灯（绿/黄/红）
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { getStatusColor } from '../../../utils/format';

type SystemStatus = 'normal' | 'warning' | 'error';

export default function SubsystemIndicators() {
  const { trains } = useSimulationState();

  // 简单的状态判断逻辑（后续迭代可细化）
  const vehicleStatus: SystemStatus = trains.length > 0 ? 'normal' : 'warning';
  const powerStatus: SystemStatus = trains.some((t) => t.pantograph_voltage < 1400) ? 'warning' : 'normal';
  const signalStatus: SystemStatus = 'normal';
  const trackStatus: SystemStatus = 'normal';

  const systems = [
    { name: '车辆系统', status: vehicleStatus, icon: '🚇' },
    { name: '供电系统', status: powerStatus, icon: '⚡' },
    { name: '信号系统', status: signalStatus, icon: '🚦' },
    { name: '轨道系统', status: trackStatus, icon: '🛤️' },
  ];

  return (
    <div className="panel" style={styles.container}>
      <div style={styles.title}>子系统状态</div>
      <div style={styles.grid}>
        {systems.map((sys, i) => (
          <div key={i} style={styles.item}>
            <span
              style={{
                ...styles.dot,
                backgroundColor: getStatusColor(sys.status),
              }}
            />
            <span style={styles.icon}>{sys.icon}</span>
            <span style={styles.name}>{sys.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    padding: '10px 12px',
    minWidth: '200px',
  },
  title: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    marginBottom: '8px',
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  icon: {
    fontSize: '14px',
  },
  name: {
    color: 'var(--text-primary)',
  },
};
