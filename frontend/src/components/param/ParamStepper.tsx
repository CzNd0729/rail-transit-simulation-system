/**
 * ParamStepper — 带 ▲▼ 步进按钮的数值参数输入
 * 步进量由外部传入的固定 step 决定（通常为基准值 10%）
 */
import { applyParamStep } from '../../utils/paramStep';
interface ParamStepperProps {
  label: string;
  value: number | undefined;
  step: number;
  onChange: (value: number) => void;
  min?: number;
  disabled?: boolean;
}

export default function ParamStepper({
  label,
  value,
  step,
  onChange,
  min = 0,
  disabled = false,
}: ParamStepperProps) {
  const current = value ?? 0;

  const handleIncrement = () => {
    onChange(applyParamStep(current, step, 1, min));
  };

  const handleDecrement = () => {
    onChange(applyParamStep(current, step, -1, min));
  };

  const handleInput = (raw: string) => {
    const parsed = Number(raw);
    if (!Number.isNaN(parsed)) {
      onChange(parsed);
    }
  };

  return (
    <div style={styles.row}>
      <label style={styles.label}>{label}</label>
      <div style={styles.stepper}>
        <input
          type="number"
          value={value ?? ''}
          onChange={(e) => handleInput(e.target.value)}
          style={styles.input}
          disabled={disabled}
        />
        <div style={styles.buttons}>
          <button
            type="button"
            aria-label={`增加 ${label}`}
            style={styles.stepBtn}
            onClick={handleIncrement}
            disabled={disabled}
          >
            ▲
          </button>
          <button
            type="button"
            aria-label={`减少 ${label}`}
            style={styles.stepBtn}
            onClick={handleDecrement}
            disabled={disabled}
          >
            ▼
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '3px 0',
  },
  label: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
    flexShrink: 0,
  },
  stepper: {
    display: 'flex',
    alignItems: 'stretch',
    border: '1px solid var(--color-primary)',
    borderRadius: '4px',
    overflow: 'hidden',
    background: 'var(--bg-dark)',
  },
  input: {
    width: '88px',
    padding: '4px 8px',
    border: 'none',
    outline: 'none',
    background: 'transparent',
    color: 'var(--text-highlight)',
    textAlign: 'right' as const,
    fontFamily: 'monospace',
    fontSize: '12px',
  },
  buttons: {
    display: 'flex',
    flexDirection: 'column',
    borderLeft: '1px solid var(--border-color)',
  },
  stepBtn: {
    flex: 1,
    width: '22px',
    padding: 0,
    border: 'none',
    background: 'var(--bg-card)',
    color: 'var(--text-secondary)',
    fontSize: '8px',
    lineHeight: 1,
    cursor: 'pointer',
  },
};
