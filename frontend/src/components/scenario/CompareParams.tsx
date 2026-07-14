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
      'empty_mass', 'passenger_capacity', 'max_speed',
      'max_traction_force', 'max_brake_force',
      'davis_A', 'davis_B', 'davis_C_front_area',
      'davis_C_drag_coeff', 'curve_resist_coeff', 'tunnel_resist_factor',
    ],
    labels: {
      empty_mass: '空车质量', passenger_capacity: '载客量', max_speed: '最大速度',
      max_traction_force: '最大牵引力', max_brake_force: '最大制动力',
      davis_A: 'Davis A', davis_B: 'Davis B', davis_C_front_area: '迎风面积',
      davis_C_drag_coeff: '空气阻力系数 Cd', curve_resist_coeff: '弯道阻力系数',
      tunnel_resist_factor: '隧道阻力系数',
    },
    units: {
      empty_mass: 'kg', passenger_capacity: '人', max_speed: 'km/h',
      max_traction_force: 'N', max_brake_force: 'N',
      davis_A: '', davis_B: '', davis_C_front_area: 'm²',
      davis_C_drag_coeff: '', curve_resist_coeff: '', tunnel_resist_factor: '',
    },
    decimals: {},
  },
  {
    name: '信号参数', icon: '🚦',
    keys: ['dwell_time', 'departure_interval', 'target_speed_ratio', 'safety_distance', 'comfort_decel', 'max_jerk'],
    labels: {
      dwell_time: '站停时间', departure_interval: '发车间隔', target_speed_ratio: '目标速度比',
      safety_distance: 'ATP安全距离', comfort_decel: '舒适减速度', max_jerk: '冲击率上限',
    },
    units: {
      dwell_time: 's', departure_interval: 's', target_speed_ratio: '',
      safety_distance: 'm', comfort_decel: 'm/s²', max_jerk: 'm/s³',
    },
    decimals: { target_speed_ratio: 2, comfort_decel: 1, max_jerk: 2 },
  },
  {
    name: '供电参数', icon: '⚡',
    keys: ['pantograph_voltage', 'substation_capacity'],
    labels: { pantograph_voltage: '网压', substation_capacity: '变电所容量' },
    units: { pantograph_voltage: 'V', substation_capacity: 'kW' },
    decimals: {},
  },
];

/** simulation 参数展示 */
const SIM_PARAM_KEYS = ['totalTime', 'evaluationTime', 'coastingMinSpeed', 'stationStopTolerance'] as const;
const SIM_PARAM_LABELS: Record<string, string> = {
  totalTime: '仿真总时长', evaluationTime: '评估窗口',
  coastingMinSpeed: '惰行最低速度', stationStopTolerance: '站台停车容忍度',
};
const SIM_PARAM_UNITS: Record<string, string> = {
  totalTime: 's', evaluationTime: 's', coastingMinSpeed: 'km/h', stationStopTolerance: 'm',
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
