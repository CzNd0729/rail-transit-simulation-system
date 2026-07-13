import { formatAxisLabel, VEHICLE_CHART_DECIMALS } from './format';

const AXIS_LABEL_COLOR = '#a0a0a0';

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
