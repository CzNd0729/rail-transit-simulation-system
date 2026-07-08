# TrackView 轨道视图详细设计

> 日期: 2026-07-08 | 迭代: 一 | 状态: 设计完成

## 概述

在现有 `TrackView` 页面上，使用 `mockLineData` 和 `SimulationContext` 中的列车位置数据，将三个占位符子组件改造为真实数据驱动的可视化组件。

## 整体布局（不变）

```
┌──────────────────────────────────────────────────────────────┐
│ TrackView                                                     │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ LineProfileDetail (ECharts 综合剖面图)    flex: 1, ~50%   │ │
│ └──────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────┬─────────────────────────────┐ │
│ │ OccupancyDisplay           │ SwitchStatus                │ │
│ │ SVG 轨道条带图              │ Mock 道岔列表                 │ │
│ │ flex: 1, ~40%              │ flex: 1, ~40%               │ │
│ └────────────────────────────┴─────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 组件树（不变）

```
TrackView.tsx
├── LineProfileDetail.tsx  ← 重写：从占位符 → ECharts 双Y轴组合图
├── OccupancyDisplay.tsx   ← 增强：从空状态网格 → SVG 轨道条带图
└── SwitchStatus.tsx       ← 增强：从空状态 → mock 数据列表
```

## 数据来源

- **线路几何数据**: `mockLineData.ts` — stations (8站), segments (7区间含 circuits)
- **列车位置**: `SimulationContext.trains[0].position` — 每 100ms 更新
- **道岔数据**: `mockLineData.ts` 新增 `mockSwitches` 导出 (8个静态道岔)
- **不新增 mock 数据文件**，不修改 `SimulationContext` reducer

---

## 组件一：LineProfileDetail — ECharts 综合剖面图

### 图表配置

| 配置项 | 内容 |
|--------|------|
| 类型 | 双 Y 轴多系列图 |
| X 轴 | 公里标 (m)，范围 0 ~ total_length |
| 左 Y 轴 | 坡度 (‰) |
| 右 Y 轴 | 限速 (km/h)，范围 0 ~ 100 |

### 数据系列

| 系列 | Y轴 | 渲染 | 数据来源 |
|------|-----|------|---------|
| 坡度阶梯线 | 左 | 蓝色填充面积图 (`areaStyle`) | `segments[].gradient` 构造阶梯坐标 |
| 限速阶梯线 | 右 | 红色虚线 (`type: 'dashed'`) | `segments[].speed_limit` 构造阶梯坐标 |

### 标注

| 标注 | 方式 | 数据来源 |
|------|------|---------|
| 车站位置 | 8 条竖虚线 (`markLine`) + 站名 label | `stations[].chainage`, `stations[].name` |
| 隧道段 | 灰色半透明矩形 (`markArea`) | `segments[]` 中 `is_tunnel === true` 的起止范围 |
| 列车位置 | 1 条红色竖实线 (`markLine`) | `context.trains[0].position`，每 100ms 更新 |

### 阶梯坐标构造

由于 ECharts 不支持原生阶梯函数，需将每段数据展开为两个点（起点+终点），使分段呈现阶梯状：

```typescript
// 例: [{ start: 0, end: 500, value: 5 }] → [[0,5], [500,5]]
function toStepData(segments: Segment[], field: keyof Segment): [number, number][] {
  const result: [number, number][] = [];
  for (const seg of segments) {
    result.push([seg.start_chainage, seg[field]]);
    result.push([seg.end_chainage, seg[field]]);
  }
  return result;
}
```

### 动态更新策略

- `markLine` 列车位置通过 `useSimulationState()` 读取 `trains[0]?.position`
- 使用 `useEffect` + `setInterval` (100ms) 更新 ECharts 实例的 `markLine` 数据
- 组件卸载时清理 interval

---

## 组件二：OccupancyDisplay — SVG 轨道条带图

### 渲染方式

内联 SVG（无额外依赖），水平条带布局。

### 视觉结构

```
公里标:  0m      1800m     3500m    5200m     6800m    8500m   10200m  12200m
         ├────────┼────────┼────────┼────────┼────────┼────────┼────────┤
正线:    │■■■■■■■■│■■■■■■■■│■■■■■■■■│■■■■■■■■│■■■■■■■■│■■■■■■■■│■■■■■■■■│
车站:    [ST01]  [ST02]  [ST03]  [ST04]  [ST05]  [ST06]  [ST07]  [ST08]
```

### 颜色编码（暗色主题）

| 状态 | 填充色 | 描边色 |
|------|--------|--------|
| 空闲 | `#1a3a1a` | `#2a5a2a` |
| 占用 | `#4a1a1a` | `#8a2a2a` |

### 条带图元素

- **区段列**: 每个 `TrackCircuit` 一个 `<rect>`，宽度 = 公里标跨度比例，间距 2px
- **车站标签**: 每个 `StationLayout` 一个 `<text>`，位置 = 车站 chainage 对应比例坐标
- **列车图标**: 1 个 `<text>🚇</text>` 绝对定位于 `trains[0].position` 对应 X 坐标
- **公里标尺**: 顶部水平刻度线 + 数字标注（0, 2000, 4000, ...）

### 交互

| 操作 | 行为 |
|------|------|
| hover 电路块 | `<title>` 原生 SVG tooltip：电路 ID、公里标范围、占用状态 |
| hover 车站标签 | `<title>` 原生 SVG tooltip：站名 |

### SVG 坐标映射

- `viewBox="0 0 {total_length} 120"` — X 轴直接映射公里标（1:1），Y 轴分上下两轨
- 正线 Y 范围: 20~50, 车站标签 Y: 60~80, 公里标尺 Y: 5~15
- SVG 容器 100% 宽度 + 固定高度 200px，`preserveAspectRatio="none"` 使 X 方向自适应拉伸

### 数据映射

```typescript
// 从 mockLineData.segments[] 展平所有 circuits，初始占用状态来自 mockLineData
const allCircuits = mockLineData.segments.flatMap(seg => seg.circuits);
```

### 动态更新

- 初始状态: 使用 mockLineData 中 circuits 的 `occupied` 值（已有部分为 true）
- 占用状态轮换: 每 500ms 随机选取 1-3 个电路切换 `occupied` 状态（模拟列车移动）
- 列车位置: 从 `context.trains[0].position` 实时读取，映射为 SVG X 坐标
- 使用 `useState` 管理电路占用数组，`useEffect` + `setInterval` (500ms) 驱动轮换

---

## 组件三：SwitchStatus — Mock 道岔列表

### 数据策略

迭代一不实现道岔逻辑，全部使用静态 mock 数据。

在 `mockLineData.ts` 中新增导出：

```typescript
export const mockSwitches: Switch[] = [
  { id: 'SW01', chainage: 100,  type: 'single',    normal_direction: 'ST01→ST02',
    reverse_direction: '侧线1', lateral_speed_limit: 25, state: 'normal' },
  { id: 'SW02', chainage: 1900, type: 'single',    normal_direction: 'ST02→ST03',
    reverse_direction: '侧线1', lateral_speed_limit: 25, state: 'normal' },
  { id: 'SW03', chainage: 3600, type: 'crossover', normal_direction: '上行→下行',
    reverse_direction: '上行→上行', lateral_speed_limit: 30, state: 'reverse' },
  { id: 'SW04', chainage: 5300, type: 'single',    normal_direction: 'ST04→ST05',
    reverse_direction: '侧线2', lateral_speed_limit: 25, state: 'normal' },
  { id: 'SW05', chainage: 6900, type: 'single',    normal_direction: 'ST05→ST06',
    reverse_direction: '侧线1', lateral_speed_limit: 25, state: 'transitioning' },
  { id: 'SW06', chainage: 8600, type: 'single',    normal_direction: 'ST06→ST07',
    reverse_direction: '存车线', lateral_speed_limit: 20, state: 'reverse' },
  { id: 'SW07', chainage: 10300, type: 'crossover', normal_direction: '上行→下行',
    reverse_direction: '上行→上行', lateral_speed_limit: 30, state: 'normal' },
  { id: 'SW08', chainage: 12100, type: 'single',    normal_direction: 'ST08→折返',
    reverse_direction: '存车线', lateral_speed_limit: 20, state: 'normal' },
];
```

### 组件改造

| 现状 | 改造 |
|------|------|
| `track.switch_states` 为空 → 显示"暂无数据" | fallback: context 为空时使用 `mockSwitches` |
| 卡片仅显示 ID + 位置 | 增加字段: 类型 (single/crossover)、方向、侧向限速 |

### 视觉增强

- 每个道岔卡片增加方向示意图标：
  - **定位 (normal)**: `→` + 绿色 `#52c41a`
  - **反位 (reverse)**: `↗` + 黄色 `#faad14`
  - **转换中 (transitioning)**: `⟳` + 蓝色 `#1890ff` + CSS 旋转动画

---

## 不修改项

- `SimulationContext.tsx` — reducer 和初始状态不变
- `App.tsx` — 路由和组件挂载不变
- `TrackView.tsx` — 布局结构不变
- 不新增 npm 依赖

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/pages/TrackView.tsx` | 不变 | 布局无需改动 |
| `src/components/views/track/LineProfileDetail.tsx` | 重写 | 占位符 → ECharts 双Y轴剖面图 |
| `src/components/views/track/OccupancyDisplay.tsx` | 重写 | 空状态网格 → SVG 轨道条带图 |
| `src/components/views/track/SwitchStatus.tsx` | 修改 | 增加 mock 数据 fallback + 视觉增强 |
| `src/data/mockLineData.ts` | 修改 | 新增 `mockSwitches` 导出 |

## 验收标准

1. TrackView 页面三个面板均不再显示"暂无数据"/"迭代三实现"占位符
2. LineProfileDetail 显示全线坡度填充图 + 限速虚线 + 车站标注 + 隧道遮罩
3. OccupancyDisplay 显示全线程轨道电路色块，hover 可见 tooltip
4. SwitchStatus 显示 8 个道岔卡片，各含状态彩色标签
5. 所有数据来自 `mockLineData.ts`，无需启动后端
6. TypeScript 类型检查通过，无编译错误
