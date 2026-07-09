# 综合视图可折叠面板 + 双向轨道设计

> 日期: 2026-07-09 | 迭代: 一

## 1. CollapsiblePanel 组件

### 接口
```typescript
interface CollapsiblePanelProps {
  title: string;
  icon?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  headerRight?: React.ReactNode;
}
```

### 行为
- 左侧三角 `▶`/`▼` 点击切换展开/折叠
- 内容区 `max-height` 过渡动画 200ms ease-in-out
- 折叠后仅显示标题栏（32px）
- `defaultOpen` 默认 `true`

### OverviewView 应用
| 区块 | 可折叠 | 默认 |
|------|--------|------|
| StatusCards | 否 | 始终显示 |
| SubsystemIndicators | 是 | 开 |
| LineProfile | 是 | 开 |
| LineDiagram | 是 | 开 |
| SpeedPositionCurve | 是 | 开 |

## 2. 双向轨道渲染

### 坐标系统（SVG 世界坐标）
```
区间段（站间）：
  上行轨 Y = 35
  下行轨 Y = 45
  间距 10

车站区域：
  上行轨 Y = 25（向外偏移）
  下行轨 Y = 55（向外偏移）
  间距 30，站台居中 Y=40
```

### 进出站贝塞尔过渡
```
进站（前 500m 分叉）：
  上行：M x,35 C x+200,35 x+300,25 x+500,25
  下行：M x,45 C x+200,45 x+300,55 x+500,55

出站（后 500m 回归）：
  上行：M x,25 C x+200,25 x+300,35 x+500,35
  下行：M x,55 C x+200,55 x+300,45 x+500,45
```

### 组件改造

**TrackSegment**
- 新增 `direction: 'up' | 'down'` prop
- 区间段：直线 `<line>` Y=35 或 45
- 进站/出站区段：`<path>` 贝塞尔曲线
- 轨道电路色块跟随对应轨道

**StationNode**
- 站台矩形居中 Y=40，高度 20
- 上行正线 Y=25 从上方经过
- 下行正线 Y=55 从下方经过

**TrainMarker**
- 根据 `train.direction` 选择 Y=35（上行）或 Y=45（下行）
- 无 direction 字段时默认 Y=35

### 文件改动
- 新增 `components/common/CollapsiblePanel.tsx`
- 修改 `pages/OverviewView.tsx` — 包裹 CollapsiblePanel
- 修改 `components/views/overview/TrackSegment.tsx` — 双向渲染
- 修改 `components/views/overview/StationNode.tsx` — 站台居中
- 修改 `components/views/overview/TrainMarker.tsx` — direction 支持
