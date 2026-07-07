/**
 * StepButton — 单步执行按钮
 * 基于《需求文档》UI-CTRL-03
 * 仅在暂停/空闲状态可用
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';

interface Props {
  send: (data: object) => void;
}

export default function StepButton({ send }: Props) {
  const { runState } = useSimulationState();
  const { stepSimulation } = useSimulation(send);

  const canStep = runState === 'idle' || runState === 'paused' || runState === 'stopped';

  return (
    <button
      className="btn"
      onClick={stepSimulation}
      disabled={!canStep}
      style={styles.btn}
    >
      ⏭ 单步执行
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  btn: {
    width: '100%',
    padding: '6px 0',
    fontSize: '12px',
  },
};
