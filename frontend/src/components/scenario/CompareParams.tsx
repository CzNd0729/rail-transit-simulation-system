/**
 * CompareParams — 方案参数对比
 * - 0 个方案：提示勾选
 * - 1 个方案：展示完整参数列表
 * - 2+ 个方案：差异对比模式（相同折叠、不同高亮）
 */
import React from 'react';
import type { ScenarioDetailResponse } from '../../types/simulation';

interface CompareParamsProps {
  scenarios: ScenarioDetailResponse[];
}

/** 参数分组定义 */
interface ParamGroup {
  name: string;
  icon: string;
  keys: string[];
  labels: Record<string, string>;
  units: Record<string, string>;
  decimals: Record<string, number>;
}

const PARAM_GROUPS: ParamGroup[] = [
  {
    name: '车辆参数', icon: '🚇',
    keys: [
      'emptyMass', 'passengerCapacity', 'maxSpeed',
      'maxTractionForce', 'maxBrakeForce',
      'davisA', 'davisB', 'davisCFrontArea',
      'davisCDragCoeff', 'curveResistCoeff', 'tunnelResistFactor',
    ],
    labels: {
      emptyMass: '空车质量', passengerCapacity: '载客量', maxSpeed: '最大速度',
      maxTractionForce: '最大牵引力', maxBrakeForce: '最大制动力',
      davisA: 'Davis A', davisB: 'Davis B', davisCFrontArea: '迎风面积',
      davisCDragCoeff: '空气阻力系数 Cd', curveResistCoeff: '弯道阻力系数',
      tunnelResistFactor: '隧道阻力系数',
    },
    units: {
      emptyMass: 'kg', passengerCapacity: '人', maxSpeed: 'km/h',
      maxTractionForce: 'N', maxBrakeForce: 'N',
      davisA: '', davisB: '', davisCFrontArea: 'm²',
      davisCDragCoeff: '', curveResistCoeff: '', tunnelResistFactor: '',
    },
    decimals: {},
  },
  {
    name: '信号参数', icon: '🚦',
    keys: ['dwellTime', 'departureInterval', 'targetSpeedRatio', 'safetyDistance', 'comfortDecel', 'maxJerk', 'evaluationTime', 'totalTime'],
    labels: {
      dwellTime: '站停时间', departureInterval: '发车间隔', targetSpeedRatio: '目标速度比',
      safetyDistance: 'ATP安全距离', comfortDecel: '舒适减速度', maxJerk: '冲击率上限',
      evaluationTime: '评估窗口', totalTime: '仿真总时长',
    },
    units: {
      dwellTime: 's', departureInterval: 's', targetSpeedRatio: '',
      safetyDistance: 'm', comfortDecel: 'm/s²', maxJerk: 'm/s³',
      evaluationTime: 's', totalTime: 's',
    },
    decimals: { targetSpeedRatio: 2, comfortDecel: 1, maxJerk: 2, evaluationTime: 0, totalTime: 0 },
  },
  {
    name: '供电参数', icon: '⚡',
    keys: ['pantographVoltage', 'substationCapacity'],
    labels: { pantographVoltage: '网压', substationCapacity: '变电所容量' },
    units: { pantographVoltage: 'V', substationCapacity: 'kW' },
    decimals: {},
  },
];

/** simulation 参数展示（按方案 JSON 实际存储字段） */
const SIM_PARAM_KEYS = ['trainCount', 'bidirectional', 'coastingMinSpeed', 'stationStopTolerance'] as const;
const SIM_PARAM_LABELS: Record<string, string> = {
  trainCount: '列车数量', bidirectional: '双向运行',
  coastingMinSpeed: '惰行最低速度', stationStopTolerance: '站台停车容忍度',
};
const SIM_PARAM_UNITS: Record<string, string> = {
  trainCount: '列', bidirectional: '', coastingMinSpeed: 'km/h', stationStopTolerance: 'm',
};

function formatParamValue(value: unknown, unit: string, decimals?: number): string {
  if (typeof value === 'number') {
    const d = decimals ?? (Number.isInteger(value) ? 0 : 1);
    const formatted = value.toFixed(d);
    return unit ? `${formatted} ${unit}` : formatted;
  }
  return String(value ?? '-');
}

/** 判断一个参数在所有方案中是否有差异 */
function hasDiff(scenarios: ScenarioDetailResponse[], group: string, key: string): boolean {
  const values = scenarios.map((s) => {
    const v = (s.params as Record<string, Record<string, unknown>>)[group]?.[key];
    return JSON.stringify(v);
  });
  return new Set(values).size > 1;
}

/** 将分组名映射到 params 对象的键 */
function mapGroupToParamKey(groupName: string): string {
  const map: Record<string, string> = {
    '车辆参数': 'vehicle',
    '信号参数': 'signal',
    '供电参数': 'power',
  };
  return map[groupName] ?? groupName;
}

export default function CompareParams({ scenarios }: CompareParamsProps) {
  if (scenarios.length === 0) {
    return (
      <div className="panel" style={styles.panel}>
        <div className="panel-title">🔧 参数对比</div>
        <div style={styles.empty}>请勾选方案查看参数</div>
      </div>
    );
  }

  const isDiffMode = scenarios.length >= 2;

  return (
    <div className="panel" style={styles.panel}>
      <div className="panel-title">
        🔧 参数对比
        {isDiffMode && <span style={{ fontSize: '11px', color: 'var(--text-secondary)', marginLeft: '8px' }}>（差异模式，相同参数已折叠）</span>}
      </div>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>参数</th>
              {scenarios.map((s) => (
                <th key={s.id} style={styles.th}>{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PARAM_GROUPS.map((group) => (
              <React.Fragment key={group.name}>
                <tr>
                  <td colSpan={scenarios.length + 1} style={styles.groupHeader}>
                    {group.icon} {group.name}
                  </td>
                </tr>
                {group.keys.map((key) => {
                  const diff = isDiffMode && hasDiff(scenarios, mapGroupToParamKey(group.name), key);
                  if (isDiffMode && !diff) return null;
                  return (
                    <tr key={key} style={diff ? { backgroundColor: 'rgba(250, 173, 20, 0.08)' } : undefined}>
                      <td style={styles.tdLabel}>
                        {group.labels[key] ?? key}
                        {diff && <span style={{ marginLeft: '4px', fontSize: '10px' }}>🔶</span>}
                      </td>
                      {scenarios.map((s) => {
                        const val = (s.params as Record<string, Record<string, unknown>>)[mapGroupToParamKey(group.name)]?.[key];
                        return (
                          <td key={s.id} style={diff ? { ...styles.td, color: 'var(--color-warning)' } : styles.td}>
                            {formatParamValue(val, group.units[key] ?? '', group.decimals[key])}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </React.Fragment>
            ))}
            {/* simulation 参数 */}
            <tr>
              <td colSpan={scenarios.length + 1} style={styles.groupHeader}>
                ⚙️ 仿真参数
              </td>
            </tr>
            {SIM_PARAM_KEYS.map((key) => {
              const diff = isDiffMode && hasDiff(scenarios, 'simulation', key);
              if (isDiffMode && !diff) return null;
              return (
                <tr key={key} style={diff ? { backgroundColor: 'rgba(250, 173, 20, 0.08)' } : undefined}>
                  <td style={styles.tdLabel}>
                    {SIM_PARAM_LABELS[key] ?? key}
                    {diff && <span style={{ marginLeft: '4px', fontSize: '10px' }}>🔶</span>}
                  </td>
                  {scenarios.map((s) => {
                    const val = (s.params as Record<string, Record<string, unknown>>).simulation?.[key];
                    return (
                      <td key={s.id} style={diff ? { ...styles.td, color: 'var(--color-warning)' } : styles.td}>
                        {formatParamValue(val, SIM_PARAM_UNITS[key] ?? '', 0)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: { marginBottom: '12px' },
  tableWrapper: { overflowX: 'auto', maxHeight: '500px', overflowY: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' },
  th: {
    textAlign: 'center', padding: '8px 10px',
    borderBottom: '1px solid var(--border-color)',
    color: 'var(--text-highlight)', fontWeight: 600, whiteSpace: 'nowrap',
  },
  td: {
    textAlign: 'center', padding: '6px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: '12px',
  },
  tdLabel: {
    textAlign: 'left', padding: '6px 10px',
    borderBottom: '1px solid rgba(42, 42, 74, 0.4)',
    color: 'var(--text-secondary)', fontWeight: 500,
  },
  groupHeader: {
    textAlign: 'left', padding: '8px 10px',
    borderBottom: '2px solid var(--border-color)',
    color: 'var(--text-highlight)', fontWeight: 700, fontSize: '12px',
    backgroundColor: 'rgba(42, 42, 74, 0.2)',
  },
  empty: { textAlign: 'center', color: 'var(--text-secondary)', fontSize: '13px', padding: '24px 0' },
};
