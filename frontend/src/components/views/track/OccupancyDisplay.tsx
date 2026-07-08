/**
 * OccupancyDisplay — SVG 轨道条带图
 * 展示全线轨道电路区段占用状态 + 列车位置
 */
import { useState, useEffect, useMemo } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import type { TrackCircuit } from '../../../types/simulation';

function circuitColor(occupied: boolean): { fill: string; stroke: string } {
  return occupied
    ? { fill: '#4a1a1a', stroke: '#8a2a2a' }
    : { fill: '#1a3a1a', stroke: '#2a5a2a' };
}

export default function OccupancyDisplay() {
  const { trains } = useSimulationState();
  const { segments, stations, total_length } = mockLineData;

  const flatCircuits: TrackCircuit[] = useMemo(
    () => segments.flatMap((seg) => seg.circuits),
    [segments]
  );

  const [circuits, setCircuits] = useState<TrackCircuit[]>(flatCircuits);

  // 每 500ms 随机翻转 1-3 个电路状态
  useEffect(() => {
    if (flatCircuits.length === 0) return;
    const id = setInterval(() => {
      setCircuits((prev) => {
        const updated = [...prev];
        const count = 1 + Math.floor(Math.random() * 3);
        for (let i = 0; i < count; i++) {
          const idx = Math.floor(Math.random() * updated.length);
          updated[idx] = { ...updated[idx], occupied: !updated[idx].occupied };
        }
        return updated;
      });
    }, 500);
    return () => clearInterval(id);
  }, [flatCircuits.length]);

  const trackY = 35;
  const trackH = 16;

  const occupiedCount = circuits.filter((c) => c.occupied).length;
  const freeCount = circuits.length - occupiedCount;

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
          {Array.from({ length: 7 }, (_, i) => i * 2000).map((pos) => (
            <g key={`ruler-${pos}`}>
              <line x1={pos} y1={8} x2={pos} y2={14} stroke="#555" strokeWidth={1} />
              <text x={pos} y={24} textAnchor="middle" fontSize={8} fill="#888">
                {pos}m
              </text>
            </g>
          ))}

          {/* 轨道电路色块 */}
          {circuits.map((c) => {
            const w = c.end_chainage - c.start_chainage;
            const colors = circuitColor(c.occupied);
            return (
              <rect
                key={c.id}
                x={c.start_chainage}
                y={trackY}
                width={Math.max(w, 2)}
                height={trackH}
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
          })}

          {/* 车站标签 */}
          {stations.map((s) => (
            <g key={s.id}>
              <line
                x1={s.chainage} y1={trackY + trackH + 2}
                x2={s.chainage} y2={trackY + trackH + 12}
                stroke="#555" strokeWidth={1}
              />
              <text
                x={s.chainage} y={trackY + trackH + 24}
                textAnchor="middle" fontSize={8} fill="#ccc"
              >
                {s.name}
              </text>
            </g>
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

      {/* 统计描述 */}
      <div style={styles.summary}>
        <span>总计 <b>{circuits.length}</b> 个区段</span>
        <span style={{ color: '#ff4d4f' }}>
          ● 占用 <b>{occupiedCount}</b>
        </span>
        <span style={{ color: '#52c41a' }}>
          ● 空闲 <b>{freeCount}</b>
        </span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  summary: {
    display: 'flex',
    gap: '16px',
    padding: '6px 4px 0',
    fontSize: '11px',
    color: 'var(--text-secondary)',
    borderTop: '1px solid var(--border-color)',
    flexShrink: 0,
  },
};
