/**
 * CompareTable — 多方案对比表格
 * 展示各方案的指标，按5个维度分组，颜色标识优劣（绿色最优、红色最差）
 */
import React from 'react';
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

interface DimensionGroup {
  name: string;
  icon: string;
  metrics: MetricDef[];
}

const DIMENSION_GROUPS: DimensionGroup[] = [
  {
    name: '效率', icon: '⚡',
    metrics: [
      { key: 'totalTime', label: '总耗时', unit: 's', lowerIsBetter: true, decimals: 1 },
      { key: 'totalDistance', label: '总里程', unit: 'm', lowerIsBetter: false, decimals: 1 },
      { key: 'avgSpeed', label: '平均速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
      { key: 'maxSpeed', label: '最高速度', unit: 'km/h', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    name: '能耗', icon: '🔋',
    metrics: [
      { key: 'tractionEnergy', label: '牵引能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenEnergy', label: '再生电量', unit: 'kWh', lowerIsBetter: false, decimals: 1 },
      { key: 'netEnergy', label: '净能耗', unit: 'kWh', lowerIsBetter: true, decimals: 1 },
      { key: 'regenRate', label: '再生利用率', unit: '%', lowerIsBetter: false, decimals: 1 },
    ],
  },
  {
    name: '舒适度', icon: '🛋️',
    metrics: [
      { key: 'maxJerk', label: '最大冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 2 },
      { key: 'avgJerk', label: '平均冲击率', unit: 'm/s³', lowerIsBetter: true, decimals: 2 },
      { key: 'maxAccel', label: '最大加速度', unit: 'm/s²', lowerIsBetter: true, decimals: 2 },
    ],
  },
  {
    name: '安全', icon: '🛡️',
    metrics: [
      { key: 'minVoltage', label: '最低网压', unit: 'V', lowerIsBetter: false, decimals: 0 },
      { key: 'peakPower', label: '峰值功率', unit: 'kW', lowerIsBetter: true, decimals: 1 },
      { key: 'ebCount', label: '紧急制动', unit: '次', lowerIsBetter: true, decimals: 0 },
    ],
  },
  {
    name: '准点', icon: '⏱️',
    metrics: [
      { key: 'totalDelay', label: '总晚点', unit: 's', lowerIsBetter: true, decimals: 1 },
    ],
  },
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
            {DIMENSION_GROUPS.map((group) => (
              <React.Fragment key={group.name}>
                {/* 维度分组标题行 */}
                <tr>
                  <td colSpan={scenarios.length + 1} style={styles.dimHeader}>
                    {group.icon} {group.name}
                  </td>
                </tr>
                {/* 该维度的指标行 */}
                {group.metrics.map((metric) => (
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
              </React.Fragment>
            ))}
            {/* 评估窗口辅助信息行 */}
            <tr>
              <td style={styles.tdLabel}>评估窗口</td>
              {scenarios.map((s) => {
                const duration = (s.result as unknown as Record<string, number>).evaluationDuration;
                return (
                  <td key={s.id} style={{ ...styles.td, color: 'var(--text-secondary)', fontWeight: 400 }}>
                    {typeof duration === 'number' && duration > 0 ? `${duration}s` : '-'}
                  </td>
                );
              })}
            </tr>
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
  dimHeader: {
    textAlign: 'left' as const,
    padding: '8px 10px',
    borderBottom: '2px solid var(--border-color)',
    color: 'var(--text-highlight)',
    fontWeight: 700,
    fontSize: '12px',
    backgroundColor: 'rgba(42, 42, 74, 0.2)',
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
