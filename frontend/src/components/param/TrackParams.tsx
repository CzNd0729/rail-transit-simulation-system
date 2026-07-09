/**
 * TrackParams — 线路参数编辑表单
 * 基于《需求文档》UI-PARAM-02
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
}

export default function TrackParamsForm({ send, disabled = false }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    if (disabled) return;
    updateParams({ track: { ...params.track, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🛤️ 线路参数</legend>
      {params.track.segment_id && (
        <div style={styles.hint}>当前区段：{params.track.segment_id}</div>
      )}
      <ParamRow label="坡度 (‰)" value={params.track.gradient} onChange={(v) => handleChange('gradient', v)} disabled={disabled} />
      <ParamRow label="曲率半径 (m)" value={params.track.curvature} onChange={(v) => handleChange('curvature', v)} disabled={disabled} />
      <ParamRow label="限速 (km/h)" value={params.track.speed_limit} onChange={(v) => handleChange('speed_limit', v)} disabled={disabled} />
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
  hint: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginBottom: '4px',
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
