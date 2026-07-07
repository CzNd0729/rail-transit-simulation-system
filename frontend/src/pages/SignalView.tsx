/**
 * SignalView — 信号视图
 * 基于《需求文档》3.3.3 信号视图设计
 *
 * 功能：
 * - UI-SIG-01: 移动授权（MA）示意图 — 显示各列车安全包络和追踪间隔
 * - UI-SIG-02: 速度包络线 — ATP 紧急制动触发曲线 vs 实际运行曲线
 * - UI-SIG-03: 运行图（时间-距离图）— 多列车时空轨迹绘制
 * - UI-SIG-04: 联锁状态表 — 进路/道岔/信号机状态列表（迭代四）
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
