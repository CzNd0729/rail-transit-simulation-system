# 综合视图可折叠面板 + 双向轨道 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add collapsible panels to OverviewView and render dual-track subway lines with station entry/exit transitions.

**Architecture:** Create a reusable CollapsiblePanel wrapper component with CSS transitions. Refactor SVG track components to support bidirectional rendering with Bezier curves for station transitions.

**Tech Stack:** React 18, TypeScript, CSS transitions, SVG paths

## Global Constraints

- Use existing CSS variables from index.css (--border-color, --bg-dark, etc.)
- Maintain backward compatibility: components work with or without new props
- No new npm dependencies
- TypeScript strict mode compliance

---

### Task 1: CollapsiblePanel 基础组件

**Files:**
- Create: `frontend/src/components/common/CollapsiblePanel.tsx`
- Create: `frontend/src/components/common/CollapsiblePanel.module.css`
- Test: `frontend/src/components/common/CollapsiblePanel.test.tsx`

**Interfaces:**
- Produces: `CollapsiblePanel` component with props:
  - `title: string`
  - `icon?: string`
  - `defaultOpen?: boolean` (default true)
  - `headerRight?: React.ReactNode`
  - `children: React.ReactNode`

- [ ] **Step 1: Write the failing test**

```typescript
// CollapsiblePanel.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import CollapsiblePanel from './CollapsiblePanel';

describe('CollapsiblePanel', () => {
  it('renders title and children when open', () => {
    render(
      <CollapsiblePanel title="Test Panel" icon="📊">
        <div>Content</div>
      </CollapsiblePanel>
    );
    expect(screen.getByText('📊 Test Panel')).toBeInTheDocument();
    expect(screen.getByText('Content')).toBeInTheDocument();
  });

  it('toggles collapse on click', () => {
    render(
      <CollapsiblePanel title="Test" defaultOpen={true}>
        <div>Content</div>
      </CollapsiblePanel>
    );
    const toggle = screen.getByRole('button');
    fireEvent.click(toggle);
    // After click, content should be hidden (max-height: 0)
    const content = screen.getByText('Content').parentElement;
    expect(content).toHaveStyle({ maxHeight: '0px' });
  });

  it('respects defaultOpen=false', () => {
    render(
      <CollapsiblePanel title="Test" defaultOpen={false}>
        <div>Content</div>
      </CollapsiblePanel>
    );
    const content = screen.getByText('Content').parentElement;
    expect(content).toHaveStyle({ maxHeight: '0px' });
  });

  it('renders headerRight content', () => {
    render(
      <CollapsiblePanel title="Test" headerRight={<span>Extra</span>}>
        <div>Content</div>
      </CollapsiblePanel>
    );
    expect(screen.getByText('Extra')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- CollapsiblePanel.test.tsx
```

Expected: FAIL - Cannot find module './CollapsiblePanel'

- [ ] **Step 3: Write minimal implementation**

```typescript
// CollapsiblePanel.tsx
import { useState } from 'react';
import styles from './CollapsiblePanel.module.css';

interface CollapsiblePanelProps {
  title: string;
  icon?: string;
  defaultOpen?: boolean;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
}

export default function CollapsiblePanel({
  title,
  icon,
  defaultOpen = true,
  headerRight,
  children,
}: CollapsiblePanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <button
          className={styles.toggle}
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Collapse' : 'Expand'}
        >
          <span className={`${styles.arrow} ${isOpen ? styles.arrowOpen : ''}`}>
            ▶
          </span>
          {icon && <span className={styles.icon}>{icon}</span>}
          <span className={styles.title}>{title}</span>
        </button>
        {headerRight && <div className={styles.headerRight}>{headerRight}</div>}
      </div>
      <div
        className={styles.content}
        style={{ maxHeight: isOpen ? '2000px' : '0px' }}
      >
        {children}
      </div>
    </div>
  );
}
```

```css
/* CollapsiblePanel.module.css */
.container {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background: var(--bg-dark);
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border-color);
}

.toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 0;
  font-size: 14px;
}

.arrow {
  display: inline-block;
  transition: transform 0.2s ease;
  font-size: 10px;
}

.arrowOpen {
  transform: rotate(90deg);
}

.icon {
  font-size: 16px;
}

.title {
  font-weight: 500;
}

.headerRight {
  display: flex;
  align-items: center;
  gap: 8px;
}

.content {
  max-height: 2000px;
  overflow: hidden;
  transition: max-height 0.2s ease-in-out;
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- CollapsiblePanel.test.tsx
```

Expected: PASS - All 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/common/CollapsiblePanel.tsx frontend/src/components/common/CollapsiblePanel.module.css frontend/src/components/common/CollapsiblePanel.test.tsx
git commit -m "feat: add CollapsiblePanel component"
```

---

### Task 2: OverviewView 集成 CollapsiblePanel

**Files:**
- Modify: `frontend/src/pages/OverviewView.tsx`

**Interfaces:**
- Consumes: `CollapsiblePanel` from Task 1
- Produces: Updated OverviewView with collapsible sections

- [ ] **Step 1: Read current OverviewView structure**

```bash
cd frontend && cat src/pages/OverviewView.tsx
```

Expected: See current layout with StatusCards, SubsystemIndicators, LineProfile, LineDiagram, SpeedPositionCurve

- [ ] **Step 2: Wrap components with CollapsiblePanel**

```typescript
// OverviewView.tsx - key changes
import CollapsiblePanel from '../components/common/CollapsiblePanel';

export default function OverviewView() {
  return (
    <div style={styles.container}>
      {/* StatusCards - 不折叠 */}
      <StatusCards />

      {/* SubsystemIndicators - 可折叠 */}
      <CollapsiblePanel title="子系统状态" icon="🔧" defaultOpen={true}>
        <SubsystemIndicators />
      </CollapsiblePanel>

      {/* LineProfile - 可折叠 */}
      <CollapsiblePanel title="线路纵断面" icon="📈" defaultOpen={true}>
        <div style={styles.chartWrapper}>
          <LineProfile />
        </div>
      </CollapsiblePanel>

      {/* LineDiagram - 可折叠 */}
      <CollapsiblePanel title="线路图" icon="🚇" defaultOpen={true}>
        <div style={styles.chartWrapper}>
          <LineDiagram />
        </div>
      </CollapsiblePanel>

      {/* SpeedPositionCurve - 可折叠 */}
      <CollapsiblePanel title="速度-位置曲线" icon="📊" defaultOpen={true}>
        <div style={styles.chartWrapper}>
          <SpeedPositionCurve />
        </div>
      </CollapsiblePanel>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '12px',
    height: '100%',
    overflowY: 'auto',
  },
  chartWrapper: {
    height: '300px',
    padding: '12px',
  },
};
```

- [ ] **Step 3: Run dev server and verify**

```bash
cd frontend && npm run dev
```

Expected: OverviewView shows collapsible panels, clicking arrows toggles visibility with smooth animation

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/OverviewView.tsx
git commit -m "feat: integrate CollapsiblePanel into OverviewView"
```

---

### Task 3: TrackSegment 双向轨道支持

**Files:**
- Modify: `frontend/src/components/views/overview/TrackSegment.tsx`
- Test: `frontend/src/components/views/overview/TrackSegment.test.tsx`

**Interfaces:**
- Consumes: `InterStationSegment` type, station positions from `LineLayout`
- Produces: Updated TrackSegment with `direction` prop

- [ ] **Step 1: Write the failing test**

```typescript
// TrackSegment.test.tsx
import { render } from '@testing-library/react';
import TrackSegment from './TrackSegment';
import type { InterStationSegment } from '../../../types/simulation';

const mockSegment: InterStationSegment = {
  start: 0,
  end: 1000,
  circuits: [],
};

describe('TrackSegment', () => {
  it('renders single track when no direction specified', () => {
    const { container } = render(<TrackSegment segment={mockSegment} />);
    const lines = container.querySelectorAll('line');
    expect(lines.length).toBe(1); // Single track at Y=40
  });

  it('renders dual tracks when direction specified', () => {
    const { container } = render(
      <TrackSegment segment={mockSegment} direction="up" />
    );
    const lines = container.querySelectorAll('line');
    expect(lines.length).toBe(2); // Up and down tracks
  });

  it('positions up track at Y=35', () => {
    const { container } = render(
      <TrackSegment segment={mockSegment} direction="up" />
    );
    const upLine = container.querySelector('line[data-direction="up"]');
    expect(upLine?.getAttribute('y1')).toBe('35');
  });

  it('positions down track at Y=45', () => {
    const { container } = render(
      <TrackSegment segment={mockSegment} direction="up" />
    );
    const downLine = container.querySelector('line[data-direction="down"]');
    expect(downLine?.getAttribute('y1')).toBe('45');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- TrackSegment.test.tsx
```

Expected: FAIL - direction prop not supported

- [ ] **Step 3: Update TrackSegment to support dual tracks**

```typescript
// TrackSegment.tsx - key changes
interface TrackSegmentProps {
  segment: InterStationSegment;
  direction?: 'up' | 'down'; // New prop
  isStationArea?: boolean; // Whether this segment is near a station
}

const TRACK_Y_INTERVAL = { up: 35, down: 45 };
const TRACK_Y_STATION = { up: 25, down: 55 };

export default function TrackSegment({ segment, direction, isStationArea }: TrackSegmentProps) {
  const yCoords = isStationArea ? TRACK_Y_STATION : TRACK_Y_INTERVAL;
  
  if (!direction) {
    // Backward compatibility: single track
    return (
      <line
        x1={segment.start}
        y1={40}
        x2={segment.end}
        y2={40}
        stroke="#e0e0e0"
        strokeWidth={4}
      />
    );
  }

  // Dual track rendering
  return (
    <g>
      {/* Up track */}
      <line
        data-direction="up"
        x1={segment.start}
        y1={yCoords.up}
        x2={segment.end}
        y2={yCoords.up}
        stroke="#e0e0e0"
        strokeWidth={4}
      />
      {/* Down track */}
      <line
        data-direction="down"
        x1={segment.start}
        y1={yCoords.down}
        x2={segment.end}
        y2={yCoords.down}
        stroke="#e0e0e0"
        strokeWidth={4}
      />
    </g>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- TrackSegment.test.tsx
```

Expected: PASS - All 4 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/TrackSegment.tsx frontend/src/components/views/overview/TrackSegment.test.tsx
git commit -m "feat: add dual-track support to TrackSegment"
```

---

### Task 4: StationNode 双向轨道 + 站台布局

**Files:**
- Modify: `frontend/src/components/views/overview/StationNode.tsx`
- Test: `frontend/src/components/views/overview/StationNode.test.tsx`

**Interfaces:**
- Consumes: `Station` type, track Y coordinates (up=25, down=55 at station)
- Produces: Updated StationNode with centered platform between dual tracks

- [ ] **Step 1: Write the failing test**

```typescript
// StationNode.test.tsx
import { render } from '@testing-library/react';
import StationNode from './StationNode';
import type { Station } from '../../../types/simulation';

const mockStation: Station = {
  id: 'ST01',
  name: 'Test Station',
  chainage: 1000,
  length: 200,
  dwellTime: 30,
  isTerminus: false,
};

describe('StationNode', () => {
  it('renders platform centered at Y=40', () => {
    const { container } = render(<StationNode station={mockStation} />);
    const platform = container.querySelector('rect[data-role="platform"]');
    const y = parseFloat(platform?.getAttribute('y') || '0');
    const height = parseFloat(platform?.getAttribute('height') || '0');
    expect(y + height / 2).toBe(40);
  });

  it('renders up track at Y=25', () => {
    const { container } = render(<StationNode station={mockStation} />);
    const upTrack = container.querySelector('line[data-direction="up"]');
    expect(upTrack?.getAttribute('y1')).toBe('25');
  });

  it('renders down track at Y=55', () => {
    const { container } = render(<StationNode station={mockStation} />);
    const downTrack = container.querySelector('line[data-direction="down"]');
    expect(downTrack?.getAttribute('y1')).toBe('55');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- StationNode.test.tsx
```

Expected: FAIL - station layout not updated

- [ ] **Step 3: Update StationNode layout**

```typescript
// StationNode.tsx - key changes
const STATION_Y = {
  up: 25,
  down: 55,
  platform: 40,
};

export default function StationNode({ station }: StationNodeProps) {
  const x = station.chainage;
  const width = station.length;
  const platformHeight = 20;

  return (
    <g>
      {/* Platform centered at Y=40 */}
      <rect
        data-role="platform"
        x={x}
        y={STATION_Y.platform - platformHeight / 2}
        width={width}
        height={platformHeight}
        fill="#3a4a5a"
        stroke="#5a6a7a"
        strokeWidth={1}
        rx={4}
      />

      {/* Up track above platform */}
      <line
        data-direction="up"
        x1={x}
        y1={STATION_Y.up}
        x2={x + width}
        y2={STATION_Y.up}
        stroke="#e0e0e0"
        strokeWidth={4}
      />

      {/* Down track below platform */}
      <line
        data-direction="down"
        x1={x}
        y1={STATION_Y.down}
        x2={x + width}
        y2={STATION_Y.down}
        stroke="#e0e0e0"
        strokeWidth={4}
      />

      {/* Station name label */}
      <text
        x={x + width / 2}
        y={STATION_Y.platform}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#fff"
        fontSize={12}
      >
        {station.name}
      </text>
    </g>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- StationNode.test.tsx
```

Expected: PASS - All 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/StationNode.tsx frontend/src/components/views/overview/StationNode.test.tsx
git commit -m "feat: update StationNode for dual-track layout"
```

---

### Task 5: TrainMarker 方向支持

**Files:**
- Modify: `frontend/src/components/views/overview/TrainMarker.tsx`
- Test: `frontend/src/components/views/overview/TrainMarker.test.tsx`

**Interfaces:**
- Consumes: `Train` type with optional `direction` field
- Produces: Updated TrainMarker positioning on correct track

- [ ] **Step 1: Write the failing test**

```typescript
// TrainMarker.test.tsx
import { render } from '@testing-library/react';
import TrainMarker from './TrainMarker';
import type { Train } from '../../../types/simulation';

const mockTrain: Train = {
  id: 'T001',
  position: 500,
  speed: 60,
  acceleration: 0,
  direction: 'up',
  // ... other fields
};

describe('TrainMarker', () => {
  it('positions on up track (Y=35) when direction=up', () => {
    const { container } = render(<TrainMarker train={mockTrain} />);
    const marker = container.querySelector('g[data-role="train"]');
    const transform = marker?.getAttribute('transform');
    expect(transform).toContain('translate(500, 35)');
  });

  it('positions on down track (Y=45) when direction=down', () => {
    const trainDown = { ...mockTrain, direction: 'down' as const };
    const { container } = render(<TrainMarker train={trainDown} />);
    const marker = container.querySelector('g[data-role="train"]');
    const transform = marker?.getAttribute('transform');
    expect(transform).toContain('translate(500, 45)');
  });

  it('defaults to Y=35 when no direction', () => {
    const trainNoDir = { ...mockTrain, direction: undefined };
    const { container } = render(<TrainMarker train={trainNoDir} />);
    const marker = container.querySelector('g[data-role="train"]');
    const transform = marker?.getAttribute('transform');
    expect(transform).toContain('translate(500, 35)');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- TrainMarker.test.tsx
```

Expected: FAIL - direction not supported

- [ ] **Step 3: Update TrainMarker to use direction**

```typescript
// TrainMarker.tsx - key changes
const TRAIN_Y = {
  up: 35,
  down: 45,
  default: 35,
};

export default function TrainMarker({ train }: TrainMarkerProps) {
  const y = train.direction ? TRAIN_Y[train.direction] : TRAIN_Y.default;

  return (
    <g data-role="train" transform={`translate(${train.position}, ${y})`}>
      {/* Train icon */}
      <rect
        x={-15}
        y={-8}
        width={30}
        height={16}
        fill="#ff6b6b"
        rx={4}
      />
      <text
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#fff"
        fontSize={10}
        fontWeight="bold"
      >
        🚇
      </text>
      {/* Speed label */}
      <text
        y={-12}
        textAnchor="middle"
        fill="#fff"
        fontSize={10}
      >
        {train.speed.toFixed(0)} km/h
      </text>
    </g>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm test -- TrainMarker.test.tsx
```

Expected: PASS - All 3 tests pass

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/views/overview/TrainMarker.tsx frontend/src/components/views/overview/TrainMarker.test.tsx
git commit -m "feat: add direction support to TrainMarker"
```

---

### Task 6: LineDiagram 双向轨道集成

**Files:**
- Modify: `frontend/src/components/views/overview/LineDiagram.tsx`

**Interfaces:**
- Consumes: Updated TrackSegment, StationNode, TrainMarker from Tasks 3-5
- Consumes: LineLayout with station positions
- Produces: Complete dual-track rendering with Bezier transitions

- [ ] **Step 1: Read current LineDiagram structure**

```bash
cd frontend && cat src/components/views/overview/LineDiagram.tsx | head -100
```

Expected: See current SVG rendering logic

- [ ] **Step 2: Add Bezier transition paths**

```typescript
// LineDiagram.tsx - add transition path helper
function generateTransitionPath(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  direction: 'up' | 'down'
): string {
  const midX = (startX + endX) / 2;
  // Bezier curve with control points
  return `M ${startX},${startY} C ${midX},${startY} ${midX},${endY} ${endX},${endY}`;
}

// In render:
{segments.map((seg, idx) => {
  const nextStation = lineLayout.stations.find(
    s => s.chainage > seg.end && s.chainage < seg.end + 500
  );

  return (
    <g key={idx}>
      {/* Main segment */}
      <TrackSegment segment={seg} direction="up" />
      
      {/* Transition to station */}
      {nextStation && (
        <>
          <path
            d={generateTransitionPath(
              seg.end, 35,
              nextStation.chainage, 25,
              'up'
            )}
            stroke="#e0e0e0"
            strokeWidth={4}
            fill="none"
          />
          <path
            d={generateTransitionPath(
              seg.end, 45,
              nextStation.chainage, 55,
              'down'
            )}
            stroke="#e0e0e0"
            strokeWidth={4}
            fill="none"
          />
        </>
      )}
    </g>
  );
})}
```

- [ ] **Step 3: Run dev server and verify visual output**

```bash
cd frontend && npm run dev
```

Expected: Dual tracks visible with smooth Bezier curves at station entries/exits

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/views/overview/LineDiagram.tsx
git commit -m "feat: integrate dual-track rendering with Bezier transitions"
```

---

### Task 7: 端到端验证

**Files:**
- Test: `frontend/src/pages/OverviewView.test.tsx`

- [ ] **Step 1: Write integration test**

```typescript
// OverviewView.test.tsx
import { render, screen } from '@testing-library/react';
import { SimulationProvider } from '../context/SimulationContext';
import OverviewView from './OverviewView';

describe('OverviewView', () => {
  it('renders all collapsible panels', () => {
    render(
      <SimulationProvider>
        <OverviewView />
      </SimulationProvider>
    );
    
    expect(screen.getByText('子系统状态')).toBeInTheDocument();
    expect(screen.getByText('线路纵断面')).toBeInTheDocument();
    expect(screen.getByText('线路图')).toBeInTheDocument();
    expect(screen.getByText('速度-位置曲线')).toBeInTheDocument();
  });

  it('collapses panel on toggle click', () => {
    render(
      <SimulationProvider>
        <OverviewView />
      </SimulationProvider>
    );
    
    const toggle = screen.getByLabelText('Collapse');
    toggle.click();
    
    // Content should be hidden
    expect(toggle.getAttribute('aria-label')).toBe('Expand');
  });
});
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd frontend && npm test -- OverviewView.test.tsx
```

Expected: PASS - All tests pass

- [ ] **Step 3: Run all tests**

```bash
cd frontend && npm test
```

Expected: All tests pass, no regressions

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/OverviewView.test.tsx
git commit -m "test: add OverviewView integration tests"
```

- [ ] **Step 5: Visual verification checklist**

Open dev server and verify:
- [ ] All panels show with triangle toggers
- [ ] Clicking triangles smoothly collapses/expands content
- [ ] Dual tracks visible in LineDiagram
- [ ] Bezier curves smooth at station entries
- [ ] Train markers on correct track based on direction
- [ ] No console errors
- [ ] Responsive layout maintains usability

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: complete collapsible panels and dual-track implementation"
```
