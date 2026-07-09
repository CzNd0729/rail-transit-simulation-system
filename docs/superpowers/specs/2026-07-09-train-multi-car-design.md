# 列车多车厢可视化设计

> 日期: 2026-07-09 | 迭代: 一

## 1. 列车渲染

### 视觉结构
```
列车（120m 总长，6 节车厢）：
┌────┬────┬────┬────┬────┬────┐▶
│ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │
└────┴────┴────┴────┴────┴────┘

每节车厢：20m 长
车身高度：12px（SVG 世界坐标）
填充色：跟随工况（牵引 #1890ff / 惰行 #faad14 / 制动 #ff4d4f）
车头箭头：小三角指示运行方向
```

### SVG 渲染
- 6 个 `<rect>` 车厢段，每个 20m 宽，间距 1px
- 车身 Y 坐标：上行轨道 Y=35，高度 12px（Y=29 到 Y=41）
- 车头位置绘制 `<polygon>` 小三角（宽 4m，高 8px）

## 2. 列车定位

### 运行时定位
- 列车中心点 = `train.position`（后端推送的公里标）
- 车身范围：`[position - 60, position + 60]`（前后各 60m）
- Y 坐标：上行轨道 Y=35

### 停车居中逻辑
```typescript
// 当列车停靠在车站时
const stationCenter = station.chainage + station.length / 2;
train.position = stationCenter;

// 车身范围：[stationCenter - 60, stationCenter + 60]
// 确保 station.length >= 120m（列车完全在车站内）
```

### TrainMarker 组件改造
```typescript
interface TrainMarkerProps {
  train: TrainState;
  direction?: 'up' | 'down';
}

const TRAIN_LENGTH = 120; // 列车总长 (m)
const CAR_COUNT = 6;
const CAR_LENGTH = TRAIN_LENGTH / CAR_COUNT; // 20m
const CAR_GAP = 1; // 车厢间距 (m)
const TRAIN_HEIGHT = 12; // 车身高度 (px)

const MODE_COLORS = {
  traction: '#1890ff',
  coasting: '#faad14',
  braking: '#ff4d4f',
};

export default function TrainMarker({ train, direction = 'up' }: TrainMarkerProps) {
  const y = direction === 'up' ? 35 : 45;
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

## 3. 文件改动

- 修改 `components/views/overview/TrainMarker.tsx` — 多车厢渲染
- 修改 `components/views/overview/LineDiagram.tsx` — 传递 train 对象
