/**
 * ControlPanel — 仿真控制面板
 * 基于《需求文档》3.4.1 仿真控制区设计
 *
 * 功能：
 * - UI-CTRL-01: 运行/暂停/停止按钮
 * - UI-CTRL-02: 仿真速度倍率选择器 (1× / 5× / 10×)
 */
import RunControlButtons from './RunControlButtons';
import SpeedSelector from './SpeedSelector';
import { useSimulationState, useSimulationDispatch } from '../../context/SimulationContext';

interface Props {
  send: (data: object) => void;
}

export default function ControlPanel({ send }: Props) {
  const dispatch = useSimulationDispatch();
  const { evaluationComplete } = useSimulationState();

  return (
    <div className="panel">
      <div className="panel-title">🎮 仿真控制</div>
      {evaluationComplete && (
        <div style={styles.evalNotice}>
          <span>🟢 评估完成 ({evaluationComplete.evaluationTime}s)</span>
          <span style={{ marginLeft: '4px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            方案已自动保存
          </span>
          <button
            className="btn"
            style={{ marginLeft: 'auto', fontSize: '11px', padding: '1px 6px' }}
            onClick={() => dispatch({ type: 'SET_EVALUATION_COMPLETE', payload: null })}
          >
            ✕
          </button>
        </div>
      )}
      <div style={styles.content}>
        <RunControlButtons send={send} />
        <SpeedSelector send={send} />
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
  evalNotice: {
    display: 'flex',
    alignItems: 'center',
    padding: '6px 10px',
    marginBottom: '8px',
    backgroundColor: 'rgba(82, 196, 26, 0.12)',
    border: '1px solid var(--color-success)',
    borderRadius: 'var(--border-radius)',
    fontSize: '12px',
    color: 'var(--color-success)',
    flexShrink: 0,
  },
};
