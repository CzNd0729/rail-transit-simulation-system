/**
 * 均匀降采样工具函数
 * 从超长时序数组中取 maxPoints 个均匀分布的点，保留首尾确保范围完整。
 * 用于减少传入 ECharts 的渲染数据量。
 */
export function downsample(
  data: [number, number][],
  maxPoints: number = 800,
): [number, number][] {
  if (data.length <= maxPoints) return data;
  const step = data.length / maxPoints;
  const result: [number, number][] = [];
  for (let i = 0; i < maxPoints; i++) {
    result.push(data[Math.floor(i * step)]);
  }
  // 确保最后一个数据点始终包含
  const last = data[data.length - 1];
  if (result[result.length - 1] !== last) {
    result.push(last);
  }
  return result;
}
