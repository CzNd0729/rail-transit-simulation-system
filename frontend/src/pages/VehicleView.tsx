/**
 * VehicleView — 车辆视图
 * 基于《需求文档》3.3.4 车辆视图设计
 *
 * 功能：
 * - UI-VHC-01: 速度-时间曲线 — 实时绘制速度随时间变化
 * - UI-VHC-02: 加速度-时间曲线 — 实时绘制加速度曲线
 * - UI-VHC-03: 工况指示器 — 当前工况（牵引/惰行/制动）彩色标识
 * - UI-VHC-04: 总阻力-时间曲线（默认），可切换四分项堆叠
 * - UI-VHC-05: 能耗累计图 — 牵引/再生累计 kWh
 */
import SpeedTimeCurve from '../components/views/vehicle/SpeedTimeCurve';
import AccelTimeCurve from '../components/views/vehicle/AccelTimeCurve';
import JerkTimeCurve from '../components/views/vehicle/JerkTimeCurve';
import ModeIndicator from '../components/views/vehicle/ModeIndicator';
import ResistanceChart from '../components/views/vehicle/ResistanceChart';
import EnergyChart from '../components/views/vehicle/EnergyChart';

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

      <div style={styles.secondaryRow}>
        <div style={styles.chartHalf}>
          <ResistanceChart />
        </div>
        <div style={styles.chartHalf}>
          <EnergyChart />
        </div>
      </div>

      <div style={styles.jerkRow}>
        <JerkTimeCurve />
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
    minHeight: 0,
  },
  indicatorRow: {
    flexShrink: 0,
  },
  chartRow: {
    display: 'flex',
    gap: '12px',
    flex: 1,
    minHeight: '180px',
  },
  secondaryRow: {
    display: 'flex',
    gap: '12px',
    flex: '0 0 200px',
    minHeight: '160px',
  },
  chartHalf: {
    flex: 1,
    minWidth: 0,
    minHeight: 0,
  },
  jerkRow: {
    flex: '0 0 180px',
    minHeight: '140px',
  },
};
