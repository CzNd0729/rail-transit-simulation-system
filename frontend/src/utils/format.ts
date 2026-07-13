/**
 * 格式化工具函数
 */

/**
 * 统一数值格式化，保留指定位数小数（默认 2 位）
 * 用于图表 tooltip、轴标签等显示
 */
export function formatNum(value: number, decimals = 2): string {
  return value.toFixed(decimals);
}

/** 车辆视图图表轴 / tooltip 默认小数位（十分位） */
export const VEHICLE_CHART_DECIMALS = 1;

/** ECharts 轴标签格式化，默认车辆视图十分位 */
export function formatAxisLabel(
  value: number,
  decimals = VEHICLE_CHART_DECIMALS,
): string {
  return value.toFixed(decimals);
}

/** 时间轴 max 取整到十分位，避免浮点噪声轴标签 */
export function stableVehicleTimeMax(
  elapsed: number,
  lastTime?: number,
  minMax = 600,
): number {
  const raw = Math.max(elapsed + 10, (lastTime ?? 0) + 10, minMax);
  return Math.round(raw * 10) / 10;
}

/**
 * ECharts axis-trigger tooltip formatter：将所有数值格式化为指定位数小数
 * 适用于 trigger: 'axis' 的折线图
 * @param decimals 小数位数，默认 2
 */
export function axisTooltip(decimals = 2) {
  return (params: any) => {
    const list = Array.isArray(params) ? params : [params];
    const rawAxis = list[0]?.axisValue;
    const axisVal = typeof rawAxis === 'number'
      ? formatNum(rawAxis, decimals)
      : (list[0]?.axisValueLabel ?? '');
    const body = list
      .map((p: any) => {
        const yVal = Array.isArray(p.value) ? p.value[1] : p.value;
        return `${p.marker} ${p.seriesName}: ${formatNum(yVal, decimals)}`;
      })
      .join('<br/>');
    return axisVal ? `${axisVal}<br/>${body}` : body;
  };
}

/**
 * 格式化仿真时间为 HH:MM:SS 格式
 * @param seconds 秒数
 */
export function formatSimTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
}

/**
 * 格式化速度显示 (km/h)
 */
export function formatSpeed(speed: number): string {
  return `${speed.toFixed(1)} km/h`;
}

/**
 * 格式化距离/公里标 (m)
 */
export function formatDistance(meters: number): string {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(2)} km`;
  }
  return `${meters.toFixed(1)} m`;
}

/**
 * 格式化电压 (V)
 */
export function formatVoltage(voltage: number): string {
  return `${voltage.toFixed(0)} V`;
}

/**
 * 格式化功率 (kW)
 */
export function formatPower(power: number): string {
  if (Math.abs(power) >= 1000) {
    return `${(power / 1000).toFixed(2)} MW`;
  }
  return `${power.toFixed(1)} kW`;
}

/**
 * 格式化能耗 (kWh)
 */
export function formatEnergy(energy: number): string {
  return `${energy.toFixed(2)} kWh`;
}

/**
 * 工况中文标签
 */
export function getModeLabel(mode: string): string {
  const labels: Record<string, string> = {
    traction: '牵引',
    coasting: '惰行',
    braking: '制动',
    stopped: '停稳',
    dwell: '站停',
  };
  return labels[mode] || mode;
}

/** 信号运行相位中文标签 */
export function getSignalPhaseLabel(phase: string): string {
  const labels: Record<string, string> = {
    traction: '牵引',
    coasting: '惰行',
    braking: '制动',
    dwell: '站停',
  };
  return labels[phase] ?? phase;
}

/**
 * 解析当前信号相位：优先后端 runningPhase，否则从列车状态推导
 */
export function resolveSignalPhase(
  runningPhase: string | undefined,
  trainMode: string | undefined,
  tractionLevel = 0,
  brakeLevel = 0,
): string {
  if (runningPhase) return runningPhase;
  if (trainMode === 'stopped' || trainMode === 'dwell') return 'dwell';
  if (brakeLevel > 0.01) return 'braking';
  if (tractionLevel > 0.01) return 'traction';
  return trainMode ?? 'coasting';
}

/**
 * 根据列车状态与信号相位推导展示工况
 */
export function getDisplayMode(
  mode: string | undefined,
  speed: number,
  runningPhase?: string,
): string {
  if (runningPhase === 'dwell') return 'stopped';
  if (mode === 'stopped') return 'stopped';
  if (mode === 'coasting' && speed < 0.5) return 'stopped';
  return mode ?? 'coasting';
}

/**
 * 工况颜色映射
 */
export function getModeColor(mode: string): string {
  const colors: Record<string, string> = {
    traction: '#52c41a',   // 绿色
    coasting: '#faad14',   // 黄色
    braking: '#ff4d4f',    // 红色
    stopped: '#8c8c8c',    // 灰色
  };
  return colors[mode] || '#999';
}

/**
 * 状态灯颜色：正常/警告/故障
 */
export function getStatusColor(status: 'normal' | 'warning' | 'error'): string {
  const colors: Record<string, string> = {
    normal: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
  };
  return colors[status] || '#999';
}

/** 数字补零到两位 */
function pad(n: number): string {
  return n.toString().padStart(2, '0');
}
