/**
 * TrackView — 轨道视图
 * 基于《需求文档》3.3.5 轨道视图设计
 *
 * 功能：
 * - UI-TRK-01: 线路剖面图 — 坡度-距离剖面，标注车站和区间
 * - UI-TRK-02: 区段占用状态 — 轨道区段占用/空闲可视化
 * - UI-TRK-03: 道岔状态图 — 道岔定位/反位/转换中状态显示（迭代四）
 */
import LineProfileDetail from '../components/views/track/LineProfileDetail';
import OccupancyDisplay from '../components/views/track/OccupancyDisplay';
import SwitchStatus from '../components/views/track/SwitchStatus';

export default function TrackView() {
  return (
    <div style={styles.container}>
      {/* 线路剖面图 */}
      <div style={styles.profileSection}>
        <LineProfileDetail />
      </div>

      {/* 区段占用状态 + 道岔状态 */}
      <div style={styles.statusRow}>
        <div style={styles.half}>
          <OccupancyDisplay />
        </div>
        <div style={styles.half}>
          <SwitchStatus />
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
  profileSection: {
    flex: 1,
    minHeight: '300px',
  },
  statusRow: {
    display: 'flex',
    gap: '12px',
    flex: 1,
    minHeight: '200px',
  },
  half: {
    flex: 1,
  },
};
