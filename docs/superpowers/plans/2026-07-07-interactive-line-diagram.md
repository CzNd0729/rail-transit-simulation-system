# 交互式线路图实现规划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 替换现有 TrainAnimation 为可缩放、可交互的 SVG 线路图，支持站内多股道布局、区间轨道电路占用可视化、列车跟随与手动浏览。

**Architecture:** SVG + React 自定义组件。SVG 画布使用世界坐标（米），X 轴 = 公里标，Y 轴 = 股道编号映射。`useViewport` hook 管理 viewBox 实现缩放/平移/跟随。子组件（StationNode、TrackSegment、TrainMarker）各自渲染 SVG `<g>` 组，由 LineDiagram 主容器组合。StationInfoCard 为 HTML 浮层。

**Tech Stack:** React 19, TypeScript 6, SVG (原生), CSS inline styles (无额外依赖)

## Global Constraints

- 所有新增文件放在 `frontend/src/` 下，遵循现有目录结构
- 组件使用 inline `styles` 对象（与现有组件风格一致，不引入 CSS 模块或框架）
- 类型定义追加到现有 `types/simulation.ts`，不创建新类型文件
- 颜色使用 CSS 变量（`var(--xxx)`）或现有 `format.ts` 中的工具函数
- Mock 数据放在 `frontend/src/data/` 目录

## File Structure

| 文件 | 职责 | 操作 |
|---|---|---|
| `src/types/simulation.ts` | 新增 TrackLayout, StationLayout, InterStationSegment, LineLayout 接口；AppState 新增 lineLayout 字段 | 修改 |
| `src/data/mockLineData.ts` | 8 站 Mock 线路数据 | 新增 |
| `src/hooks/useViewport.ts` | SVG viewBox 管理、缩放/平移/跟随逻辑 | 新增 |
| `src/components/views/overview/TrackSegment.tsx` | 区间轨道电路 SVG 色块渲染 | 新增 |
| `src/components/views/overview/StationNode.tsx` | 站内多股道 SVG 渲染 | 新增 |
| `src/components/views/overview/TrainMarker.tsx` | 列车图标 SVG 渲染 | 新增 |
| `src/components/views/overview/StationInfoCard.tsx` | 车站信息浮动卡片 | 新增 |
| `src/components/views/overview/ViewportControls.tsx` | 缩放/跟随控制栏 | 新增 |
| `src/components/views/overview/LineDiagram.tsx` | 主容器，组装 SVG 画布 + 控制栏 + 信息卡片 | 新增 |
| `src/pages/OverviewView.tsx` | TrainAnimation → LineDiagram | 修改 |
| `src/context/SimulationContext.tsx` | initialState 新增 lineLayout 字段 | 修改 |
| `src/components/views/overview/TrainAnimation.tsx` | 被 LineDiagram 取代 | 删除 |

---

### Task 1: 数据基础 — 类型定义与 Mock 数据

**Files:**
- Modify: `frontend/src/types/simulation.ts`
- Create: `frontend/src/data/mockLineData.ts`
- Modify: `frontend/src/context/SimulationContext.tsx`

**Interfaces:**
- Consumes: 无（基础数据层）
- Produces: `TrackLayout`, `StationLayout`, `InterStationSegment`, `LineLayout` 接口；`mockLineData` 导出常量

- [ ] **Step 1: 在 types/simulation.ts 中更新 Station.chainage 注释并追加新接口**

先修改 Station 接口的 chainage 注释（第 32 行），从"站台中心公里标"改为"车站起点公里标"：

```typescript
  chainage: number;          // 车站起点公里标 (m)
```

然后在文件末尾（`InitConfig` 接口之后）追加：

```typescript
// ==================== 线路布局（交互式线路图） ====================

/** 站内股道布局 */
export interface TrackLayout {
  track_id: string;
  name: string;           // "正线", "侧线1", "存车线"
  type: 'main' | 'siding' | 'parking';
  occupied: boolean;
}

/** 车站布局（扩展现有 Station） */
export interface StationLayout extends Station {
  length: number;         // 站长 (m)
  tracks: TrackLayout[];
  arrival_time?: number;  // 到达仿真时间 (s)
  departure_time?: number;
  dwell_time_actual?: number; // 实际停站时长 (s)
  occupancy_rate: number; // 站台占用率 [0, 1]
}

/** 区间轨道段（两站之间） */
export interface InterStationSegment {
  start_chainage: number;
  end_chainage: number;
  circuits: TrackCircuit[];
}

/** 完整线路布局数据 */
export interface LineLayout {
  name: string;
  stations: StationLayout[];
  segments: InterStationSegment[];
  total_length: number;
}
```

- [ ] **Step 2: 在 AppState 接口中新增 lineLayout 字段**

在 `AppState` 接口的 `fps: number;` 之后追加：

```typescript
  /** 线路布局数据（Mock 模式或从后端初始化） */
  lineLayout: LineLayout | null;
```

- [ ] **Step 3: 更新 SimulationContext.tsx 的 initialState**

在 `initialState` 对象中 `fps: 0,` 之后追加：

```typescript
  lineLayout: null,
```

同时在 `SimulationContext.tsx` 顶部的 import 中追加 `LineLayout`（虽然 initialState 用 null 不需要，但为后续 action 类型准备）：

```typescript
import type {
  AppState,
  RunState,
  ViewType,
  SimulationSnapshot,
  SimulationParams,
  LineLayout,
} from '../types/simulation';
```

- [ ] **Step 4: 创建 Mock 数据文件**

创建 `frontend/src/data/mockLineData.ts`：

```typescript
/**
 * Mock 线路数据 — 8 站线路
 * 用于前端开发阶段，后端就绪后替换为 API 数据
 */
import type { LineLayout, StationLayout, InterStationSegment, TrackCircuit } from '../types/simulation';

// ==================== 车站定义 ====================

const stations: StationLayout[] = [
  {
    id: 'ST01', name: '始发站', chainage: 0, dwell_time: 30,
    platform_half_length: 100, is_terminus: true, sort_order: 1,
    length: 200,
    tracks: [
      { track_id: 'ST01-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST01-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST01-s2', name: '侧线2', type: 'siding', occupied: true },
      { track_id: 'ST01-p1', name: '存车线', type: 'parking', occupied: false },
    ],
    occupancy_rate: 0.25,
  },
  {
    id: 'ST02', name: '科技园', chainage: 1800, dwell_time: 25,
    platform_half_length: 75, is_terminus: false, sort_order: 2,
    length: 150,
    tracks: [
      { track_id: 'ST02-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST02-s1', name: '侧线1', type: 'siding', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST03', name: '大学城', chainage: 3500, dwell_time: 20,
    platform_half_length: 60, is_terminus: false, sort_order: 3,
    length: 120,
    tracks: [
      { track_id: 'ST03-main', name: '正线', type: 'main', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST04', name: '市中心', chainage: 5200, dwell_time: 35,
    platform_half_length: 125, is_terminus: false, sort_order: 4,
    length: 250,
    tracks: [
      { track_id: 'ST04-main', name: '正线', type: 'main', occupied: true },
      { track_id: 'ST04-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST04-s2', name: '侧线2', type: 'siding', occupied: true },
    ],
    occupancy_rate: 0.67,
  },
  {
    id: 'ST05', name: '商业街', chainage: 6800, dwell_time: 25,
    platform_half_length: 65, is_terminus: false, sort_order: 5,
    length: 130,
    tracks: [
      { track_id: 'ST05-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST05-s1', name: '侧线1', type: 'siding', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST06', name: '工业区', chainage: 8500, dwell_time: 30,
    platform_half_length: 90, is_terminus: false, sort_order: 6,
    length: 180,
    tracks: [
      { track_id: 'ST06-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST06-s1', name: '侧线1', type: 'siding', occupied: true },
      { track_id: 'ST06-p1', name: '存车线', type: 'parking', occupied: false },
    ],
    occupancy_rate: 0.33,
  },
  {
    id: 'ST07', name: '新城', chainage: 10200, dwell_time: 20,
    platform_half_length: 60, is_terminus: false, sort_order: 7,
    length: 120,
    tracks: [
      { track_id: 'ST07-main', name: '正线', type: 'main', occupied: false },
    ],
    occupancy_rate: 0.0,
  },
  {
    id: 'ST08', name: '终点站', chainage: 12000, dwell_time: 30,
    platform_half_length: 100, is_terminus: true, sort_order: 8,
    length: 200,
    tracks: [
      { track_id: 'ST08-main', name: '正线', type: 'main', occupied: false },
      { track_id: 'ST08-s1', name: '侧线1', type: 'siding', occupied: false },
      { track_id: 'ST08-s2', name: '侧线2', type: 'siding', occupied: false },
      { track_id: 'ST08-p1', name: '存车线', type: 'parking', occupied: true },
    ],
    occupancy_rate: 0.25,
  },
];

// ==================== 区间轨道电路 ====================

function generateCircuits(start: number, end: number, prefix: string): TrackCircuit[] {
  const circuits: TrackCircuit[] = [];
  const segmentLen = 300; // 每个轨道电路约 300m
  let pos = start;
  let idx = 0;
  while (pos < end) {
    const next = Math.min(pos + segmentLen + Math.floor(Math.sin(idx * 1.7) * 80), end);
    circuits.push({
      id: `${prefix}-TC${idx + 1}`,
      start_chainage: pos,
      end_chainage: next,
      direction: 'both',
      occupied: idx % 5 === 2, // 每 5 个区段有 1 个占用
    });
    pos = next;
    idx++;
  }
  return circuits;
}

const segments: InterStationSegment[] = [];
for (let i = 0; i < stations.length - 1; i++) {
  const startStation = stations[i];
  const endStation = stations[i + 1];
  const segStart = startStation.chainage + startStation.length;
  const segEnd = endStation.chainage;
  segments.push({
    start_chainage: segStart,
    end_chainage: segEnd,
    circuits: generateCircuits(segStart, segEnd, `SEG${i + 1}`),
  });
}

// ==================== 导出 ====================

export const mockLineData: LineLayout = {
  name: 'NULL示范线',
  stations,
  segments,
  total_length: 12200, // 终点站 chainage + length
};
```

- [ ] **Step 5: 验证编译通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 6: 提交**

```bash
git add frontend/src/types/simulation.ts frontend/src/data/mockLineData.ts frontend/src/context/SimulationContext.tsx
git commit -m "feat(frontend): 新增线路布局类型定义与 8 站 Mock 数据"
```

---

### Task 2: 视口管理 — useViewport Hook

**Files:**
- Create: `frontend/src/hooks/useViewport.ts`

**Interfaces:**
- Consumes: 无（纯逻辑 hook，不依赖其他新组件）
- Produces: `useViewport(trainPosition, totalLength, containerRef)` → `UseViewportReturn`

- [ ] **Step 1: 创建 useViewport.ts**

创建 `frontend/src/hooks/useViewport.ts`：

```typescript
/**
 * useViewport — SVG 视口管理 Hook
 * 管理缩放、平移、跟随模式，输出 viewBox 字符串
 *
 * 坐标系: 世界坐标 (m), X = 公里标, Y = 股道映射
 */
import { useState, useCallback, useRef, useEffect, type RefObject } from 'react';

interface ViewportState {
  zoom: number;
  panX: number;
  panY: number;
  followMode: boolean;
}

interface UseViewportOptions {
  /** 列车当前公里标 (m), undefined 表示无列车 */
  trainPosition?: number;
  /** 线路总长 (m) */
  totalLength: number;
  /** SVG 容器的 ref */
  containerRef: RefObject<SVGSVGElement | null>;
  /** Y 轴可视范围 (世界坐标单位) */
  worldHeight?: number;
  /** 最小缩放 */
  minZoom?: number;
  /** 最大缩放 */
  maxZoom?: number;
}

interface UseViewportReturn {
  /** 当前 SVG viewBox 字符串 */
  viewBox: string;
  /** 当前缩放倍率 */
  zoom: number;
  /** 是否处于跟随模式 */
  followMode: boolean;
  /** 设置缩放倍率 */
  setZoom: (z: number) => void;
  /** 切换跟随模式 */
  toggleFollow: () => void;
  /** 缩放到全线可见 */
  fitAll: () => void;
  /** 滚轮事件处理 */
  handleWheel: (e: React.WheelEvent) => void;
  /** 鼠标按下 (开始拖拽) */
  handleMouseDown: (e: React.MouseEvent) => void;
  /** 鼠标移动 (拖拽中) */
  handleMouseMove: (e: React.MouseEvent) => void;
  /** 鼠标松开 (结束拖拽) */
  handleMouseUp: () => void;
}

export function useViewport(options: UseViewportOptions): UseViewportReturn {
  const {
    trainPosition,
    totalLength,
    containerRef,
    worldHeight = 80,
    minZoom = 0.2,
    maxZoom = 5.0,
  } = options;

  const [state, setState] = useState<ViewportState>({
    zoom: 1.0,
    panX: 0,
    panY: 0,
    followMode: true,
  });

  const isDragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const animFrameRef = useRef<number>(0);

  // 计算容器宽度 (px)
  const getContainerWidth = useCallback(() => {
    return containerRef.current?.clientWidth || 800;
  }, [containerRef]);

  // 计算 viewBox 宽度 (世界坐标)
  const getViewWidth = useCallback((zoom: number) => {
    return totalLength / zoom;
  }, [totalLength]);

  // 屏幕像素 → 世界坐标 X
  const screenToWorldX = useCallback((screenX: number, zoom: number, panX: number) => {
    const containerW = getContainerWidth();
    const viewW = totalLength / zoom;
    return panX + (screenX / containerW) * viewW;
  }, [getContainerWidth, totalLength]);

  // 跟随模式: 每帧更新 panX 使列车在视口 30% 处
  useEffect(() => {
    if (!state.followMode || trainPosition === undefined) return;

    const viewW = getViewWidth(state.zoom);
    const targetPanX = trainPosition - viewW * 0.3;
    const clampedPanX = Math.max(0, Math.min(targetPanX, totalLength - viewW));

    setState(prev => {
      if (Math.abs(prev.panX - clampedPanX) < 0.5) return prev;
      return { ...prev, panX: clampedPanX };
    });
  }, [trainPosition, state.followMode, state.zoom, getViewWidth, totalLength]);

  // 计算 viewBox 字符串
  const viewW = getViewWidth(state.zoom);
  const clampedPanX = Math.max(0, Math.min(state.panX, Math.max(0, totalLength - viewW)));
  const viewBox = `${clampedPanX} ${state.panY} ${viewW} ${worldHeight}`;

  // 缩放
  const setZoom = useCallback((z: number) => {
    setState(prev => ({ ...prev, zoom: Math.max(minZoom, Math.min(maxZoom, z)) }));
  }, [minZoom, maxZoom]);

  // 切换跟随
  const toggleFollow = useCallback(() => {
    setState(prev => {
      if (!prev.followMode && trainPosition !== undefined) {
        // 重新锁定: 平滑动画到列车位置
        const viewW = totalLength / prev.zoom;
        const targetPanX = trainPosition - viewW * 0.3;
        const clamped = Math.max(0, Math.min(targetPanX, totalLength - viewW));

        // 用 requestAnimationFrame 做线性插值动画
        const startPanX = prev.panX;
        const startTime = performance.now();
        const duration = 300;

        const animate = (now: number) => {
          const t = Math.min((now - startTime) / duration, 1);
          const eased = t * (2 - t); // ease-out
          const currentPanX = startPanX + (clamped - startPanX) * eased;
          setState(s => ({ ...s, panX: currentPanX }));
          if (t < 1) {
            animFrameRef.current = requestAnimationFrame(animate);
          }
        };
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = requestAnimationFrame(animate);

        return { ...prev, followMode: true };
      }
      return { ...prev, followMode: false };
    });
  }, [trainPosition, totalLength]);

  // 全线总览
  const fitAll = useCallback(() => {
    setState(prev => ({ ...prev, zoom: minZoom, panX: 0, panY: 0, followMode: false }));
  }, [minZoom]);

  // 滚轮缩放: 以鼠标位置为锚点
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    const mouseX = e.clientX - rect.left;
    setState(prev => {
      const worldXBefore = screenToWorldX(mouseX, prev.zoom, prev.panX);
      const delta = e.deltaY > 0 ? -0.2 : 0.2;
      const newZoom = Math.max(minZoom, Math.min(maxZoom, prev.zoom + delta));
      // 保持鼠标下的世界坐标不变
      const containerW = getContainerWidth();
      const newViewW = totalLength / newZoom;
      const newPanX = worldXBefore - (mouseX / containerW) * newViewW;
      return { ...prev, zoom: newZoom, panX: newPanX, followMode: false };
    });
  }, [containerRef, screenToWorldX, minZoom, maxZoom, getContainerWidth, totalLength]);

  // 鼠标拖拽
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    dragStart.current = { x: e.clientX, y: e.clientY, panX: state.panX, panY: state.panY };
    setState(prev => ({ ...prev, followMode: false }));
  }, [state.panX, state.panY]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging.current) return;
    const containerW = getContainerWidth();
    setState(prev => {
      const viewW = totalLength / prev.zoom;
      const dx = e.clientX - dragStart.current.x;
      const dy = e.clientY - dragStart.current.y;
      const worldDx = -(dx / containerW) * viewW;
      const worldDy = -(dy / containerW) * viewW; // 保持纵横比
      return {
        ...prev,
        panX: dragStart.current.panX + worldDx,
        panY: dragStart.current.panY + worldDy,
      };
    });
  }, [getContainerWidth, totalLength]);

  const handleMouseUp = useCallback(() => {
    isDragging.current = false;
  }, []);

  // 清理动画帧
  useEffect(() => {
    return () => cancelAnimationFrame(animFrameRef.current);
  }, []);

  return {
    viewBox,
    zoom: state.zoom,
    followMode: state.followMode,
    setZoom,
    toggleFollow,
    fitAll,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
  };
}
```

- [ ] **Step 2: 验证编译通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 3: 提交**

```bash
git add frontend/src/hooks/useViewport.ts
git commit -m "feat(frontend): 新增 useViewport 视口管理 hook"
```

---

### Task 3: SVG 子组件 — TrackSegment、StationNode、TrainMarker

**Files:**
- Create: `frontend/src/components/views/overview/TrackSegment.tsx`
- Create: `frontend/src/components/views/overview/StationNode.tsx`
- Create: `frontend/src/components/views/overview/TrainMarker.tsx`

**Interfaces:**
- Consumes: `InterStationSegment`, `StationLayout`, `TrainState` (来自 Task 1 类型)
- Produces: 三个 React 组件供 LineDiagram 使用

- [ ] **Step 1: 创建 TrackSegment.tsx — 区间轨道电路渲染**

创建 `frontend/src/components/views/overview/TrackSegment.tsx`：

```typescript
/**
 * TrackSegment — 区间轨道电路 SVG 渲染
 * 在两站之间绘制轨道电路色块，颜色表示占用/空闲状态
 */
import type { InterStationSegment } from '../../../types/simulation';

interface TrackSegmentProps {
  segment: InterStationSegment;
  /** Y 坐标基准线 (世界坐标) */
  y: number;
  /** 色块高度 (世界坐标) */
  height?: number;
}

const COLOR_OCCUPIED = 'rgba(255, 77, 79, 0.6)';
const COLOR_FREE = 'rgba(82, 196, 26, 0.3)';
const GAP_COLOR = '#2a2a4a';

export default function TrackSegment({ segment, y, height = 6 }: TrackSegmentProps) {
  return (
    <g>
      {segment.circuits.map((circuit) => {
        const x = circuit.start_chainage;
        const w = circuit.end_chainage - circuit.start_chainage;
        return (
          <rect
            key={circuit.id}
            x={x}
            y={y - height / 2}
            width={Math.max(0, w - 1)} // 1m 间隙
            height={height}
            fill={circuit.occupied ? COLOR_OCCUPIED : COLOR_FREE}
            rx={1}
          />
        );
      })}
      {/* 区间基准线 (轨道中心线) */}
      <line
        x1={segment.start_chainage}
        y1={y}
        x2={segment.end_chainage}
        y2={y}
        stroke={GAP_COLOR}
        strokeWidth={1}
        strokeDasharray="4 2"
      />
    </g>
  );
}
```

- [ ] **Step 2: 创建 StationNode.tsx — 站内股道渲染**

创建 `frontend/src/components/views/overview/StationNode.tsx`：

```typescript
/**
 * StationNode — 站内多股道 SVG 渲染
 * 绘制车站范围内的所有股道，正线粗实线、侧线细实线、存车线虚线
 */
import { memo } from 'react';
import type { StationLayout } from '../../../types/simulation';

interface StationNodeProps {
  station: StationLayout;
  /** 是否显示详情 (缩放级别控制) */
  showDetail: boolean;
  /** 点击车站事件 */
  onClick?: (stationId: string) => void;
  /** 鼠标进入事件 */
  onMouseEnter?: (stationId: string) => void;
  /** 鼠标离开事件 */
  onMouseLeave?: () => void;
  /** 是否选中 */
  selected: boolean;
}

const TRACK_STYLES = {
  main: { strokeWidth: 3, stroke: '#e0e0e0', strokeDasharray: '' },
  siding: { strokeWidth: 2, stroke: '#a0a0a0', strokeDasharray: '' },
  parking: { strokeWidth: 2, stroke: '#808080', strokeDasharray: '6 3' },
} as const;

const TRACK_SPACING = 12; // 股道间垂直间距 (世界坐标单位)
const BORDER_COLOR = '#4a4a6a';

function StationNodeInner({
  station,
  showDetail,
  onClick,
  onMouseEnter,
  onMouseLeave,
  selected,
}: StationNodeProps) {
  const x = station.chainage;
  const w = station.length;
  const trackCount = station.tracks.length;

  // 车站整体高度
  const totalHeight = showDetail
    ? Math.max(trackCount * TRACK_SPACING + 8, 20)
    : 16;

  // 股道 Y 坐标: 居中排列
  const baseY = 40; // 车站中心线 Y
  const startY = baseY - ((trackCount - 1) * TRACK_SPACING) / 2;

  return (
    <g
      onClick={() => onClick?.(station.id)}
      onMouseEnter={() => onMouseEnter?.(station.id)}
      onMouseLeave={onMouseLeave}
      style={{ cursor: 'pointer' }}
    >
      {/* 车站背景 */}
      <rect
        x={x}
        y={baseY - totalHeight / 2}
        width={w}
        height={totalHeight}
        fill={selected ? 'rgba(24, 144, 255, 0.15)' : 'rgba(255, 255, 255, 0.03)'}
        stroke={selected ? '#1890ff' : BORDER_COLOR}
        strokeWidth={selected ? 2 : 1}
        rx={2}
      />

      {/* 车站封边竖线 */}
      <line x1={x} y1={baseY - totalHeight / 2 - 4} x2={x} y2={baseY + totalHeight / 2 + 4}
        stroke={BORDER_COLOR} strokeWidth={1} />
      <line x1={x + w} y1={baseY - totalHeight / 2 - 4} x2={x + w} y2={baseY + totalHeight / 2 + 4}
        stroke={BORDER_COLOR} strokeWidth={1} />

      {/* 站名 */}
      <text
        x={x + w / 2}
        y={baseY - totalHeight / 2 - 6}
        textAnchor="middle"
        fill="#e0e0e0"
        fontSize={10}
        fontWeight={600}
      >
        {station.name}
      </text>

      {/* 公里标 */}
      <text
        x={x + w / 2}
        y={baseY + totalHeight / 2 + 12}
        textAnchor="middle"
        fill="#808080"
        fontSize={8}
      >
        K{(station.chainage / 1000).toFixed(1)}
      </text>

      {/* 股道渲染 (仅 detail 模式) */}
      {showDetail && station.tracks.map((track, i) => {
        const ty = startY + i * TRACK_SPACING;
        const style = TRACK_STYLES[track.type];
        return (
          <g key={track.track_id}>
            {/* 股道占用底色 */}
            {track.occupied && (
              <rect
                x={x + 2}
                y={ty - 3}
                width={w - 4}
                height={6}
                fill="rgba(255, 77, 79, 0.2)"
                rx={1}
              />
            )}
            {/* 股道线 */}
            <line
              x1={x + 4}
              y1={ty}
              x2={x + w - 4}
              y2={ty}
              stroke={track.occupied ? '#ff4d4f' : style.stroke}
              strokeWidth={style.strokeWidth}
              strokeDasharray={style.strokeDasharray || undefined}
            />
            {/* 股道名称 (缩放较大时显示) */}
            <text
              x={x + 6}
              y={ty - 4}
              fill="#808080"
              fontSize={6}
            >
              {track.name}
            </text>
          </g>
        );
      })}

      {/* 简略模式: 只显示车站方块 + 站名 */}
      {!showDetail && (
        <line
          x1={x + 4}
          y1={baseY}
          x2={x + w - 4}
          y2={baseY}
          stroke="#e0e0e0"
          strokeWidth={3}
        />
      )}
    </g>
  );
}

const StationNode = memo(StationNodeInner);
export default StationNode;
```

- [ ] **Step 3: 创建 TrainMarker.tsx — 列车图标渲染**

创建 `frontend/src/components/views/overview/TrainMarker.tsx`：

```typescript
/**
 * TrainMarker — 列车图标 SVG 渲染
 * 在正线上显示列车位置，底色跟随工况
 */
import type { TrainState } from '../../../types/simulation';

interface TrainMarkerProps {
  train: TrainState;
  /** 正线 Y 坐标 (世界坐标) */
  trackY: number;
}

const MODE_COLORS: Record<string, string> = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

export default function TrainMarker({ train, trackY }: TrainMarkerProps) {
  const color = MODE_COLORS[train.mode] || '#999';
  const x = train.position;

  return (
    <g
      style={{
        transition: 'transform 100ms linear',
      }}
    >
      {/* 列车背景色块 */}
      <rect
        x={x - 10}
        y={trackY - 8}
        width={20}
        height={16}
        rx={4}
        fill={color}
        opacity={0.9}
      />
      {/* 列车图标文字 */}
      <text
        x={x}
        y={trackY + 4}
        textAnchor="middle"
        fontSize={10}
        fill="#fff"
      >
        🚇
      </text>
      {/* 速度标注 */}
      <text
        x={x}
        y={trackY - 12}
        textAnchor="middle"
        fontSize={7}
        fill={color}
        fontWeight={600}
      >
        {train.speed.toFixed(0)}km/h
      </text>
    </g>
  );
}
```

- [ ] **Step 4: 验证编译通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/views/overview/TrackSegment.tsx frontend/src/components/views/overview/StationNode.tsx frontend/src/components/views/overview/TrainMarker.tsx
git commit -m "feat(frontend): 新增线路图 SVG 子组件 (TrackSegment/StationNode/TrainMarker)"
```

---

### Task 4: UI 辅助组件 — StationInfoCard 与 ViewportControls

**Files:**
- Create: `frontend/src/components/views/overview/StationInfoCard.tsx`
- Create: `frontend/src/components/views/overview/ViewportControls.tsx`

**Interfaces:**
- Consumes: `StationLayout` (Task 1), viewport 控制函数签名 (Task 2)
- Produces: 两个 React 组件供 LineDiagram 使用

- [ ] **Step 1: 创建 StationInfoCard.tsx**

创建 `frontend/src/components/views/overview/StationInfoCard.tsx`：

```typescript
/**
 * StationInfoCard — 车站信息浮动卡片
 * 悬停或点击车站时显示的详细信息面板 (HTML 浮层)
 */
import type { StationLayout } from '../../../types/simulation';
import { formatSimTime } from '../../../utils/format';

interface StationInfoCardProps {
  station: StationLayout;
  /** 卡片定位 (屏幕像素, 由父组件计算) */
  position: { x: number; y: number };
  /** 关闭卡片 */
  onClose: () => void;
}

export default function StationInfoCard({ station, position, onClose }: StationInfoCardProps) {
  const trackSummary = station.tracks
    .map(t => `${t.name}:${t.occupied ? '占用' : '空闲'}`)
    .join('  ');

  return (
    <div
      style={{
        ...styles.card,
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* 头部 */}
      <div style={styles.header}>
        <span style={styles.title}>🏢 {station.name}</span>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      {/* 基本信息 */}
      <div style={styles.row}>
        <span style={styles.label}>公里标:</span>
        <span>K{(station.chainage / 1000).toFixed(3).replace('.', '+')}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>站长:</span>
        <span>{station.length}m</span>
        <span style={{ marginLeft: 12 }}>{station.tracks.length}条股道</span>
      </div>

      {/* 时间信息 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>到达:</span>
        <span>{station.arrival_time != null ? formatSimTime(station.arrival_time) : '--:--:--'}</span>
        <span style={{ marginLeft: 12, color: '#a0a0a0' }}>出发:</span>
        <span>{station.departure_time != null ? formatSimTime(station.departure_time) : '--:--:--'}</span>
      </div>
      <div style={styles.row}>
        <span style={styles.label}>停站:</span>
        <span>{station.dwell_time_actual != null ? `${station.dwell_time_actual.toFixed(0)}s` : '--'}</span>
      </div>

      {/* 占用信息 */}
      <div style={styles.divider} />
      <div style={styles.row}>
        <span style={styles.label}>站台占用:</span>
        <div style={styles.barContainer}>
          <div
            style={{
              ...styles.barFill,
              width: `${station.occupancy_rate * 100}%`,
            }}
          />
        </div>
        <span style={{ marginLeft: 8 }}>{(station.occupancy_rate * 100).toFixed(0)}%</span>
      </div>
      <div style={styles.trackStatus}>
        {trackSummary}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    position: 'absolute',
    zIndex: 100,
    backgroundColor: 'var(--bg-dark)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '12px',
    minWidth: '240px',
    fontSize: '12px',
    color: '#e0e0e0',
    boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
    pointerEvents: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  title: {
    fontWeight: 600,
    fontSize: '14px',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#808080',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '0 4px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '4px',
  },
  label: {
    color: '#808080',
    marginRight: '8px',
    minWidth: '60px',
  },
  divider: {
    height: '1px',
    backgroundColor: 'var(--border-color)',
    margin: '8px 0',
  },
  barContainer: {
    flex: 1,
    height: '6px',
    backgroundColor: 'rgba(255,255,255,0.1)',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    backgroundColor: '#1890ff',
    borderRadius: '3px',
    transition: 'width 0.3s',
  },
  trackStatus: {
    fontSize: '11px',
    color: '#a0a0a0',
    marginTop: '4px',
    lineHeight: '1.6',
  },
};
```

- [ ] **Step 2: 创建 ViewportControls.tsx**

创建 `frontend/src/components/views/overview/ViewportControls.tsx`：

```typescript
/**
 * ViewportControls — 视口控制栏
 * 缩放滑块 + 跟随锁定按钮 + 全线总览按钮
 */
interface ViewportControlsProps {
  zoom: number;
  followMode: boolean;
  onZoomChange: (z: number) => void;
  onToggleFollow: () => void;
  onFitAll: () => void;
}

export default function ViewportControls({
  zoom,
  followMode,
  onZoomChange,
  onToggleFollow,
  onFitAll,
}: ViewportControlsProps) {
  return (
    <div style={styles.container}>
      {/* 缩放控制 */}
      <button
        style={styles.btn}
        onClick={() => onZoomChange(Math.max(0.2, zoom - 0.5))}
        title="缩小"
      >
        −
      </button>
      <input
        type="range"
        min={0.2}
        max={5}
        step={0.1}
        value={zoom}
        onChange={(e) => onZoomChange(parseFloat(e.target.value))}
        style={styles.slider}
        title={`缩放: ${zoom.toFixed(1)}×`}
      />
      <button
        style={styles.btn}
        onClick={() => onZoomChange(Math.min(5, zoom + 0.5))}
        title="放大"
      >
        +
      </button>

      <span style={styles.zoomLabel}>{zoom.toFixed(1)}×</span>

      {/* 分隔线 */}
      <div style={styles.separator} />

      {/* 跟随按钮 */}
      <button
        style={{
          ...styles.btn,
          backgroundColor: followMode ? 'rgba(24, 144, 255, 0.3)' : 'transparent',
          color: followMode ? '#1890ff' : '#a0a0a0',
        }}
        onClick={onToggleFollow}
        title={followMode ? '取消跟随' : '锁定跟随'}
      >
        {followMode ? '📍' : '📌'}
      </button>

      {/* 全线总览 */}
      <button
        style={styles.btn}
        onClick={onFitAll}
        title="全线总览"
      >
        🔍
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    backgroundColor: 'rgba(30, 30, 50, 0.9)',
    borderRadius: '6px',
    border: '1px solid var(--border-color)',
    fontSize: '12px',
  },
  btn: {
    background: 'none',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: '#e0e0e0',
    cursor: 'pointer',
    padding: '2px 8px',
    fontSize: '14px',
    lineHeight: '1.4',
  },
  slider: {
    width: '80px',
    height: '4px',
    accentColor: '#1890ff',
  },
  zoomLabel: {
    color: '#a0a0a0',
    fontSize: '11px',
    minWidth: '32px',
    textAlign: 'center',
  },
  separator: {
    width: '1px',
    height: '16px',
    backgroundColor: 'var(--border-color)',
    margin: '0 2px',
  },
};
```

- [ ] **Step 3: 验证编译通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/views/overview/StationInfoCard.tsx frontend/src/components/views/overview/ViewportControls.tsx
git commit -m "feat(frontend): 新增 StationInfoCard 与 ViewportControls 组件"
```

---

### Task 5: 主容器与集成 — LineDiagram + OverviewView 接入

**Files:**
- Create: `frontend/src/components/views/overview/LineDiagram.tsx`
- Modify: `frontend/src/pages/OverviewView.tsx`
- Delete: `frontend/src/components/views/overview/TrainAnimation.tsx`

**Interfaces:**
- Consumes: Task 1 的类型和 Mock 数据，Task 2 的 useViewport，Task 3 的 SVG 组件，Task 4 的 UI 组件
- Produces: 可运行的完整交互式线路图

- [ ] **Step 1: 创建 LineDiagram.tsx 主容器**

创建 `frontend/src/components/views/overview/LineDiagram.tsx`：

```typescript
/**
 * LineDiagram — 交互式线路图主容器
 * 组装 SVG 画布、车站/区间/列车子组件、视口控制栏、信息卡片
 */
import { useRef, useState, useEffect, useCallback } from 'react';
import { useSimulationState } from '../../../context/SimulationContext';
import { useViewport } from '../../../hooks/useViewport';
import { mockLineData } from '../../../data/mockLineData';
import type { StationLayout, LineLayout } from '../../../types/simulation';
import TrackSegment from './TrackSegment';
import StationNode from './StationNode';
import TrainMarker from './TrainMarker';
import StationInfoCard from './StationInfoCard';
import ViewportControls from './ViewportControls';

export default function LineDiagram() {
  const { trains } = useSimulationState();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // 线路数据 (Mock 阶段, 后续从 state.lineLayout 读取)
  const [lineLayout] = useState<LineLayout>(mockLineData);

  // 悬停/选中的车站
  const [hoveredStation, setHoveredStation] = useState<string | null>(null);
  const [selectedStation, setSelectedStation] = useState<string | null>(null);
  const [cardPosition, setCardPosition] = useState({ x: 0, y: 0 });

  // 列车位置 (取第一列列车)
  const trainPosition = trains.length > 0 ? trains[0].position : undefined;

  // 视口管理
  const viewport = useViewport({
    trainPosition,
    totalLength: lineLayout.total_length,
    containerRef: svgRef,
    worldHeight: 80,
  });

  // 初始化: 加载 Mock 数据到 context (如果 context 中没有)
  // 后续后端就绪后改为 useEffect 从 API 获取

  // 判断是否显示站内详情 (缩放 >= 0.8 时显示)
  const showDetail = viewport.zoom >= 0.8;

  // 车站点击
  const handleStationClick = useCallback((stationId: string) => {
    setSelectedStation(prev => prev === stationId ? null : stationId);
    // 计算卡片位置: 转换为屏幕坐标
    if (svgRef.current && containerRef.current) {
      const svgRect = svgRef.current.getBoundingClientRect();
      const containerRect = containerRef.current.getBoundingClientRect();
      const station = lineLayout.stations.find(s => s.id === stationId);
      if (station) {
        // 简单的屏幕坐标映射
        const viewW = lineLayout.total_length / viewport.zoom;
        const screenX = ((station.chainage + station.length / 2 - parseFloat(viewport.viewBox.split(' ')[0])) / viewW) * svgRect.width;
        setCardPosition({
          x: Math.min(screenX, containerRect.width - 260),
          y: 10,
        });
      }
    }
  }, [lineLayout, viewport.zoom, viewport.viewBox]);

  // 车站悬停
  const handleStationHover = useCallback((stationId: string) => {
    setHoveredStation(stationId);
  }, []);

  const handleStationLeave = useCallback(() => {
    setHoveredStation(null);
  }, []);

  // 获取显示信息卡片的车站
  const activeStationId = selectedStation || hoveredStation;
  const activeStation = activeStationId
    ? lineLayout.stations.find(s => s.id === activeStationId) || null
    : null;

  // 正线 Y 坐标 (与 StationNode 中 baseY 一致)
  const mainTrackY = 40;

  return (
    <div ref={containerRef} className="panel" style={styles.container}>
      <div className="panel-title">🚇 线路图</div>

      {/* SVG 画布 */}
      <svg
        ref={svgRef}
        style={styles.svg}
        viewBox={viewport.viewBox}
        preserveAspectRatio="none"
        onWheel={viewport.handleWheel}
        onMouseDown={viewport.handleMouseDown}
        onMouseMove={viewport.handleMouseMove}
        onMouseUp={viewport.handleMouseUp}
        onMouseLeave={viewport.handleMouseUp}
      >
        {/* 区间轨道电路 */}
        {lineLayout.segments.map((seg) => (
          <TrackSegment key={`${seg.start_chainage}-${seg.end_chainage}`} segment={seg} y={mainTrackY} />
        ))}

        {/* 车站 */}
        {lineLayout.stations.map((station) => (
          <StationNode
            key={station.id}
            station={station}
            showDetail={showDetail}
            selected={selectedStation === station.id}
            onClick={handleStationClick}
            onMouseEnter={handleStationHover}
            onMouseLeave={handleStationLeave}
          />
        ))}

        {/* 列车 */}
        {trains.map((train) => (
          <TrainMarker key={train.id} train={train} trackY={mainTrackY} />
        ))}
      </svg>

      {/* 控制栏 */}
      <div style={styles.controlsWrap}>
        <ViewportControls
          zoom={viewport.zoom}
          followMode={viewport.followMode}
          onZoomChange={viewport.setZoom}
          onToggleFollow={viewport.toggleFollow}
          onFitAll={viewport.fitAll}
        />
      </div>

      {/* 车站信息卡片 */}
      {activeStation && (
        <StationInfoCard
          station={activeStation}
          position={cardPosition}
          onClose={() => { setSelectedStation(null); setHoveredStation(null); }}
        />
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'relative',
    height: '100%',
    overflow: 'hidden',
  },
  svg: {
    width: '100%',
    height: 'calc(100% - 30px)',
    cursor: 'grab',
    userSelect: 'none',
  },
  controlsWrap: {
    position: 'absolute',
    bottom: '8px',
    right: '8px',
  },
};
```

- [ ] **Step 2: 修改 OverviewView.tsx — 替换 TrainAnimation**

将 `frontend/src/pages/OverviewView.tsx` 中的 import 和使用处修改：

将:
```typescript
import TrainAnimation from '../components/views/overview/TrainAnimation';
```

改为:
```typescript
import LineDiagram from '../components/views/overview/LineDiagram';
```

将 JSX 中的:
```tsx
<TrainAnimation />
```

改为:
```tsx
<LineDiagram />
```

同时删除 `styles` 中不再需要的 `container: { height: '80px' }` 等 TrainAnimation 相关样式。由于 LineDiagram 自带面板样式且 `flex: 1`，`middleRow` 的样式无需改变。

- [ ] **Step 3: 删除旧 TrainAnimation.tsx**

```bash
git rm frontend/src/components/views/overview/TrainAnimation.tsx
```

- [ ] **Step 4: 验证编译通过**

Run: `cd frontend && npx tsc --noEmit`
Expected: 无类型错误

- [ ] **Step 5: 启动开发服务器验证效果**

Run: `cd frontend && npm run dev`

在浏览器中打开，验证：
1. 线路图正确显示 8 个车站和区间轨道电路色块
2. 缩放滑块可调节，滚轮可缩放
3. 拖拽可平移视图，拖拽后自动解除跟随
4. 点击跟随按钮可重新锁定
5. 悬停/点击车站显示信息卡片
6. 缩放较小时车站简化为方块，放大后显示股道详情
7. 点击"全线总览"按钮可缩放到全部车站可见

- [ ] **Step 6: 提交**

```bash
git add -A
git commit -m "feat(frontend): 实现交互式线路图主容器并集成到综合视图"
```
