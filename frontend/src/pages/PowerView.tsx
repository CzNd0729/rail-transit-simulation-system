/**
 * PowerView — 供电视图
 * 基于《需求文档》3.3.2 供电视图设计
 *
 * 功能：
 * - UI-PWR-01: 接触网电压分布图 — 全线电压曲线，标示变电所位置
 * - UI-PWR-02: 变电所状态面板 — 各变电所输出电流/功率/能耗
 * - UI-PWR-03: 再生制动能量流向 — 可视化当前能量回馈路径（迭代四）
 */
import VoltageProfile from '../components/views/power/VoltageProfile';
import SubstationPanel from '../components/views/power/SubstationPanel';

export default function PowerView() {
  return (
    <div style={styles.container}>
      {/* 接触网电压分布图 */}
      <div style={styles.chartSection}>
        <VoltageProfile />
      </div>

      {/* 变电所状态面板 */}
      <div style={styles.panelSection}>
        <SubstationPanel />
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
  chartSection: {
    flex: 1,
    minHeight: '300px',
  },
  panelSection: {
    flex: 1,
    overflow: 'auto',
  },
};
