# TrackView 轨道视图实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 TrackView 页面的三个占位符组件改造为真实 mock 数据驱动的可视化组件：ECharts 综合剖面图、SVG 轨道条带图、道岔状态列表。

**Architecture:** 不修改 TrackView 布局结构和 SimulationContext reducer。LineProfileDetail 使用 ECharts 双 Y 轴 + markLine/markArea 标注；OccupancyDisplay 使用内联 SVG viewBox 映射公里标坐标；SwitchStatus 增加 mockSwitches fallback。所有数据从 mockLineData.ts 统一导出。

**Tech Stack:** React 19 + TypeScript, ECharts 6 + echarts-for-react, 内联 SVG（无新依赖）

## Global Constraints

- 不新增 npm 依赖
- 不修改 `SimulationContext.tsx`、`App.tsx`、`TrackView.tsx` 的布局结构
- 所有数据来自 `mockLineData.ts` 和 `SimulationContext`，无需后端
- TypeScript 类型检查必须通过 (`npx tsc -b`)
- 组件遵循函数组件 + Hooks 模式，使用现有暗色主题 CSS 变量

---

### Task 1: mockLineData.ts — 新增 mockSwitches 导出

**Files:**
- Modify: `frontend/src/data/mockLineData.ts`

**Interfaces:**
- Produces: `export const mockSwitches: Switch[]` (8 个道岔)

- [ ] **Step 1: 在文件末尾新增 mockSwitches 数据**

```typescript
// 在 mockLineData.ts 末尾，export const mockLineData 之后新增

import type { Switch } from '../types/simulation';

export const mockSwitches: Switch[] = [
  {
    id: 'SW01', chainage: 100, type: 'single',
    normal_direction: 'ST01→ST02', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW02', chainage: 1900, type: 'single',
    normal_direction: 'ST02→ST03', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW03', chainage: 3600, type: 'crossover',
    normal_direction: '上行→下行', reverse_direction: '上行→上行',
    lateral_speed_limit: 30, state: 'reverse',
  },
  {
    id: 'SW04', chainage: 5300, type: 'single',
    normal_direction: 'ST04→ST05', reverse_direction: '侧线2',
    lateral_speed_limit: 25, state: 'normal',
  },
  {
    id: 'SW05', chainage: 6900, type: 'single',
    normal_direction: 'ST05→ST06', reverse_direction: '侧线1',
    lateral_speed_limit: 25, state: 'transitioning',
  },
  {
    id: 'SW06', chainage: 8600, type: 'single',
    normal_direction: 'ST06→ST07', reverse_direction: '存车线',
    lateral_speed_limit: 20, state: 'reverse',
  },
  {
    id: 'SW07', chainage: 10300, type: 'crossover',
    normal_direction: '上行→下行', reverse_direction: '上行→上行',
    lateral_speed_limit: 30, state: 'normal',
  },
  {
    id: 'SW08', chainage: 12100, type: 'single',
    normal_direction: 'ST08→折返', reverse_direction: '存车线',
    lateral_speed_limit: 20, state: 'normal',
  },
];
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: 无类型错误。

---

### Task 2: LineProfileDetail.tsx — 重写为 ECharts 双 Y 轴综合剖面图

**Files:**
- Modify: `frontend/src/components/views/track/LineProfileDetail.tsx`

**Interfaces:**
- Consumes: `mockLineData` from `../../../data/mockLineData` (StationLayout[], InterStationSegment[])
- Consumes: `useSimulationState()` from `../../../context/SimulationContext` → `trains[0].position`

- [ ] **Step 1: 编写 toStepData 工具函数**

在组件文件顶部（export default 之前）添加：

```typescript
/** 将分段数据展开为 ECharts 阶梯图所需的坐标对 */
function toStepData<T extends Record<string, unknown>>(
  segments: Array<{ start_chainage: number; end_chainage: number } & T>,
  field: keyof T
): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    const val = Number(seg[field]);
    result.push([seg.start_chainage, val]);
    result.push([seg.end_chainage, val]);
  }
  return result;
}
```

- [ ] **Step 2: 构造车站 markLine 和隧道 markArea 数据**

```typescript
import { mockLineData } from '../../../data/mockLineData';

// 在组件内部
const { stations, segments, total_length } = mockLineData;

// 车站竖虚线
const stationMarkLines = stations.map((s) => ({
  xAxis: s.chainage,
  label: { formatter: s.name, color: '#e0e0e0', fontSize: 10 },
  lineStyle: { color: '#555', type: 'dashed' as const, width: 1 },
}));

// 隧道半透明遮罩
const tunnelAreas = segments
  .filter((s) => s.is_tunnel)
  .map((s) => [
    { xAxis: s.start_chainage, itemStyle: { color: 'rgba(128,128,128,0.15)' } },
    { xAxis: s.end_chainage },
  ]);
```

- [ ] **Step 3: 构建 ECharts option 并渲染**

```typescript
import ReactECharts from 'echarts-for-react';
import { useSimulationState } from '../../../context/SimulationContext';

export default function LineProfileDetail() {
  const { trains } = useSimulationState();
  const { stations, segments, total_length } = mockLineData;

  const gradientData = toStepData(segments, 'gradient');
  const speedLimitData = toStepData(segments, 'speed_limit');

  const stationMarkLines = stations.map((s) => ({
    xAxis: s.chainage,
    label: { formatter: s.name, color: '#e0e0e0', fontSize: 10 },
    lineStyle: { color: '#555', type: 'dashed' as const, width: 1 },
  }));

  const tunnelAreas = segments
    .filter((s) => s.is_tunnel)
    .map((s) => [
      { xAxis: s.start_chainage, itemStyle: { color: 'rgba(128,128,128,0.15)' } },
      { xAxis: s.end_chainage },
    ]);

  const trainPos = trains[0]?.position;
  const trainMarkLine = trainPos != null ? [{
    xAxis: trainPos,
    label: { formatter: '🚇', color: '#ff4d4f', fontSize: 14 },
    lineStyle: { color: '#ff4d4f', type: 'solid' as const, width: 2 },
  }] : [];

  const option = {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' as const },
    legend: {
      data: ['坡度 (‰)', '限速 (km/h)'],
      textStyle: { color: '#a0a0a0', fontSize: 11 },
      top: 0,
    },
    grid: { left: 55, right: 55, top: 40, bottom: 35 },
    xAxis: {
      type: 'value' as const,
      name: '公里标 (m)',
      nameTextStyle: { color: '#a0a0a0' },
      axisLabel: { color: '#a0a0a0' },
      axisLine: { lineStyle: { color: '#2a2a4a' } },
      min: 0,
      max: total_length,
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '坡度 (‰)',
        nameTextStyle: { color: '#1890ff' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#1890ff' } },
        splitLine: { lineStyle: { color: '#1a1a2e' } },
      },
      {
        type: 'value' as const,
        name: '限速 (km/h)',
        nameTextStyle: { color: '#ff4d4f' },
        axisLabel: { color: '#a0a0a0' },
        axisLine: { lineStyle: { color: '#ff4d4f' } },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '坡度 (‰)',
        type: 'line',
        yAxisIndex: 0,
        data: gradientData,
        areaStyle: { color: 'rgba(24, 144, 255, 0.15)' },
        lineStyle: { color: '#1890ff', width: 1.5 },
        itemStyle: { color: '#1890ff' },
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: stationMarkLines,
        },
        markArea: {
          silent: true,
          data: tunnelAreas,
        },
      },
      {
        name: '限速 (km/h)',
        type: 'line',
        yAxisIndex: 1,
        data: speedLimitData,
        lineStyle: { color: '#ff4d4f', type: 'dashed' as const, width: 1.5 },
        itemStyle: { color: '#ff4d4f' },
        showSymbol: false,
        markLine: {
          silent: true,
          symbol: 'none',
          data: trainMarkLine,
        },
      },
    ],
  };

  return (
    <div className="panel" style={{ height: '100%' }}>
      <div className="panel-title">🏔️ 线路综合剖面图</div>
      <ReactECharts option={option} style={{ height: 'calc(100% - 30px)' }} notMerge />
    </div>
  );
}
```

- [ ] **Step 4: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: 无类型错误。

---

### Task 3: OccupancyDisplay.tsx — 重写为 SVG 轨道条带图

**Files:**
- Modify: `frontend/src/components/views/track/OccupancyDisplay.tsx`

**Interfaces:**
- Consumes: `mockLineData` → `segments[].circuits[]`, `stations[]`
- Consumes: `useSimulationState()` → `trains[0].position`
- Produces: SVG viewBox `"0 0 {total_length} 120"` 条带图

- [ ] **Step 1: 编写组件代码（完整替换）**

```typescript
/**
 * OccupancyDisplay — SVG 轨道条带图
 * 展示全线轨道电路区段占用状态 + 列车位置
 */
import { useState, useEffect } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { mockLineData } from '../../../data/mockLineData';
import type { TrackCircuit } from '../../../types/simulation';

/** 电路色块颜色 */
function circuitColor(occupied: boolean): { fill: string; stroke: string } {
  return occupied
    ? { fill: '#4a1a1a', stroke: '#8a2a2a' }
    : { fill: '#1a3a1a', stroke: '#2a5a2a' };
}

export default function OccupancyDisplay() {
  const { trains } = useSimulationState();
  const { segments, stations, total_length } = mockLineData;

  // 展平所有电路
  const flatCircuits: TrackCircuit[] = segments.flatMap((seg) => seg.circuits);

  // 本地电路占用状态（初始从 mockLineData 读取）
  const [circuits, setCircuits] = useState<TrackCircuit[]>(flatCircuits);

  // 每 500ms 随机轮换 1-3 个电路状态
  useEffect(() => {
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
  }, []);

  const trainPos = trains[0]?.position ?? null;
  const trackY = 35;
  const trackH = 16;

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
                <title>{`${c.id}\n${c.start_chainage}m - ${c.end_chainage}m\n${c.occupied ? '占用' : '空闲'}`}</title>
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
          {trainPos != null && (
            <g>
              <rect
                x={trainPos - 8} y={trackY - 10}
                width={16} height={trackH + 8}
                rx={3} fill="#ff4d4f" opacity={0.85}
              />
              <text
                x={trainPos} y={trackY + 10}
                textAnchor="middle" fontSize={10} fill="#fff"
              >
                🚇
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: 无类型错误。

---

### Task 4: SwitchStatus.tsx — 增强 mock 数据 fallback

**Files:**
- Modify: `frontend/src/components/views/track/SwitchStatus.tsx`

**Interfaces:**
- Consumes: `mockSwitches` from `../../../data/mockLineData`
- Consumes: `useSimulationState()` → `track.switch_states`（优先 context，空则 fallback）
- Produces: 增强后的道岔卡片列表

- [ ] **Step 1: 修改组件，增加 mockSwitches fallback + 增强字段**

```typescript
/**
 * SwitchStatus — 道岔状态图
 * 优先使用 context 数据，空时 fallback 到 mockSwitches
 */
import { useSimulationState } from '../../../context/SimulationContext';
import { mockSwitches } from '../../../data/mockLineData';
import type { Switch } from '../../../types/simulation';

const stateColors: Record<string, string> = {
  normal: '#52c41a',
  reverse: '#faad14',
  transitioning: '#1890ff',
};

const stateLabels: Record<string, string> = {
  normal: '定位',
  reverse: '反位',
  transitioning: '转换中',
};

const stateIcons: Record<string, string> = {
  normal: '→',
  reverse: '↗',
  transitioning: '⟳',
};

const typeLabels: Record<string, string> = {
  single: '单开',
  crossover: '交叉渡线',
};

export default function SwitchStatus() {
  const { track } = useSimulationState();

  // context 有数据则用 context，否则 fallback 到 mockSwitches
  const switches: Switch[] =
    track.switch_states.length > 0 ? track.switch_states : mockSwitches;

  return (
    <div className="panel" style={{ height: '100%', overflow: 'auto' }}>
      <div className="panel-title">🔀 道岔状态</div>
      <div style={styles.grid}>
        {switches.map((sw) => (
          <div key={sw.id} style={styles.item}>
            <div style={styles.header}>
              <span style={styles.id}>{sw.id}</span>
              <span style={styles.typeTag}>{typeLabels[sw.type] || sw.type}</span>
              <span
                style={{
                  ...styles.badge,
                  backgroundColor: stateColors[sw.state] || '#999',
                  ...(sw.state === 'transitioning' ? styles.spin : {}),
                }}
              >
                <span style={{ marginRight: 2 }}>{stateIcons[sw.state] || '?'}</span>
                {stateLabels[sw.state] || sw.state}
              </span>
            </div>
            <div style={styles.details}>
              <span>📍 {sw.chainage} m</span>
              <span>🔧 定位: {sw.normal_direction}</span>
              <span>🔁 反位: {sw.reverse_direction}</span>
              <span>⚠️ 侧向限速: {sw.lateral_speed_limit} km/h</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    padding: '8px 0',
  },
  item: {
    padding: '8px 10px',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    backgroundColor: 'var(--bg-dark)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  id: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-highlight)',
  },
  typeTag: {
    fontSize: '9px',
    padding: '1px 5px',
    borderRadius: '3px',
    backgroundColor: 'var(--bg-darker)',
    color: 'var(--text-secondary)',
  },
  badge: {
    padding: '2px 8px',
    borderRadius: '10px',
    fontSize: '10px',
    color: '#fff',
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    marginLeft: 'auto',
  },
  spin: {
    animation: 'spin 1s linear infinite',
  },
  details: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '2px 12px',
    marginTop: '6px',
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
};
```

- [ ] **Step 2: 添加 CSS 旋转动画**

在 `frontend/src/index.css` 末尾添加：

```css
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

- [ ] **Step 3: 验证 TypeScript 编译**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: 无类型错误。

---

### Task 5: 集成验证 — 运行前端确认 TrackView 正常渲染

**Files:** 无修改（验证任务）

- [ ] **Step 1: TypeScript 类型检查**

```bash
cd frontend && npx tsc -b --noEmit
```

Expected: 无错误。

- [ ] **Step 2: 启动开发服务器**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 浏览器验证**

打开 `http://localhost:5173`，切换到「轨道视图」：

1. **LineProfileDetail**: 显示坡度蓝色填充图 + 限速红色虚线 + 8 个车站竖虚线 + 隧道灰色遮罩
2. **OccupancyDisplay**: 显示 SVG 轨道条带，色块代表电路占用状态，hover 可见 tooltip
3. **SwitchStatus**: 显示 8 个道岔卡片，各有状态彩色标签和方向图标
4. 无"暂无数据"或"迭代三实现"占位符

---

### Task 6: 清理 — 移除未使用的 import（如有）

**Files:** 各修改文件中检查

- [ ] **Step 1: 运行 lint 检查**

```bash
cd frontend && npm run lint
```

Expected: 无 lint 警告。

- [ ] **Step 2: 最终确认**

确认所有文件修改完整且无遗漏。
