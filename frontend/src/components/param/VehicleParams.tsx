/**
 * VehicleParams — 车辆参数编辑表单
 * 基于《需求文档》UI-PARAM-01
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import { DEFAULT_VEHICLE_PARAMS } from '../../data/mockVehicleParams';
import type { TractionCurvePoint } from '../../types/simulation';

interface Props {
  send: (data: object) => void;
}

export default function VehicleParamsForm({ send }: Props) {
  const { params } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    updateParams({ vehicle: { ...params.vehicle, [key]: value } });
  };

  const handleCurveChange = (traction_curve: TractionCurvePoint[]) => {
    updateParams({ vehicle: { ...params.vehicle, traction_curve } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚇 车辆参数</legend>
      <div style={styles.hint}>参数在下次点击「运行」时生效</div>
      <ParamRow label="空车质量 (kg)" value={params.vehicle.empty_mass} onChange={(v) => handleChange('empty_mass', v)} />
      <ParamRow label="载客量" value={params.vehicle.passenger_capacity} onChange={(v) => handleChange('passenger_capacity', v)} />
      <ParamRow label="最大速度 (km/h)" value={params.vehicle.max_speed} onChange={(v) => handleChange('max_speed', v)} />
      <ParamRow label="最大牵引力 (N)" value={params.vehicle.max_traction_force} onChange={(v) => handleChange('max_traction_force', v)} />
      <ParamRow label="最大制动力 (N)" value={params.vehicle.max_brake_force} onChange={(v) => handleChange('max_brake_force', v)} />
      <ParamRow label="Davis A" value={params.vehicle.davis_A} onChange={(v) => handleChange('davis_A', v)} step="0.001" />
      <ParamRow label="Davis B" value={params.vehicle.davis_B} onChange={(v) => handleChange('davis_B', v)} step="0.0001" />
      <ParamRow label="迎风面积 (m²)" value={params.vehicle.davis_C_front_area} onChange={(v) => handleChange('davis_C_front_area', v)} />
      <TractionCurveTable
        curve={params.vehicle.traction_curve}
        onChange={handleCurveChange}
      />
      <button
        type="button"
        className="btn"
        style={styles.resetBtn}
        onClick={() => updateParams({ vehicle: { ...DEFAULT_VEHICLE_PARAMS } })}
      >
        恢复默认
      </button>
    </fieldset>
  );
}

function TractionCurveTable({ curve, onChange }: {
  curve: TractionCurvePoint[] | undefined;
  onChange: (curve: TractionCurvePoint[]) => void;
}) {
  const points = curve ?? DEFAULT_VEHICLE_PARAMS.traction_curve;
  return (
    <div style={styles.curveSection}>
      <div style={styles.curveTitle}>牵引特性曲线</div>
      <table style={styles.table}>
        <thead>
          <tr><th style={styles.th}>速度 (km/h)</th><th style={styles.th}>牵引力 %</th></tr>
        </thead>
        <tbody>
          {points.map((pt, i) => (
            <tr key={i}>
              <td style={styles.td}>
                <input type="number" value={pt.speed}
                  onChange={(e) => {
                    const next = [...points];
                    next[i] = { ...pt, speed: Number(e.target.value) };
                    onChange(next);
                  }} style={styles.input} />
              </td>
              <td style={styles.td}>
                <input type="number" step="0.1" min="0" max="1" value={pt.force_percent}
                  onChange={(e) => {
                    const next = [...points];
                    next[i] = { ...pt, force_percent: Number(e.target.value) };
                    onChange(next);
                  }} style={styles.input} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ParamRow({ label, value, onChange, step }: {
  label: string;
  value: number | undefined;
  onChange: (v: number) => void;
  step?: string;
}) {
  return (
    <div style={styles.row}>
      <label>{label}</label>
      <input
        type="number"
        step={step}
        value={value ?? ''}
        onChange={(e) => onChange(Number(e.target.value))}
        style={styles.input}
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
  curveSection: {
    marginTop: '6px',
  },
  curveTitle: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    marginBottom: '4px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '11px',
  },
  th: {
    textAlign: 'left' as const,
    color: 'var(--text-secondary)',
    paddingBottom: '2px',
  },
  td: {
    padding: '2px 0',
  },
  resetBtn: {
    marginTop: '6px',
    width: '100%',
    fontSize: '12px',
  },
};
