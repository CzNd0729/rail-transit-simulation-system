import { useMemo } from 'react';
import { useSimulationState } from '../context/SimulationContext';
import { getTrainChartHistory } from '../utils/chartHistory';
import {
  isChartTrainLive,
  resolveChartTrainId,
} from '../utils/resolveChartTrainId';
import type { TrainChartHistory, TrainState } from '../types/simulation';

/** 解析当前选中列车；无选中或 ID 失效时回退到首车 */
export function resolveSelectedTrain(
  trains: TrainState[],
  selectedTrainId: string | null,
): TrainState | undefined {
  if (trains.length === 0) {
    return undefined;
  }
  if (selectedTrainId) {
    const found = trains.find((t) => t.id === selectedTrainId);
    if (found) {
      return found;
    }
  }
  return trains[0];
}

export function useSelectedTrain(): TrainState | undefined {
  const { trains, selectedTrainId } = useSimulationState();
  return useMemo(
    () => resolveSelectedTrain(trains, selectedTrainId),
    [trains, selectedTrainId],
  );
}

/** 曲线绑定列车 ID（全部模式优先最早发车历史） */
export function useActiveChartTrainId(): string {
  const { chartHistory, trains, selectedTrainId } = useSimulationState();
  return resolveChartTrainId(chartHistory, trains, selectedTrainId);
}

/** 选中列车对应的曲线历史（车辆/信号详情视图） */
export function useActiveChartHistory(): TrainChartHistory {
  const { chartHistory, trains, selectedTrainId, chartVersion } = useSimulationState();
  const trainId = resolveChartTrainId(chartHistory, trains, selectedTrainId);
  return useMemo(
    () => getTrainChartHistory(chartHistory, trainId),
    // chartVersion：可变 push 后引用不变，靠版本号驱动刷新
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [chartHistory, trainId, chartVersion],
  );
}

/** 时间轴是否跟随全局 clock（离线车为 false） */
export function useChartFollowClock(): boolean {
  const { trains } = useSimulationState();
  const trainId = useActiveChartTrainId();
  return isChartTrainLive(trains, trainId);
}
