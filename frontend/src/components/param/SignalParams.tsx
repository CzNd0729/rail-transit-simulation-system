/**
 * SignalParams — 信号参数编辑表单
 * 基于《需求文档》UI-PARAM-04（迭代三）
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
}

export default function SignalParamsForm({ send }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    updateParams({ signal: { ...params.signal, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚦 信号参数</legend>
      <ParamRow label="站停时间 (s)" value={params.signal.dwell_time} onChange={(v) => handleChange('dwell_time', v)} />
      <ParamRow label="发车间隔 (s)" value={params.signal.departure_interval} onChange={(v) => handleChange('departure_interval', v)} />
      <ParamRow label="目标速度比" value={params.signal.target_speed_ratio} onChange={(v) => handleChange('target_speed_ratio', v)} />
    </fieldset>
  );
}

function ParamRow({ label, value, onChange }: { label: string; value: number | undefined; onChange: (v: number) => void }) {
  return (
    <div style={styles.row}>
      <label>{label}</label>
      <input
        type="number"
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        style={styles.input}
        placeholder="默认值"
        step={label === '目标速度比' ? 0.05 : 1}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  fieldset: {
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: '8px',
  },
  legend: {
    fontSize: '12px',
    color: 'var(--text-highlight)',
    padding: '0 4px',
  },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '3px 0',
  },
  input: {
    width: '100px',
    textAlign: 'right' as const,
  },
};
