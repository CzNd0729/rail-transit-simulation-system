/**
 * VehicleParams — 车辆参数编辑表单
 * 基于《需求文档》UI-PARAM-01
 */
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import { DEFAULT_VEHICLE_PARAMS } from '../../data/mockVehicleParams';
import ParamStepper from './ParamStepper';
import {
  VEHICLE_PARAM_STEP_KEYS,
  computeFixedParamStep,
  type VehicleParamStepKey,
} from '../../utils/paramStep';

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
  davis_C_drag_coeff: '空气阻力系数 Cd',
  curve_resist_coeff: '弯道阻力系数',
  tunnel_resist_factor: '隧道阻力系数',
};

export default function VehicleParamsForm({ send, disabled = false }: Props) {
  const { params, vehicleParamBaselines } = useSimulationState();
  const dispatch = useSimulationDispatch();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: VehicleParamStepKey, value: number) => {
    if (disabled) return;
    updateParams({ vehicle: { ...params.vehicle, [key]: value } });
  };

  const handleReset = () => {
    if (disabled) return;
    dispatch({ type: 'INIT_DEFAULT_PARAMS' });
    updateParams({ vehicle: { ...DEFAULT_VEHICLE_PARAMS } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚇 车辆参数</legend>
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
  resetBtn: {
    marginTop: '6px',
    width: '100%',
    fontSize: '12px',
  },
};
