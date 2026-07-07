/**
 * TrackParams — 线路参数编辑表单
 * 基于《需求文档》UI-PARAM-02
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
}

export default function TrackParamsForm({ send }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    updateParams({ track: { ...params.track, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🛤️ 线路参数</legend>
      <ParamRow label="坡度 (‰)" value={params.track.gradient} onChange={(v) => handleChange('gradient', v)} />
      <ParamRow label="曲率半径 (m)" value={params.track.curvature} onChange={(v) => handleChange('curvature', v)} />
      <ParamRow label="限速 (km/h)" value={params.track.speed_limit} onChange={(v) => handleChange('speed_limit', v)} />
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
