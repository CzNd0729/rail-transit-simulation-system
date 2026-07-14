/**
 * EvaluationParams — 评估参数编辑表单
 * 包含仿真总时长和评估窗口时长，放在参数配置面板最前面
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import ParamStepper from './ParamStepper';

interface Props {
  send: (data: object) => void;
  disabled?: boolean;
}

const PARAM_DEFS = [
  { key: 'total_time', label: '仿真总时长', unit: 's', step: 60, defaultValue: 6000, min: 60 },
  { key: 'evaluation_time', label: '评估窗口时长', unit: 's', step: 30, defaultValue: 600, min: 30 },
];

export default function EvaluationParamsForm({ send, disabled = false }: Props) {
  const { params, runState } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: string, value: number) => {
    if (disabled) return;
    updateParams({ signal: { ...params.signal, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>📋 评估参数</legend>
      {PARAM_DEFS.map((def) => {
        const value = params.signal[def.key as keyof typeof params.signal] ?? def.defaultValue;
        return (
          <ParamStepper
            key={def.key}
            label={`${def.label} (${def.unit})`}
            value={value as number}
            step={def.step}
            min={def.min}
            onChange={(v) => handleChange(def.key, v)}
            disabled={disabled}
          />
        );
      })}
      <div style={styles.hint}>
        仿真至少运行到评估窗口时长后，系统自动保存方案
      </div>
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
    lineHeight: 1.4,
  },
};