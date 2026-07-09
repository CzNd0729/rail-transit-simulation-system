/**
 * VehicleView — 车辆视图
 * 基于《需求文档》3.3.4 车辆视图设计
 *
 * 功能：
 * - UI-VHC-01: 速度-时间曲线 — 实时绘制速度随时间变化
 * - UI-VHC-02: 加速度-时间曲线 — 实时绘制加速度曲线
 * - UI-VHC-03: 工况指示器 — 当前工况（牵引/惰行/制动）彩色标识
 * - UI-VHC-04: 阻力分解图 — 迭代三实现
 * - UI-VHC-05: 能耗累计图 — 迭代三实现
 */
import SpeedTimeCurve from '../components/views/vehicle/SpeedTimeCurve';
import AccelTimeCurve from '../components/views/vehicle/AccelTimeCurve';
import JerkTimeCurve from '../components/views/vehicle/JerkTimeCurve';
import ModeIndicator from '../components/views/vehicle/ModeIndicator';

export default function VehicleView() {
  return (
    <div style={styles.container}>
      <div style={styles.indicatorRow}>
        <ModeIndicator />
      </div>

      <div style={{ ...styles.chartRow, flex: 1 }}>
        <div style={styles.chartHalf}>
          <SpeedTimeCurve />
        </div>
        <div style={styles.chartHalf}>
          <AccelTimeCurve />
        </div>
      </div>

      <div style={styles.jerkRow}>
        <JerkTimeCurve />
      </div>
      {/* UI-VHC-04/05: 迭代三实现，迭代一隐藏 */}
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
  indicatorRow: {
    flexShrink: 0,
  },
  chartRow: {
    display: 'flex',
    gap: '12px',
    flex: 1,
    minHeight: '200px',
  },
  chartHalf: {
    flex: 1,
  },
  jerkRow: {
    flex: '0 0 220px',
    minHeight: '180px',
  },
};
