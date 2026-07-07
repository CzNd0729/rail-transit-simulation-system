/**
 * VehicleParams — 车辆参数编辑表单
 * 基于《需求文档》UI-PARAM-01
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
}

export default function VehicleParamsForm({ send }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    updateParams({ vehicle: { ...params.vehicle, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚇 车辆参数</legend>
      <ParamRow label="空车质量 (kg)" value={params.vehicle.empty_mass} onChange={(v) => handleChange('empty_mass', v)} />
      <ParamRow label="载客量" value={params.vehicle.passenger_capacity} onChange={(v) => handleChange('passenger_capacity', v)} />
      <ParamRow label="最大速度 (km/h)" value={params.vehicle.max_speed} onChange={(v) => handleChange('max_speed', v)} />
    </fieldset>
  );
}

/** 参数行组件 */
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
