/**
 * ParamStepper — 带 ▲▼ 步进按钮的数值参数输入
 * 步进量由外部传入的固定 step 决定（通常为基准值 10%）
 */
import { applyParamStep } from '../../utils/paramStep';

interface ParamStepperProps {
  label?: string;
  value: number | undefined;
  step: number;
  onChange: (value: number) => void;
  min?: number;
<<<<<<< HEAD
  disabled?: boolean;
=======
  max?: number;
  /** 表格内紧凑模式：不显示左侧标签 */
  compact?: boolean;
}

function clamp(value: number, min: number, max?: number): number {
  let result = Math.max(min, value);
  if (max !== undefined) {
    result = Math.min(max, result);
  }
  return result;
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
}

export default function ParamStepper({
  label,
  value,
  step,
  onChange,
  min = 0,
<<<<<<< HEAD
  disabled = false,
=======
  max,
  compact = false,
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
}: ParamStepperProps) {
  const current = value ?? 0;

  const atMax = max !== undefined && current >= max - 1e-9;
  const atMin = current <= min + 1e-9;

  const handleIncrement = () => {
    if (atMax) return;
    onChange(clamp(applyParamStep(current, step, 1, min), min, max));
  };

  const handleDecrement = () => {
    if (atMin) return;
    onChange(clamp(applyParamStep(current, step, -1, min), min, max));
  };

  const handleInput = (raw: string) => {
    const parsed = Number(raw);
    if (!Number.isNaN(parsed)) {
      onChange(clamp(parsed, min, max));
    }
  };

  return (
    <div style={compact ? styles.rowCompact : styles.row}>
      {!compact && label && <label style={styles.label}>{label}</label>}
      <div style={compact ? styles.stepperCompact : styles.stepper}>
        <input
          type="number"
          className="param-stepper-input"
          value={value ?? ''}
          onChange={(e) => handleInput(e.target.value)}
<<<<<<< HEAD
          style={styles.input}
          disabled={disabled}
=======
          style={compact ? styles.inputCompact : styles.input}
>>>>>>> b9b3a165a517dee3db6dd21806ed3697074fe3bf
        />
        <div style={styles.buttons}>
          <button
            type="button"
            aria-label={label ? `增加 ${label}` : '增加'}
            style={{
              ...styles.stepBtn,
              opacity: atMax ? 0.35 : 1,
              cursor: atMax ? 'not-allowed' : 'pointer',
            }}
            disabled={atMax}
            title={atMax ? '已达上限' : undefined}
            onClick={handleIncrement}
            disabled={disabled}
          >
            ▲
          </button>
          <button
            type="button"
            aria-label={label ? `减少 ${label}` : '减少'}
            style={{
              ...styles.stepBtn,
              opacity: atMin ? 0.35 : 1,
              cursor: atMin ? 'not-allowed' : 'pointer',
            }}
            disabled={atMin}
            title={atMin ? '已达下限' : undefined}
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
  rowCompact: {
    display: 'flex',
    justifyContent: 'flex-end',
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
  stepperCompact: {
    display: 'flex',
    alignItems: 'stretch',
    border: '1px solid var(--color-primary)',
    borderRadius: '4px',
    overflow: 'hidden',
    background: 'var(--bg-dark)',
    width: '100%',
    maxWidth: '120px',
    marginLeft: 'auto',
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
  inputCompact: {
    flex: 1,
    minWidth: 0,
    padding: '4px 6px',
    border: 'none',
    outline: 'none',
    background: 'transparent',
    color: 'var(--text-highlight)',
    textAlign: 'right' as const,
    fontFamily: 'monospace',
    fontSize: '11px',
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
