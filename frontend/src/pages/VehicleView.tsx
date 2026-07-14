/**
 * VehicleView — 车辆视图
 */
import SpeedTimeCurve from '../components/views/vehicle/SpeedTimeCurve';
import AccelTimeCurve from '../components/views/vehicle/AccelTimeCurve';
import JerkTimeCurve from '../components/views/vehicle/JerkTimeCurve';
import ModeIndicator from '../components/views/vehicle/ModeIndicator';
import ResistanceChart from '../components/views/vehicle/ResistanceChart';
import EnergyChart from '../components/views/vehicle/EnergyChart';
import { ChartLifecycleProvider } from '../components/common/ChartLifecycleContext';

export default function VehicleView({ active = true }: { active?: boolean }) {
  return (
    <ChartLifecycleProvider active={active}>
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
    </ChartLifecycleProvider>
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
