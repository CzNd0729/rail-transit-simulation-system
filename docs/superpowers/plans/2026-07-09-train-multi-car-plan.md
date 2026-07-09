# 列车多车厢可视化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render train as 6-car segments (120m total) with proper positioning and station-centering logic.

**Architecture:** Refactor TrainMarker component to draw 6 rectangles representing train cars. Position train centered on `train.position`, ensure visual accuracy when stopped at stations.

**Tech Stack:** React 18, TypeScript, SVG

## Global Constraints

- Train length: 120m (fixed)
- Car count: 6
- Car length: 20m each
- Track: up track (Y=35) only for now
- No new dependencies
- TypeScript strict mode

---

### Task 1: TrainMarker 多车厢渲染

**Files:**
- Modify: `frontend/src/components/views/overview/TrainMarker.tsx`

**Interfaces:**
- Consumes: `TrainState` type (position, mode, speed)
- Consumes: `direction` prop ('up' | 'down')
- Produces: Updated TrainMarker with 6-car rendering

- [ ] **Step 1: Read current TrainMarker**

```bash
cd frontend && cat src/components/views/overview/TrainMarker.tsx
```

Expected: See current single-marker implementation

- [ ] **Step 2: Rewrite TrainMarker with multi-car rendering**

```typescript
/**
 * TrainMarker — 列车多车厢 SVG 渲染
 * 120m 总长，6 节车厢，跟随工况着色
 */
import type { TrainState } from '../../../types/simulation';

interface TrainMarkerProps {
  train: TrainState;
  direction?: 'up' | 'down';
}

const TRAIN_LENGTH = 120; // 列车总长 (m)
const CAR_COUNT = 6;
const CAR_LENGTH = TRAIN_LENGTH / CAR_COUNT; // 20m
const CAR_GAP = 1; // 车厢间距 (m)
const TRAIN_HEIGHT = 12; // 车身高度 (px)

const MODE_COLORS: Record<string, string> = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

const TRACK_Y = {
  up: 35,
  down: 45,
};

export default function TrainMarker({ train, direction = 'up' }: TrainMarkerProps) {
  const y = TRACK_Y[direction];
  const color = MODE_COLORS[train.mode] || '#999';
  const trainStart = train.position - TRAIN_LENGTH / 2;

  return (
    <g>
      {/* 6 节车厢 */}
      {Array.from({ length: CAR_COUNT }).map((_, i) => {
        const carX = trainStart + i * (CAR_LENGTH + CAR_GAP);
        return (
          <rect
            key={i}
            x={carX}
            y={y - TRAIN_HEIGHT / 2}
            width={CAR_LENGTH - CAR_GAP}
            height={TRAIN_HEIGHT}
            fill={color}
            rx={2}
          />
        );
      })}

      {/* 车头箭头 */}
      <polygon
        points={`${trainStart + TRAIN_LENGTH},${y - 4} ${trainStart + TRAIN_LENGTH + 4},${y} ${trainStart + TRAIN_LENGTH},${y + 4}`}
        fill={color}
      />

      {/* 速度标注 */}
      <text
        x={train.position}
        y={y - TRAIN_HEIGHT / 2 - 4}
        textAnchor="middle"
        fontSize={8}
        fill={color}
        fontWeight={600}
      >
        {train.speed.toFixed(0)}km/h
      </text>
    </g>
  );
}
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Run dev server and verify visually**

```bash
cd frontend && npm run dev
```

Expected: Train renders as 6 colored rectangles with arrow, moves smoothly along track

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/TrainMarker.tsx
git commit -m "feat: render train as 6-car segments"
```

---

### Task 2: LineDiagram 集成

**Files:**
- Modify: `frontend/src/components/views/overview/LineDiagram.tsx`

- [ ] **Step 1: Verify LineDiagram passes train object correctly**

```bash
cd frontend && grep -A 5 "TrainMarker" src/components/views/overview/LineDiagram.tsx
```

Expected: See TrainMarker receiving `train` prop

- [ ] **Step 2: Ensure direction prop is passed**

If not already present, update TrainMarker usage:

```typescript
{trains.map((train) => (
  <TrainMarker key={train.id} train={train} direction="up" />
))}
```

- [ ] **Step 3: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 4: Visual verification checklist**

Open dev server and verify:
- [ ] Train shows as 6 rectangles (not single marker)
- [ ] Colors change with mode (blue/yellow/red)
- [ ] Arrow points in running direction
- [ ] Speed label displays above train
- [ ] Train stays on up track (Y=35)
- [ ] Train stops centered in station (when simulation pauses at station)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/LineDiagram.tsx
git commit -m "feat: integrate multi-car train in LineDiagram"
```
