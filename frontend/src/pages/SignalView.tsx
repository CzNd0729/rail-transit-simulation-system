/**
 * SignalView — 信号视图（迭代二单车简化版）
 *
 * - UI-SIG-01: 移动授权示意图 — 列车位置 + 固定 300m 安全包络 + 目标站台
 * - UI-SIG-02: 速度包络线 — 区段限速 + 目标速度 + 实际速度
 * - UI-SIG-03: 运行图 — 单列车时间-距离轨迹
 * - UI-SIG-04~06: 留待迭代三/四
 */
import MAChart from '../components/views/signal/MAChart';
import SpeedEnvelope from '../components/views/signal/SpeedEnvelope';
import TimetableChart from '../components/views/signal/TimetableChart';

export default function SignalView() {
  return (
    <div style={styles.container}>
      {/* 移动授权示意图 */}
      <div style={styles.row}>
        <MAChart />
      </div>

      {/* 速度包络线 + 运行图 */}
      <div style={styles.row}>
        <div style={styles.half}>
          <SpeedEnvelope />
        </div>
        <div style={styles.half}>
          <TimetableChart />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    height: '100%',
  },
  row: {
    display: 'flex',
    gap: '12px',
    flex: 1,
    minHeight: '200px',
  },
  half: {
    flex: 1,
  },
};
