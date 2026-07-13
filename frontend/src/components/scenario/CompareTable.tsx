/**
 * CompareTable — 多方案对比表格
 * 展示各方案的指标，颜色标识优劣（绿色最优、红色最差）
 */
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareTableProps {
  scenarios: ScenarioDetailResponse[];
}

interface MetricDef {
  key: string;
  label: string;
  unit: string;
  /** true = 值越小越好 */
  lowerIsBetter: boolean;
  decimals: number;
}

const METRICS: MetricDef[] = [
  { key: 'totalTime', label: '总耗时', unit: 's', lowerIsBetter: true, decimals: 1 },
  { key: 'totalDistance', label: '总里程', unit: 'm', lowerIsBetter: false, decimals: 1 },
  { key: 'avgSpeed', label: '平均速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
  { key: 'maxSpeed', label: '最高速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
  { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
  { key: 'regenEnergy', label: '再生电量', unit: 'kWh', lowerIsBetter: false, decimals: 1 },
  { key: 'netEnergy', label: '净能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
  { key: 'minVoltage', label: '最低网压', unit: 'V', lowerIsBetter: false, decimals: 0 },
  { key: 'peakPower', label: '峰值功率', unit: 'kW', lowerIsBetter: true, decimals: 1 },
];

export default function CompareTable({ scenarios }: CompareTableProps) {
  if (scenarios.length < 2) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">📊 指标对比</div>
        <div style={styles.empty}>请勾选至少 2 个方案进行对比</div>
      </div>
    );
  }

  /** 计算每个指标在所有方案中的最优/最差值 */
  const getCellStyle = (metric: MetricDef, value: number): React.CSSProperties => {
    const allValues = scenarios.map((s) => {
      const v = (s.result as unknown as Record<string, number>)[metric.key];
      return typeof v === 'number' ? v : 0;
    });
    const best = metric.lowerIsBetter ? Math.min(...allValues) : Math.max(...allValues);
    const worst = metric.lowerIsBetter ? Math.max(...allValues) : Math.min(...allValues);

    if (allValues.every((v) => v === allValues[0])) return {};

    if (value === best) {
      return { color: 'var(--color-success)', fontWeight: 700 };
    }
    if (value === worst) {
      return { color: 'var(--color-error)', fontWeight: 700 };
    }
    return {};
  };

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">📊 指标对比</div>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>指标</th>
              {scenarios.map((s) => (
                <th key={s.id} style={styles.th}>{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METRICS.map((metric) => (
              <tr key={metric.key}>
                <td style={styles.tdLabel}>{metric.label}</td>
                {scenarios.map((s) => {
                  const raw = (s.result as unknown as Record<string, number>)[metric.key];
                  const value = typeof raw === 'number' ? raw : 0;
                  const cellStyle = getCellStyle(metric, value);
                  return (
                    <td key={s.id} style={{ ...styles.td, ...cellStyle }}>
                      {value.toFixed(metric.decimals)} {metric.unit}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={styles.legend}>
        <span style={{ color: 'var(--color-success)' }}>● 最优</span>
        <span style={{ color: 'var(--color-error)' }}>● 最差</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    marginBottom: '12px',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '12px',
  },
  th: {
    textAlign: 'center',
    padding: '8px 10px',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-highlight)',
    fontWeight: 600,
    whiteSpace: 'nowrap',
  },
  td: {
    textAlign: 'center',
    padding: '7px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-primary)',
    fontFamily: 'monospace',
    fontSize: '12px',
    transition: 'color 0.2s',
  },
  tdLabel: {
    textAlign: 'left',
    padding: '7px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  empty: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    fontSize: '13px',
    padding: '24px 0',
  },
  legend: {
    display: 'flex',
    gap: '16px',
    marginTop: '8px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
};
