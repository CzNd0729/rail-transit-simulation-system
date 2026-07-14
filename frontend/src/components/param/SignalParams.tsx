/**
 * SignalParams — 信号参数编辑表单
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import ParamStepper from './ParamStepper';
import {
  SIGNAL_PARAM_STEP_KEYS,
  computeFixedParamStep,
  type SignalParamStepKey,
} from '../../utils/paramStep';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
}

const PARAM_LABELS: Record<SignalParamStepKey, string> = {
  dwell_time: '站停时间 (s)',
  departure_interval: '发车间隔 (s)',
  target_speed_ratio: '目标速度比',
  safety_distance: 'ATP安全距离 (m)',
  comfort_decel: '舒适减速度 (m/s²)',
  max_jerk: '冲击率上限 (m/s³)',
};

export default function SignalParamsForm({ send, disabled = false }: Props) {
  const { params, signalParamBaselines, connection } = useSimulationState();
  const { updateParams } = useSimulation(send);
  const isLive = import.meta.env.VITE_USE_MOCK !== 'true';

  const handleChange = (key: SignalParamStepKey, value: number) => {
    if (disabled) return;
    updateParams({ signal: { ...params.signal, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🚦 信号参数</legend>
      {SIGNAL_PARAM_STEP_KEYS.map((key) => {
        const baseline = signalParamBaselines[key] ?? params.signal[key] ?? 0;
        return (
          <ParamStepper
            key={key}
            label={PARAM_LABELS[key]}
            value={params.signal[key]}
            step={computeFixedParamStep(baseline)}
            onChange={(v) => handleChange(key, v)}
            disabled={disabled}
          />
        );
      })}
      {disabled && (
        <p style={styles.hint}>
          仿真运行中参数已锁定，请暂停后修改（与后端 PUT /params 行为一致）。
        </p>
      )}
      {!disabled && isLive && connection === 'connected' && (
        <p style={styles.hint}>
          Live 模式：暂停后可修改站停时间、发车间隔与目标速度比。
        </p>
      )}
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
    fontSize: 11,
    color: 'var(--text-secondary)',
    margin: '6px 0 0',
  },
};
