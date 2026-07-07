/**
 * RunControlButtons — 运行/暂停/停止按钮组
 * 基于《需求文档》UI-CTRL-01
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
}

export default function RunControlButtons({ send }: Props) {
  const { runState } = useSimulationState();
  const { startSimulation, pauseSimulation, resumeSimulation, stopSimulation } = useSimulation(send);

  const isIdle = runState === 'idle' || runState === 'stopped';
  const isRunning = runState === 'running';
  const isPaused = runState === 'paused';

  return (
    <div style={styles.group}>
      {/* 运行/继续按钮 */}
      {isIdle && (
        <button className="btn btn-success" onClick={startSimulation} style={styles.btn}>
          ▶ 运行
        </button>
      )}
      {isPaused && (
        <button className="btn btn-success" onClick={resumeSimulation} style={styles.btn}>
          ▶ 继续
        </button>
      )}

      {/* 暂停按钮 */}
      <button
        className="btn btn-warning"
        onClick={pauseSimulation}
        disabled={!isRunning}
        style={styles.btn}
      >
        ⏸ 暂停
      </button>

      {/* 停止按钮 */}
      <button
        className="btn btn-danger"
        onClick={stopSimulation}
        disabled={isIdle}
        style={styles.btn}
      >
        ⏹ 停止
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  group: {
    display: 'flex',
    gap: '6px',
  },
  btn: {
    flex: 1,
    fontSize: '13px',
    padding: '8px 0',
  },
};
