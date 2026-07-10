/**
 * ControlPanel — 仿真控制面板
 * 基于《需求文档》3.4.1 仿真控制区设计
 *
 * 功能：
 * - UI-CTRL-01: 运行/暂停/停止按钮
 * - UI-CTRL-02: 仿真速度倍率选择器 (1× / 5× / 10×)
 * - UI-CTRL-03: 单步执行按钮（仅暂停/空闲可用）
 */
import RunControlButtons from './RunControlButtons';
import SpeedSelector from './SpeedSelector';
import StepButton from './StepButton';
import EmergencyBrakeButton from './EmergencyBrakeButton';
import { useSimulationState } from '../../context/SimulationContext';

interface Props {
  send: (data: object) => void;
}

export default function ControlPanel({ send }: Props) {
  const { runState, trains } = useSimulationState();
  const speed = trains[0]?.speed ?? 0;

  return (
    <div className="panel">
      <div className="panel-title">🎮 仿真控制</div>
      <div style={styles.content}>
        <RunControlButtons send={send} />
        <SpeedSelector send={send} />
        <EmergencyBrakeButton send={send} runState={runState} speed={speed} />
        <StepButton send={send} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
};
