/**
 * OverviewView — 综合视图（默认视图）
 * 基于《需求文档》3.3.1 综合视图设计
 *
 * 功能：
 * - UI-VW-01: 线路纵断面图 — 显示全线车站位置、区间、坡度示意
 * - UI-VW-02: 列车位置实时动画 — 列车图标沿线路移动
 * - UI-VW-03: 速度-位置曲线图 — 实时绘制速度随位置变化曲线
 * - UI-VW-04: 关键状态速览面板 — 4 个小卡片：当前速度、网压、工况、信号授权
 * - UI-VW-05: 子系统状态指示器 — 供电/信号/轨道/车辆各系统状态灯
 */
import CollapsiblePanel from '../components/common/CollapsiblePanel';
import LineDiagram from '../components/views/overview/LineDiagram';
import SpeedPositionCurve from '../components/views/overview/SpeedPositionCurve';
import StatusCards from '../components/views/overview/StatusCards';
import SubsystemIndicators from '../components/views/overview/SubsystemIndicators';

export default function OverviewView() {
  return (
    <div style={styles.container}>
      {/* 顶部：关键状态速览 + 子系统状态（并排） */}
      <div style={styles.topRow}>
        <StatusCards />
        <SubsystemIndicators />
      </div>

      {/* 线路图（固定大小，不可折叠） */}
      <div style={styles.lineDiagramWrapper}>
        <LineDiagram />
      </div>

      {/* 速度-位置曲线（可折叠） */}
      <CollapsiblePanel title="速度-位置曲线" icon="📊" defaultOpen={true}>
        <div style={styles.chartWrapper}>
          <SpeedPositionCurve />
        </div>
      </CollapsiblePanel>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    minHeight: '100%',
    padding: '0 4px',
  },
  topRow: {
    display: 'flex',
    gap: '12px',
    flexShrink: 0,
  },
  lineDiagramWrapper: {
    height: '350px',
    flexShrink: 0,
  },
  chartWrapper: {
    height: '300px',
    padding: '12px',
  },
};
