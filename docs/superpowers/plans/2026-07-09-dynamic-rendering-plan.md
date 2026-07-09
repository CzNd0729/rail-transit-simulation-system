# 前端渲染动态化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded rendering parameters with dynamic calculations based on backend line data.

**Architecture:** Extract line data from `SimulationContext.lineLayout`, calculate rendering parameters (transition length, viewBox, zoom) dynamically. Modify four components to use actual station/segment data instead of hardcoded values.

**Tech Stack:** React 18, TypeScript, SVG, ECharts

## Global Constraints

- No new npm dependencies
- TypeScript strict mode compliance
- Maintain backward compatibility (components work with or without lineLayout)
- Use existing CSS variables from index.css

---

### Task 1: useViewport 动态 totalLength 和初始 zoom

**Files:**
- Modify: `frontend/src/hooks/useViewport.ts`

- [ ] **Step 1: Read current useViewport**

```bash
cd frontend && cat src/hooks/useViewport.ts | head -50
```

Expected: See current hardcoded totalLength usage

- [ ] **Step 2: Update useViewport to accept totalLength prop**

```typescript
// useViewport.ts - add totalLength to props
interface UseViewportOptions {
  trainPosition?: number;
  totalLength: number; // 从外部传入
  containerRef: RefObject<SVGSVGElement>;
  worldHeight?: number;
}

export function useViewport(options: UseViewportOptions) {
  const { trainPosition, totalLength, containerRef, worldHeight = 80 } = options;

  // 初始 zoom：根据容器宽度自动计算
  const [zoom, setZoomState] = useState(() => {
    const containerWidth = containerRef.current?.clientWidth ?? 800;
    return Math.max(1, containerWidth / totalLength);
  });

  // ... rest of the hook remains the same
}
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/hooks/useViewport.ts
git commit -m "refactor: useViewport accepts dynamic totalLength"
```

---

### Task 2: LineDiagram 动态过渡区计算

**Files:**
- Modify: `frontend/src/components/views/overview/LineDiagram.tsx`

- [ ] **Step 1: Read current LineDiagram**

```bash
cd frontend && grep -n "TRANSITION_LENGTH" src/components/views/overview/LineDiagram.tsx
```

Expected: See hardcoded `TRANSITION_LENGTH = 500`

- [ ] **Step 2: Add calcTransitionLength function**

```typescript
// LineDiagram.tsx - add near top
/** 动态计算过渡区长度 */
function calcTransitionLength(stations: StationLayout[]): number {
  if (stations.length < 2) return 200;
  
  const gaps = stations.slice(1).map((s, i) => {
    const prevEnd = stations[i].chainage + stations[i].length;
    return s.chainage - prevEnd;
  });
  
  const minGap = Math.min(...gaps);
  
  // 站间距 < 200m 时，过渡区为间距的 40%
  if (minGap < 200) {
    return Math.max(50, minGap * 0.4);
  }
  
  // 否则为最小间距的 30%，限制在 100-500m
  return Math.max(100, Math.min(500, minGap * 0.3));
}
```

- [ ] **Step 3: Remove hardcoded TRANSITION_LENGTH and use dynamic calculation**

```typescript
// LineDiagram.tsx - in component
export default function LineDiagram() {
  const { trains, lineLayout } = useSimulationState();
  
  // ... existing code ...
  
  if (!lineLayout) {
    // ... loading state ...
  }
  
  // 动态计算过渡区长度
  const TRANSITION_LENGTH = calcTransitionLength(lineLayout.stations);
  
  // Use TRANSITION_LENGTH in Bezier curve generation
  // ... rest of component ...
}
```

- [ ] **Step 4: Update useViewport call to pass totalLength**

```typescript
// LineDiagram.tsx - update useViewport call
const viewport = useViewport({
  trainPosition,
  totalLength: lineLayout.total_length, // 从 lineLayout 获取
  containerRef: svgRef,
  worldHeight: 80,
});
```

- [ ] **Step 5: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 6: Run dev server and verify**

```bash
cd frontend && npm run dev
```

Expected: Line diagram renders with correct station positions and smooth transitions

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/views/overview/LineDiagram.tsx
git commit -m "feat: dynamic transition length calculation"
```

---

### Task 3: StationNode 使用实际车站长度

**Files:**
- Modify: `frontend/src/components/views/overview/StationNode.tsx`

- [ ] **Step 1: Read current StationNode**

```bash
cd frontend && grep -A 5 "width.*station" src/components/views/overview/StationNode.tsx
```

Expected: See station width usage

- [ ] **Step 2: Verify StationNode uses station.length**

Check that StationNode already uses `station.length` for platform rectangle width. If it uses hardcoded values, update to:

```typescript
// StationNode.tsx - ensure platform uses actual length
<rect
  x={station.chainage}
  y={STATION_Y.up + 4}
  width={station.length} // 使用实际车站长度
  height={STATION_Y.down - STATION_Y.up - 8}
  fill="#2a3a4a"
  stroke="rgba(100, 140, 180, 0.8)"
  strokeWidth={1.5}
  rx={3}
/>
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Visual verification**

Open dev server and verify station rectangles match actual station lengths (e.g., 西直门 longer than 灵境胡同)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/StationNode.tsx
git commit -m "feat: StationNode uses actual station length"
```

---

### Task 4: TrackSegment 动态区间绘制

**Files:**
- Modify: `frontend/src/components/views/overview/TrackSegment.tsx`

- [ ] **Step 1: Read current TrackSegment**

```bash
cd frontend && cat src/components/views/overview/TrackSegment.tsx
```

Expected: See current segment rendering logic

- [ ] **Step 2: Verify TrackSegment uses segment.start_chainage and end_chainage**

Ensure TrackSegment uses actual segment boundaries:

```typescript
// TrackSegment.tsx - ensure dynamic segment rendering
<line
  x1={segment.start_chainage}
  y1={TRACK_Y.up}
  x2={segment.end_chainage}
  y2={TRACK_Y.up}
  stroke="#e0e0e0"
  strokeWidth={4}
  strokeLinecap="round"
/>
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Visual verification**

Open dev server and verify segments connect properly between stations with correct lengths

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/TrackSegment.tsx
git commit -m "feat: TrackSegment uses actual segment boundaries"
```

---

### Task 5: 集成验证

**Files:**
- None (verification only)

- [ ] **Step 1: Start backend**

```bash
cd backend && uv run uvicorn sim_engine.app:app --reload --port 8000
```

Expected: Backend starts successfully

- [ ] **Step 2: Start frontend**

```bash
cd frontend && npm run dev
```

Expected: Frontend starts on http://localhost:5173

- [ ] **Step 3: Visual verification checklist**

Open browser and verify:
- [ ] All 24 Beijing Metro Line 4 stations visible
- [ ] Station names display correctly (安河桥北 to 公益西桥)
- [ ] Station rectangle widths match actual station lengths
- [ ] Segments connect stations with correct distances
- [ ] Bezier curves smoothly transition at station entry/exit
- [ ] Zoom controls work correctly for 18.6km track
- [ ] Initial view shows entire line (zoom auto-calculated)
- [ ] Train moves along track following curves
- [ ] No console errors

- [ ] **Step 4: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: complete dynamic rendering implementation"
```

- [ ] **Step 6: Push to dev**

```bash
git checkout dev
git merge feat/dynamic-rendering
git branch -d feat/dynamic-rendering
git push origin dev
```

Expected: Changes merged and pushed successfully
