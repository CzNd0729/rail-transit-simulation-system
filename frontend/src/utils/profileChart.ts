import type { ProfileSegment } from '../data/mvpLineLayout';

/** 将分段参数展开为 ECharts 阶梯图坐标对 */
export function toStepData(
  segments: ProfileSegment[],
  field: keyof Pick<ProfileSegment, 'gradient' | 'speed_limit'>,
): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    result.push([seg.start_chainage, seg[field]]);
    result.push([seg.end_chainage, seg[field]]);
  }
  return result;
}
