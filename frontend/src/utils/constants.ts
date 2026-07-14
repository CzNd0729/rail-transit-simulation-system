/**
 * 常量定义
 */

/** WebSocket 重连间隔 (ms) */
export const WS_RECONNECT_INTERVAL = 2000;

/** 默认后端地址 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws';

/** 速度倍率选项 */
export const SPEED_MULTIPLIER_OPTIONS = [1, 5, 10] as const;

/** 速度倍率 SVG 矢量图标（紧凑重叠快进三角，连体字形） */
export const SPEED_ICONS: Record<number, string> = {
  1: `<svg width="10" height="12" viewBox="0 0 10 12"><path d="M1 0l8 6-8 6z" fill="currentColor"/></svg>`,
  5: `<svg width="16" height="12" viewBox="0 0 16 12"><path d="M1 0l9 6-9 6z" fill="currentColor" opacity=".9"/><path d="M7 0l9 6-9 6z" fill="currentColor"/></svg>`,
  10: `<svg width="16" height="12" viewBox="0 0 16 12"><path d="M1 0l6 6-6 6z" fill="currentColor" opacity=".7"/><path d="M6 0l6 6-6 6z" fill="currentColor" opacity=".9"/><path d="M11 0l5 6-5 6z" fill="currentColor"/></svg>`,
};

/** 速度倍率显示：返回 SVG 或回退文字 */
export function formatSpeedMultiplier(m: number): string {
  return SPEED_ICONS[m] || `${m}×`;
}

/** 是否使用 Mock 回放模式（预录 JSON 数据） */
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/** 默认固定网压 (V) */
export const DEFAULT_PANTOGRAPH_VOLTAGE = 1500;

/** 仿真状态中文标签 */
export const RUN_STATE_LABELS: Record<string, string> = {
  idle: '空闲',
  running: '运行中',
  paused: '已暂停',
  stopped: '已停止',
};

/** 视图配置 */
export const VIEW_CONFIG = {
  overview: { label: '综合视图', icon: '🏠' },
  power: { label: '供电视图', icon: '⚡' },
  signal: { label: '信号视图', icon: '🚦' },
  vehicle: { label: '车辆视图', icon: '🚇' },
  track: { label: '轨道视图', icon: '🛤️' },
  scenario: { label: '方案对比', icon: '📊' },
} as const;

/** 多车标识配色：红 / 黄 / 蓝（高对比，按 TRAIN_01 起顺序） */
export const TRAIN_CHART_COLORS = [
  '#ff4d4f',
  '#fadb14',
  '#1890ff',
  '#eb2f96',
  '#722ed1',
  '#13c2c2',
] as const;

export function trainColorByIndex(index: number): string {
  return TRAIN_CHART_COLORS[index % TRAIN_CHART_COLORS.length];
}

/** 迭代二 MA 示意图固定安全包络长度 (m)，迭代三改为动态 ATP 包络 */
export const MA_ENVELOPE_LENGTH = 300;

/** Mock MVP 线路全长 (m)，与 mockTrackBlueprint 一致 */
export const MOCK_LINE_TOTAL_LENGTH = 3200;
