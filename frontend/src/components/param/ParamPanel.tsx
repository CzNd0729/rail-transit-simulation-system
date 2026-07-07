/**
 * ParamPanel — 参数配置面板
 * 基于《需求文档》3.4.2 参数配置区设计
 *
 * 功能：
 * - UI-PARAM-01: 车辆参数编辑
 * - UI-PARAM-02: 线路参数编辑
 * - UI-PARAM-05: 参数重置为默认值
 * - UI-PARAM-03: 供电参数编辑（迭代三）
 * - UI-PARAM-04: 信号参数编辑（迭代三）
 * - UI-PARAM-06: 参数预设方案保存/加载（迭代三）
 */
import VehicleParamsForm from './VehicleParams';
import TrackParamsForm from './TrackParams';
import PowerParamsForm from './PowerParams';
import SignalParamsForm from './SignalParams';
import PresetManager from './PresetManager';

interface Props {
  send: (data: object) => void;
}

export default function ParamPanel({ send }: Props) {
  return (
    <div className="panel">
      <div className="panel-title">⚙️ 参数配置</div>
      <div style={styles.content}>
        <VehicleParamsForm send={send} />
        <TrackParamsForm send={send} />
        <PowerParamsForm send={send} />
        <SignalParamsForm send={send} />
        <PresetManager />
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
