import { formatAxisLabel, VEHICLE_CHART_DECIMALS } from './format';
import type { RunState } from '../types/simulation';

const AXIS_LABEL_COLOR = '#a0a0a0';

/** 仿真未启动：隐藏 x 轴竖向网格，保留坐标轴框架 */
export function xAxisSplitLineForRunState(runState: RunState) {
  return { show: runState !== 'idle' };
}

/** 车辆视图时间轴标签样式 */
export function vehicleTimeAxisLabel() {
  return {
    color: AXIS_LABEL_COLOR,
    formatter: (value: number) => formatAxisLabel(value),
  };
}

/** 车辆视图数值轴标签样式 */
export function vehicleValueAxisLabel(decimals = VEHICLE_CHART_DECIMALS) {
  return {
    color: AXIS_LABEL_COLOR,
    formatter: (value: number) => formatAxisLabel(value, decimals),
  };
}

export { VEHICLE_CHART_DECIMALS };
