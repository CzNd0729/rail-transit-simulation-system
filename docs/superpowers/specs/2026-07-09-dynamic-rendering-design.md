# 前端渲染动态化设计

> 日期: 2026-07-09 | 迭代: 一

## 1. 数据获取与动态参数

### 数据流
```
后端 /api/v1/config/line
  ↓
前端 useLineLayout hook（已有）
  ↓
lineLayout 存入 SimulationContext
  ↓
各组件从 context 读取并动态计算渲染参数
```

### 动态参数计算
```typescript
const totalLength = lineLayout.total_length;  // 从后端获取
const stations = lineLayout.stations;

// 动态过渡区长度
const minGap = Math.min(...stations.slice(1).map((s, i) => 
  s.chainage - (stations[i].chainage + stations[i].length)
));
const TRANSITION_LENGTH = Math.max(100, Math.min(500, minGap * 0.3));

// SVG viewBox
const viewBox = `${panX} 0 ${totalLength / zoom} 80`;

// 初始缩放
const initialZoom = containerWidth / totalLength;
```

## 2. 组件改造

### LineDiagram.tsx
- 移除硬编码 `TRANSITION_LENGTH = 500`
- 新增 `calcTransitionLength(stations)` 函数
- 区间段绘制：使用实际 `start_chainage` 和 `end_chainage`
- 车站绘制：使用实际 `chainage` 和 `length`

### StationNode.tsx
- 移除硬编码车站长度
- 站台矩形宽度 = `station.length`
- 车站轨道 Y 坐标保持 25/55，长度动态

### TrackSegment.tsx
- 区间轨道起止点 = 上一站 `chainage + length` 到下一站 `chainage`
- 过渡曲线长度动态计算

### useViewport.ts
- `totalLength` 从 `lineLayout.total_length` 获取
- 初始 zoom 根据容器宽度自动计算

## 3. 动态过渡区与贝塞尔曲线

### 过渡区长度计算
```typescript
function calcTransitionLength(stations: StationLayout[]): number {
  const gaps = stations.slice(1).map((s, i) => {
    const prevEnd = stations[i].chainage + stations[i].length;
    return s.chainage - prevEnd;
  });
  
  const minGap = Math.min(...gaps);
  return Math.max(100, Math.min(500, minGap * 0.3));
}
```

### 贝塞尔曲线调整
- 进站曲线：从 `station.chainage - TRANSITION_LENGTH` 到 `station.chainage`
- 出站曲线：从 `station.chainage + station.length` 到 `station.chainage + station.length + TRANSITION_LENGTH`
- 曲线控制点按比例调整

### 边界处理
- 首站无前向过渡区
- 末站无后向过渡区
- 站间距 < 200m 时，过渡区缩短为间距的 40%

## 4. 文件改动

- 修改 `components/views/overview/LineDiagram.tsx` — 动态计算过渡区
- 修改 `components/views/overview/StationNode.tsx` — 使用实际车站长度
- 修改 `components/views/overview/TrackSegment.tsx` — 动态区间绘制
- 修改 `hooks/useViewport.ts` — 动态 totalLength 和初始 zoom
