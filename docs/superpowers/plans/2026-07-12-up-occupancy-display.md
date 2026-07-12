# 区段占用状态栏上行展示条 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 OccupancyDisplay 组件中新增上行轨道电路区段展示条，与下行条上下并排显示。

**Architecture:** 后端 track.yaml 新增 23 个上行区段（与下行公里标一致），前端按 direction 字段拆分 circuits 为上下行两组，SVG 渲染双条共用标尺和车站标签，底部统计分方向显示。

**Tech Stack:** Python (YAML config), TypeScript + React + SVG

## Global Constraints

- 上行区段公里标与下行完全一致，仅 `direction: "up"`
- 两条色块条上下并排，共用同一套公里标尺和车站标签
- 底部统计拆为下行/上行两行，各行独立显示区段数/占用/空闲
- 颜色方案不变：占用 = `#4a1a1a/#8a2a2a`，空闲 = `#1a3a1a/#2a5a2a`

---

### Task 1: 后端新增上行轨道电路区段

**Files:**
- Modify: `backend/sim_engine/config/track.yaml:267`

**Interfaces:**
- Consumes: 现有 Track 模型加载逻辑（`config.py` 中 `switches` 列表解析）
- Produces: 23 个上行 `TrackCircuit` 对象（`TC01U-TC23U`），direction="up"

- [ ] **Step 1: 在 track.yaml 的 track_circuits 列表末尾添加上行区段**

在 `backend/sim_engine/config/track.yaml` 的最后一个下行区段 `TC23` 之后插入 23 个上行区段：

```yaml
    - { id: TC01U, start_chainage: 0,     end_chainage: 1100,  direction: "up" }
    - { id: TC02U, start_chainage: 1100,  end_chainage: 2000,  direction: "up" }
    - { id: TC03U, start_chainage: 2000,  end_chainage: 2800,  direction: "up" }
    - { id: TC04U, start_chainage: 2800,  end_chainage: 3600,  direction: "up" }
    - { id: TC05U, start_chainage: 3600,  end_chainage: 4300,  direction: "up" }
    - { id: TC06U, start_chainage: 4300,  end_chainage: 5100,  direction: "up" }
    - { id: TC07U, start_chainage: 5100,  end_chainage: 5800,  direction: "up" }
    - { id: TC08U, start_chainage: 5800,  end_chainage: 6600,  direction: "up" }
    - { id: TC09U, start_chainage: 6600,  end_chainage: 7300,  direction: "up" }
    - { id: TC10U, start_chainage: 7300,  end_chainage: 8300,  direction: "up" }
    - { id: TC11U, start_chainage: 8300,  end_chainage: 9200,  direction: "up" }
    - { id: TC12U, start_chainage: 9200,  end_chainage: 10000, direction: "up" }
    - { id: TC13U, start_chainage: 10000, end_chainage: 10700, direction: "up" }
    - { id: TC14U, start_chainage: 10700, end_chainage: 11400, direction: "up" }
    - { id: TC15U, start_chainage: 11400, end_chainage: 12000, direction: "up" }
    - { id: TC16U, start_chainage: 12000, end_chainage: 12700, direction: "up" }
    - { id: TC17U, start_chainage: 12700, end_chainage: 13500, direction: "up" }
    - { id: TC18U, start_chainage: 13500, end_chainage: 14300, direction: "up" }
    - { id: TC19U, start_chainage: 14300, end_chainage: 15200, direction: "up" }
    - { id: TC20U, start_chainage: 15200, end_chainage: 15900, direction: "up" }
    - { id: TC21U, start_chainage: 15900, end_chainage: 16900, direction: "up" }
    - { id: TC22U, start_chainage: 16900, end_chainage: 17700, direction: "up" }
    - { id: TC23U, start_chainage: 17700, end_chainage: 18600, direction: "up" }
```

- [ ] **Step 2: 验证后端加载上行区段**

```bash
cd backend && python -c "from sim_engine.track.config import load_track; t = load_track('sim_engine/config/track.yaml'); up = [c for c in t.circuits if c.direction == 'up']; down = [c for c in t.circuits if c.direction == 'down']; print(f'Down: {len(down)}, Up: {len(up)}')"
```

Expected: `Down: 23, Up: 23`

- [ ] **Step 3: 确认 orchestrator 正常运行（无回归）**

```bash
cd backend && python -c "from sim_engine.orchestrator import Orchestrator; o = Orchestrator.from_config_dir(); s = o.step_once(); occ = s['data']['track']['occupancy']; print(f'Occupancy items: {len(occ)}, Up items: {sum(1 for x in occ if x.get(\"direction\") == \"up\")}')"
```

Expected: `Occupancy items: 46, Up items: 23`

- [ ] **Step 4: Commit**

```bash
git add backend/sim_engine/config/track.yaml
git commit -m "feat(track): add 23 up-direction track circuits to YAML config"
```

---

### Task 2: 前端 OccupancyDisplay 双条渲染

**Files:**
- Modify: `frontend/src/components/views/track/OccupancyDisplay.tsx`

**Interfaces:**
- Consumes: `track.occupancy` (TrackCircuit[]) from SimulationContext, filtered by `direction`
- Produces: Dual SVG occupancy bars + per-direction stats

- [ ] **Step 1: 改写 OccupancyDisplay 为双条渲染 + 分方向统计**

用以下完整文件内容替换 `frontend/src/components/views/track/OccupancyDisplay.tsx`：

```tsx
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

          {/* 车站标签 */}
          {stations.map((s) => (
            <g key={s.id}>
              <line
                x1={s.chainage} y1={upY + trackH + 2}
                x2={s.chainage} y2={upY + trackH + 12}
                stroke="#555" strokeWidth={1}
              />
              <text
                x={s.chainage} y={upY + trackH + 24}
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
```

- [ ] **Step 2: TypeScript 编译检查**

```bash
cd frontend && npx tsc --noEmit 2>&1
```

Expected: 零错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/views/track/OccupancyDisplay.tsx
git commit -m "feat(frontend): add up-direction occupancy bar with dual-bar rendering"
```
