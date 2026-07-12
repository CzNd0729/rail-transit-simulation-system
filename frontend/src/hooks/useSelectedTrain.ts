import { useMemo } from 'react';
import { useSimulationState } from '../context/SimulationContext';
import { getTrainChartHistory } from '../utils/chartHistory';
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

/** 选中列车对应的曲线历史（车辆/信号详情视图） */
export function useActiveChartHistory(): TrainChartHistory {
  const { chartHistory, trains, selectedTrainId } = useSimulationState();
  const train = resolveSelectedTrain(trains, selectedTrainId);
  return useMemo(
    () => getTrainChartHistory(chartHistory, train?.id ?? 'TRAIN_01'),
    [chartHistory, train?.id],
  );
}
