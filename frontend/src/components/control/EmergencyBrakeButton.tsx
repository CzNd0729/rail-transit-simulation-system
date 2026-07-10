/**
 * EmergencyBrakeButton — 手动紧急制动按钮
 * 仅仿真运行中可点击，锁定式（点击触发/点击解除）。
 */
import { useState } from 'react';

interface Props {
  send: (data: object) => void;
  runState: string;
}

export default function EmergencyBrakeButton({ send, runState }: Props) {
  const [activated, setActivated] = useState(false);

  const handleClick = () => {
    const next = !activated;
    setActivated(next);
    send({ type: 'manual_control', emergencyBrake: next });
  };

  const isRunning = runState === 'running';

  return (
    <button
      onClick={handleClick}
      disabled={!isRunning}
      style={{
        ...styles.button,
        ...(activated ? styles.active : {}),
        ...(!isRunning ? styles.disabled : {}),
      }}
    >
      {activated ? '🚨 解除紧急制动' : '🚨 紧急制动'}
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
  active: {
    backgroundColor: '#b02a37',
    boxShadow: 'inset 0 0 8px rgba(0,0,0,0.3)',
    animation: 'none',
  },
  disabled: {
    backgroundColor: '#6c757d',
    borderColor: '#5c636a',
    cursor: 'not-allowed',
    opacity: 0.65,
  },
};