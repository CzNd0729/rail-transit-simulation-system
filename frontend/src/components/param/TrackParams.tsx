/**
 * TrackParams — 线路参数编辑表单
 * 基于《需求文档》UI-PARAM-02
 */
import { useSimulationState } from '../../context/SimulationContext';
import { useSimulation } from '../../hooks/useSimulation';
import ParamStepper from './ParamStepper';
import {
  TRACK_PARAM_STEP_KEYS,
  computeFixedParamStep,
  type TrackParamStepKey,
} from '../../utils/paramStep';

interface Props {
  send: (data: object) => void;
}

const PARAM_LABELS: Record<TrackParamStepKey, string> = {
  gradient: '坡度 (‰)',
  curvature: '曲率半径 (m)',
  speed_limit: '限速 (km/h)',
};

export default function TrackParamsForm({ send }: Props) {
  const { params, trackParamBaselines } = useSimulationState();
  const { updateParams } = useSimulation(send);

  const handleChange = (key: TrackParamStepKey, value: number) => {
    updateParams({ track: { ...params.track, [key]: value } });
  };

  return (
    <fieldset style={styles.fieldset}>
      <legend style={styles.legend}>🛤️ 线路参数</legend>
      {TRACK_PARAM_STEP_KEYS.map((key) => {
        const baseline = trackParamBaselines[key] ?? params.track[key] ?? 0;
        return (
          <ParamStepper
            key={key}
            label={PARAM_LABELS[key]}
            value={params.track[key]}
            step={computeFixedParamStep(baseline)}
            onChange={(v) => handleChange(key, v)}
          />
        );
      })}
    </fieldset>
  );
}

const styles: Record<string, React.CSSProperties> = {
  fieldset: {
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: '8px',
  },
  legend: {
    fontSize: '12px',
    color: 'var(--text-highlight)',
    padding: '0 4px',
  },
};
