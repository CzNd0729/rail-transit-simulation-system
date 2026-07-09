/**
 * PowerParams — 供电参数编辑表单
 * 基于《需求文档》UI-PARAM-03（迭代三）
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
}

export default function PowerParamsForm({ send, disabled = false }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    if (disabled) return;
    updateParams({ power: { ...params.power, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>⚡ 供电参数</legend>
      <ParamRow
        label="网压 (V)"
        value={params.power.pantograph_voltage}
        onChange={(v) => handleChange('pantograph_voltage', v)}
        disabled={disabled}
      />
      <ParamRow
        label="变电所容量 (kW)"
        value={params.power.substation_capacity}
        onChange={(v) => handleChange('substation_capacity', v)}
        disabled={disabled}
      />
    </fieldset>
  );
}

function ParamRow({ label, value, onChange, disabled = false }: {
  label: string;
  value: number | undefined;
  onChange: (v: number) => void;
  disabled?: boolean;
}) {
  return (
    <div style={styles.row}>
      <label>{label}</label>
      <input
        type="number"
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        style={styles.input}
        placeholder="默认值"
        disabled={disabled}
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
