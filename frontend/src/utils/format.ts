/**
 * 格式化工具函数
 */

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
