/**
 * PowerParams — 供电参数编辑表单
 * 基于《需求文档》UI-PARAM-03
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import ParamStepper from './ParamStepper';
import {
  POWER_PARAM_STEP_KEYS,
  computeFixedParamStep,
  type PowerParamStepKey,
} from '../../utils/paramStep';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
}

const PARAM_LABELS: Record<PowerParamStepKey, string> = {
  pantograph_voltage: '网压 (V)',
  substation_capacity: '变电所容量 (kW)',
};

export default function PowerParamsForm({ send, disabled = false }: Props) {
  const { params, powerParamBaselines } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: PowerParamStepKey, value: number) => {
    if (disabled) return;
    updateParams({ power: { ...params.power, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>⚡ 供电参数</legend>
      {POWER_PARAM_STEP_KEYS.map((key) => {
        const baseline = powerParamBaselines[key] ?? params.power[key] ?? 0;
        return (
          <ParamStepper
            key={key}
            label={PARAM_LABELS[key]}
            value={params.power[key]}
            step={computeFixedParamStep(baseline)}
            min={1}
            onChange={(v) => handleChange(key, v)}
            disabled={disabled}
          />
        );
      })}
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
};
