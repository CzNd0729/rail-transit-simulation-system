/**
 * SpeedSelector — 仿真速度倍率选择器
 * 基于《需求文档》UI-CTRL-02
 * 迭代一实现为按钮组，迭代二可改为滑块
 */
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';
import { setSimulationSpeed } from '../../services/api';
import { SPEED_MULTIPLIER_OPTIONS, USE_MOCK } from '../../utils/constants';
import type { SpeedMultiplier } from '../../types/simulation';

interface Props {
  send: (data: object) => void;
}

export default function SpeedSelector({ send }: Props) {
  const { clock } = useSimulationState();
  const dispatch = useSimulationDispatch();

  const handleSpeedChange = async (multiplier: SpeedMultiplier) => {
    dispatch({ type: 'SET_SPEED_MULTIPLIER', payload: multiplier });
    if (USE_MOCK) {
      send({ type: 'speed_multiplier', value: multiplier });
    } else {
      try {
        await setSimulationSpeed(multiplier);
      } catch (e) {
        console.error('[SpeedSelector] REST 倍率设置失败', e);
      }
    }
  };

  return (
    <div style={styles.container}>
      <label style={styles.label}>速度倍率</label>
      <div style={styles.group}>
        {SPEED_MULTIPLIER_OPTIONS.map((opt) => (
          <button
            key={opt}
            className={`btn ${clock.speed_multiplier === opt ? 'btn-primary' : ''}`}
            onClick={() => handleSpeedChange(opt)}
            style={styles.btn}
          >
            {opt}×
          </button>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  label: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
  group: {
    display: 'flex',
    gap: '4px',
  },
  btn: {
    flex: 1,
    fontSize: '12px',
    padding: '4px 0',
  },
};
