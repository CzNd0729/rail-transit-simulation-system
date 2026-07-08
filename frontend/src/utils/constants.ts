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
} as const;
