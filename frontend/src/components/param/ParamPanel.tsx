/**
 * ParamPanel — 参数配置面板
 * 基于《需求文档》3.4.2 参数配置区设计
 *
 * 功能：
 * - UI-PARAM-01: 车辆参数编辑
 * - UI-PARAM-02: 线路参数编辑
 * - UI-PARAM-05: 参数重置为默认值
 * - UI-PARAM-03: 供电参数编辑（迭代二，部分）
 * - UI-PARAM-04: 信号参数编辑（迭代二）
 * - UI-PARAM-06: 参数预设方案保存/加载（迭代二，待实现）
 */
import { useSimulationState } from '../../context/SimulationContext';
import VehicleParamsForm from './VehicleParams';
import PowerParamsForm from './PowerParams';
import SignalParamsForm from './SignalParams';
import EvaluationParamsForm from './EvaluationParams';

interface Props {
  send: (data: object) => void;
}

export default function ParamPanel({ send }: Props) {
  const { runState } = useSimulationState();
  const locked = runState === 'running';

  return (
    <div className="panel">
      <div className="panel-title">⚙️ 参数配置</div>
      {locked && (
        <div style={styles.lockBanner}>仿真运行中，请先暂停或停止后再修改参数</div>
      )}
      <div style={{ ...styles.content, ...(locked ? styles.contentLocked : {}) }}>
        <EvaluationParamsForm send={send} disabled={locked} />
        <VehicleParamsForm send={send} disabled={locked} />
        <PowerParamsForm send={send} disabled={locked} />
        <SignalParamsForm send={send} disabled={locked} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  lockBanner: {
    fontSize: '11px',
    color: 'var(--color-warning)',
    backgroundColor: 'rgba(250, 173, 20, 0.1)',
    border: '1px solid var(--color-warning)',
    borderRadius: '4px',
    padding: '6px 8px',
    marginBottom: '8px',
    lineHeight: 1.4,
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  contentLocked: {
    opacity: 0.55,
    pointerEvents: 'none',
    userSelect: 'none',
  },
};
