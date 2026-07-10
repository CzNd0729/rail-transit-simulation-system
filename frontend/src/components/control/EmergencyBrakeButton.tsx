/**
 * EmergencyBrakeButton — 手动紧急制动按钮
 *
 * 状态机：
 *   idle → 点击 → EB 激活，按钮 disabled 显示"紧急制动中"
 *                → 列车停稳（speed < 0.1）→ 按钮可点击"解除紧急制动"
 *                → 点击解除 → 回到 idle
 */
import { useState } from 'react';

interface Props {
  send: (data: object) => void;
  runState: string;
  speed: number;  // 当前列车速度 (km/h)
}

export default function EmergencyBrakeButton({ send, runState, speed }: Props) {
  const [activated, setActivated] = useState(false);

  const isRunning = runState === 'running';
  const isStopped = speed < 0.1;
  const canDeactivate = activated && isStopped;

  const handleClick = () => {
    if (activated && !isStopped) return;  // 停稳前不可解除
    const next = !activated;
    setActivated(next);
    send({ type: 'manual_control', emergencyBrake: next });
  };

  const disabled = !isRunning || (activated && !isStopped);

  let label = '🚨 紧急制动';
  if (activated) {
    label = isStopped ? '🚨 解除紧急制动' : '🚨 紧急制动中';
  }

  return (
    <button
      onClick={handleClick}
      disabled={disabled}
      style={{
        ...styles.button,
        ...(activated && !isStopped ? styles.braking : {}),
        ...(activated && isStopped ? styles.canRelease : {}),
        ...(disabled && !activated ? styles.disabled : {}),
      }}
    >
      {label}
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  button: {
    width: '100%',
    padding: '12px 0',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#fff',
    backgroundColor: '#dc3545',
    border: '2px solid #b02a37',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  braking: {
    backgroundColor: '#b02a37',
    cursor: 'not-allowed',
    opacity: 0.8,
    animation: 'none',
  },
  canRelease: {
    backgroundColor: '#dc3545',
    cursor: 'pointer',
    opacity: 1.0,
  },
  disabled: {
    backgroundColor: '#6c757d',
    border: '2px solid #5c636a',
    cursor: 'not-allowed',
    opacity: 0.65,
  },
};