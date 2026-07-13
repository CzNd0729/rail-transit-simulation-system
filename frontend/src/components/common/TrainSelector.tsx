/**
 * TrainSelector — 多车仿真下列表选择当前详情视图关注的列车
 * 改为下拉框样式，显示方向+下一站+距离，支持空选（全部列车）
 */
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';

function stationName(
  stations: { id: string; name: string }[] | undefined,
  stationId: string,
): string {
  return stations?.find((s) => s.id === stationId)?.name ?? stationId;
}

export default function TrainSelector() {
  const { trains, selectedTrainId, lineLayout } = useSimulationState();
  const dispatch = useSimulationDispatch();

  if (trains.length <= 1) {
    return null;
  }

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    dispatch({
      type: 'SET_SELECTED_TRAIN',
      payload: value === '' ? null : value,
    });
  };

  return (
    <div style={styles.container} title="选择详情视图关注的列车">
      <span style={styles.label}>关注列车</span>
      <select
        value={selectedTrainId ?? ''}
        onChange={handleChange}
        style={styles.select}
      >
        <option value="">全部列车</option>
        {trains.map((train) => {
          const dirLabel = train.direction === 'down' ? '↓' : '↑';
          const nextName = stationName(
            lineLayout?.stations,
            train.target_station_id,
          );
          const distKm =
            train.distance_to_station != null
              ? (train.distance_to_station / 1000).toFixed(1) + 'km'
              : '';
          return (
            <option key={train.id} value={train.id}>
              {dirLabel} {train.id} → {nextName}
              {distKm ? ` (${distKm})` : ''}
            </option>
          );
        })}
      </select>
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
  select: {
    fontSize: '12px',
    padding: '3px 24px 3px 8px',
    fontFamily: 'monospace',
    backgroundColor: 'var(--bg-dark)',
    color: 'var(--text-highlight)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    cursor: 'pointer',
    outline: 'none',
    minWidth: '200px',
    appearance: 'auto',
  },
};
