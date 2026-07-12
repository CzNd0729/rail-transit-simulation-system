/**
 * OccupancyDisplay — SVG 轨道条带图
 * 展示全线上下行轨道电路区段占用状态 + 列车位置
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import type { TrackCircuit } from '../../../types/simulation';

function circuitColor(occupied: boolean): { fill: string; stroke: string } {
  return occupied
    ? { fill: '#4a1a1a', stroke: '#8a2a2a' }
    : { fill: '#1a3a1a', stroke: '#2a5a2a' };
}

function renderBar(
  circuits: TrackCircuit[],
  y: number,
  h: number,
) {
  return circuits.map((c) => {
    const w = c.end_chainage - c.start_chainage;
    const colors = circuitColor(c.occupied);
    return (
      <rect
        key={c.id}
        x={c.start_chainage}
        y={y}
        width={Math.max(w, 2)}
        height={h}
        rx={2}
        fill={colors.fill}
        stroke={colors.stroke}
        strokeWidth={0.5}
      >
        <title>
          {`${c.id}\n${c.start_chainage}m - ${c.end_chainage}m\n${c.occupied ? '占用' : '空闲'}`}
        </title>
      </rect>
    );
  });
}

export default function OccupancyDisplay() {
  const { trains, lineLayout, track } = useSimulationState();

  const segments = lineLayout?.segments ?? mockLineData.segments;
  const stations = lineLayout?.stations ?? mockLineData.stations;
  const total_length = lineLayout?.total_length ?? mockLineData.total_length;

  const circuits: TrackCircuit[] =
    track.occupancy.length > 0
      ? track.occupancy
      : segments.flatMap((seg) => seg.circuits);

  const downCircuits = circuits.filter((c) => c.direction === 'down');
  const upCircuits = circuits.filter((c) => c.direction === 'up');

  const downOccupied = downCircuits.filter((c) => c.occupied).length;
  const downFree = downCircuits.length - downOccupied;
  const upOccupied = upCircuits.filter((c) => c.occupied).length;
  const upFree = upCircuits.length - upOccupied;

  const trackY = 30;  // 下行条 y
  const trackH = 14;  // 条高度
  const barGap = 4;   // 两条间距
  const upY = trackY + trackH + barGap; // 上行条 y

  return (
    <div className="panel" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="panel-title">🔲 区段占用状态</div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <svg
          viewBox={`0 0 ${total_length} 120`}
          preserveAspectRatio="none"
          style={{ width: '100%', height: '100%' }}
        >
          {/* 公里标尺 */}
          {Array.from({ length: Math.ceil(total_length / 2000) + 1 }, (_, i) => i * 2000)
            .filter((pos) => pos <= total_length)
            .map((pos) => (
              <g key={`ruler-${pos}`}>
                <line x1={pos} y1={8} x2={pos} y2={14} stroke="#555" strokeWidth={1} />
                <text x={pos} y={24} textAnchor="middle" fontSize={8} fill="#888">
                  {pos}m
                </text>
              </g>
            ))}

          {/* 下行轨道电路色块 */}
          {renderBar(downCircuits, trackY, trackH)}

          {/* 上行轨道电路色块 */}
          {renderBar(upCircuits, upY, trackH)}

          {/* 站台分隔线（纵贯双条） */}
          {stations.map((s) => (
            <line
              key={`div-${s.id}`}
              x1={s.chainage} y1={trackY}
              x2={s.chainage} y2={upY + trackH}
              stroke="#666" strokeWidth={2}
              opacity={0.7}
            />
          ))}

          {/* 列车标记 */}
          {trains.map((t) => (
            <g key={t.id}>
              <rect
                x={t.position - 8} y={trackY - 10}
                width={16} height={trackH + 8}
                rx={3} fill="#ff4d4f" opacity={0.85}
              />
              <text
                x={t.position} y={trackY + 10}
                textAnchor="middle" fontSize={10} fill="#fff"
              >
                🚇
              </text>
            </g>
          ))}
        </svg>
      </div>

      {/* 分方向统计 */}
      <div style={styles.summary}>
        <span>
          ↓ 下行 <b>{downCircuits.length}</b> 区段
          <span style={{ color: '#ff4d4f' }}> ●占用 {downOccupied}</span>
          <span style={{ color: '#52c41a' }}> ●空闲 {downFree}</span>
        </span>
        <span>
          ↑ 上行 <b>{upCircuits.length}</b> 区段
          <span style={{ color: '#ff4d4f' }}> ●占用 {upOccupied}</span>
          <span style={{ color: '#52c41a' }}> ●空闲 {upFree}</span>
        </span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  summary: {
    display: 'flex',
    gap: '24px',
    padding: '6px 4px 0',
    fontSize: '11px',
    color: 'var(--text-secondary)',
    borderTop: '1px solid var(--border-color)',
    flexShrink: 0,
  },
};
