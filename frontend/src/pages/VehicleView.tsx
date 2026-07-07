/**
 * VehicleView — 车辆视图
 * 基于《需求文档》3.3.4 车辆视图设计
 *
 * 功能：
 * - UI-VHC-01: 速度-时间曲线 — 实时绘制速度随时间变化
 * - UI-VHC-02: 加速度-时间曲线 — 实时绘制加速度曲线
 * - UI-VHC-03: 工况指示器 — 当前工况（牵引/惰行/制动）彩色标识
 * - UI-VHC-04: 阻力分解图 — 堆叠面积图或柱状图，展示各阻力分量占比
 * - UI-VHC-05: 能耗累计图 — 牵引能耗/再生制动电量的累计柱状图
 */
import SpeedTimeCurve from '../components/views/vehicle/SpeedTimeCurve';
import AccelTimeCurve from '../components/views/vehicle/AccelTimeCurve';
import ModeIndicator from '../components/views/vehicle/ModeIndicator';
import ResistanceChart from '../components/views/vehicle/ResistanceChart';
import EnergyChart from '../components/views/vehicle/EnergyChart';

export default function VehicleView() {
  return (
    <div style={styles.container}>
      {/* 工况指示器 */}
      <div style={styles.indicatorRow}>
        <ModeIndicator />
      </div>

      {/* 速度-时间曲线 + 加速度-时间曲线 */}
      <div style={styles.chartRow}>
        <div style={styles.chartHalf}>
          <SpeedTimeCurve />
        </div>
        <div style={styles.chartHalf}>
          <AccelTimeCurve />
        </div>
      </div>

      {/* 阻力分解图 + 能耗累计图 */}
      <div style={styles.chartRow}>
        <div style={styles.chartHalf}>
          <ResistanceChart />
        </div>
        <div style={styles.chartHalf}>
          <EnergyChart />
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
};
