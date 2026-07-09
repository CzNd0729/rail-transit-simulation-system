/**
 * VehicleParams — 车辆参数编辑表单
 * 基于《需求文档》UI-PARAM-01
 */
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import { DEFAULT_VEHICLE_PARAMS } from '../../data/mockVehicleParams';
import { USE_MOCK } from '../../utils/constants';
import ParamStepper from './ParamStepper';
import {
  VEHICLE_PARAM_STEP_KEYS,
  computeFixedParamStep,
  type VehicleParamStepKey,
} from '../../utils/paramStep';
import type { TractionCurvePoint } from '../../types/simulation';

interface Props {
  send: (data: object) => void;
}

const PARAM_LABELS: Record<VehicleParamStepKey, string> = {
  empty_mass: '空车质量 (kg)',
  passenger_capacity: '载客量',
  max_speed: '最大速度 (km/h)',
  max_traction_force: '最大牵引力 (N)',
  max_brake_force: '最大制动力 (N)',
  davis_A: 'Davis A',
  davis_B: 'Davis B',
  davis_C_front_area: '迎风面积 (m²)',
};

export default function VehicleParamsForm({ send }: Props) {
  const { params, vehicleParamBaselines } = useSimulationState();
  const dispatch = useSimulationDispatch();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: VehicleParamStepKey, value: number) => {
    updateParams({ vehicle: { ...params.vehicle, [key]: value } });
  };

  const handleCurveChange = (traction_curve: TractionCurvePoint[]) => {
    updateParams({ vehicle: { ...params.vehicle, traction_curve } });
  };

  const handleReset = () => {
    dispatch({ type: 'INIT_DEFAULT_PARAMS' });
    updateParams({ vehicle: { ...DEFAULT_VEHICLE_PARAMS } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚇 车辆参数</legend>
      <div style={styles.hint}>
        {USE_MOCK
          ? '参数在下次点击「运行」时生效'
          : '参数已提交后端（运行中修改下一步生效）'}
      </div>
      {VEHICLE_PARAM_STEP_KEYS.map((key) => {
        const baseline = vehicleParamBaselines[key] ?? params.vehicle[key] ?? 0;
        return (
          <ParamStepper
            key={key}
            label={PARAM_LABELS[key]}
            value={params.vehicle[key]}
            step={computeFixedParamStep(baseline)}
            onChange={(v) => handleChange(key, v)}
          />
        );
      })}
      <TractionCurveTable
        curve={params.vehicle.traction_curve}
        onChange={handleCurveChange}
        liveMode={!USE_MOCK}
      />
      <button
        type="button"
        className="btn"
        style={styles.resetBtn}
        onClick={handleReset}
      >
        恢复默认
      </button>
    </fieldset>
  );
}

function TractionCurveTable({ curve, onChange, liveMode }: {
  curve: TractionCurvePoint[] | undefined;
  onChange: (curve: TractionCurvePoint[]) => void;
  liveMode?: boolean;
}) {
  const points = curve ?? DEFAULT_VEHICLE_PARAMS.traction_curve;
  return (
    <div style={styles.curveSection}>
      <div style={styles.curveTitle}>
        牵引特性曲线{liveMode ? ' (迭代一后端暂不支持同步)' : ''}
      </div>
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
                  }} style={styles.inputPlain} />
              </td>
              <td style={styles.td}>
                <input type="number" step="0.1" min="0" max="1" value={pt.force_percent}
                  onChange={(e) => {
                    const next = [...points];
                    next[i] = { ...pt, force_percent: Number(e.target.value) };
                    onChange(next);
                  }} style={styles.inputPlain} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
  inputPlain: {
    width: '100px',
    textAlign: 'right' as const,
  },
  resetBtn: {
    marginTop: '6px',
    width: '100%',
    fontSize: '12px',
  },
};
