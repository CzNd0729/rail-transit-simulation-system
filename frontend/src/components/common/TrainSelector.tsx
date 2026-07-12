/**
 * TrainSelector — 多车仿真下列表选择当前详情视图关注的列车
 */
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';

export default function TrainSelector() {
  const { trains, selectedTrainId } = useSimulationState();
  const dispatch = useSimulationDispatch();

  if (trains.length <= 1) {
    return null;
  }

  const activeId = selectedTrainId ?? trains[0]?.id ?? null;

  return (
    <div style={styles.container} title="选择详情视图关注的列车">
      <span style={styles.label}>关注列车</span>
      <div style={styles.group}>
        {trains.map((train) => {
          const selected = train.id === activeId;
          const dirLabel = train.direction === 'down' ? '↓' : '↑';
          return (
            <button
              key={train.id}
              type="button"
              className={`btn ${selected ? 'btn-primary' : ''}`}
              style={styles.btn}
              onClick={() =>
                dispatch({ type: 'SET_SELECTED_TRAIN', payload: train.id })
              }
            >
              {dirLabel} {train.id}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexShrink: 0,
  },
  label: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    whiteSpace: 'nowrap',
  },
  group: {
    display: 'flex',
    gap: '4px',
    flexWrap: 'wrap',
  },
  btn: {
    fontSize: '11px',
    padding: '2px 8px',
    fontFamily: 'monospace',
  },
};
