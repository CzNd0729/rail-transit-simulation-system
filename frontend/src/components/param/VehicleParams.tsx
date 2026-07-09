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
  type TractionCurvePointBaseline,
} from '../../utils/paramStep';
import type { TractionCurvePoint } from '../../types/simulation';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
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

<<<<<<< HEAD
export default function VehicleParamsForm({ send, disabled = false }: Props) {
  const { params, vehicleParamBaselines, runState } = useSimulationState();
=======
export default function VehicleParamsForm({ send }: Props) {
  const { params, vehicleParamBaselines, tractionCurveBaselines } = useSimulationState();
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
  const dispatch = useSimulationDispatch();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: VehicleParamStepKey, value: number) => {
    if (disabled) return;
    updateParams({ vehicle: { ...params.vehicle, [key]: value } });
  };

  const handleCurveChange = (traction_curve: TractionCurvePoint[]) => {
    if (disabled) return;
    updateParams({ vehicle: { ...params.vehicle, traction_curve } });
  };

  const handleReset = () => {
    if (disabled) return;
    dispatch({ type: 'INIT_DEFAULT_PARAMS' });
    updateParams({ vehicle: { ...DEFAULT_VEHICLE_PARAMS } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚇 车辆参数</legend>
      <div style={styles.hint}>
        {runState === 'running'
          ? '仿真运行中已锁定，请先暂停或停止'
          : USE_MOCK
            ? '参数在下次点击「运行」时生效'
            : '参数已提交后端（暂停或空闲时可修改）'}
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
            disabled={disabled}
          />
        );
      })}
      <TractionCurveTable
        curve={params.vehicle.traction_curve}
        baselines={tractionCurveBaselines}
        onChange={handleCurveChange}
        liveMode={!USE_MOCK}
        disabled={disabled}
      />
      <button
        type="button"
        className="btn"
        style={styles.resetBtn}
        onClick={handleReset}
        disabled={disabled}
      >
        恢复默认
      </button>
    </fieldset>
  );
}

<<<<<<< HEAD
function TractionCurveTable({ curve, onChange, liveMode, disabled = false }: {
=======
function TractionCurveTable({ curve, baselines, onChange, liveMode }: {
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
  curve: TractionCurvePoint[] | undefined;
  baselines: TractionCurvePointBaseline[];
  onChange: (curve: TractionCurvePoint[]) => void;
  liveMode?: boolean;
  disabled?: boolean;
}) {
  const points = curve ?? DEFAULT_VEHICLE_PARAMS.traction_curve;

  const updatePoint = (index: number, patch: Partial<TractionCurvePoint>) => {
    const next = [...points];
    next[index] = { ...next[index], ...patch };
    onChange(next);
  };

  return (
    <div style={styles.curveSection}>
      <div style={styles.curveTitle}>
        牵引特性曲线
      </div>
      <table style={styles.table}>
        <thead>
          <tr><th style={styles.th}>速度 (km/h)</th><th style={styles.th}>牵引力 %</th></tr>
        </thead>
        <tbody>
<<<<<<< HEAD
          {points.map((pt, i) => (
            <tr key={i}>
              <td style={styles.td}>
                <input type="number" value={pt.speed}
                  disabled={disabled}
                  onChange={(e) => {
                    const next = [...points];
                    next[i] = { ...pt, speed: Number(e.target.value) };
                    onChange(next);
                  }} style={styles.inputPlain} />
              </td>
              <td style={styles.td}>
                <input type="number" step="0.1" min="0" max="1" value={pt.force_percent}
                  disabled={disabled}
                  onChange={(e) => {
                    const next = [...points];
                    next[i] = { ...pt, force_percent: Number(e.target.value) };
                    onChange(next);
                  }} style={styles.inputPlain} />
              </td>
            </tr>
          ))}
=======
          {points.map((pt, i) => {
            const base = baselines[i] ?? { speed: pt.speed, force_percent: pt.force_percent };
            return (
              <tr key={i}>
                <td style={styles.td}>
                  <ParamStepper
                    compact
                    value={pt.speed}
                    step={computeFixedParamStep(base.speed)}
                    onChange={(speed) => updatePoint(i, { speed })}
                  />
                </td>
                <td style={styles.td}>
                  <ParamStepper
                    compact
                    value={Math.round(pt.force_percent * 1000) / 10}
                    step={computeFixedParamStep(base.force_percent * 100)}
                    min={0}
                    max={100}
                    onChange={(pct) => updatePoint(i, { force_percent: pct / 100 })}
                  />
                </td>
              </tr>
            );
          })}
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
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
    verticalAlign: 'middle' as const,
  },
  resetBtn: {
    marginTop: '6px',
    width: '100%',
    fontSize: '12px',
  },
};
