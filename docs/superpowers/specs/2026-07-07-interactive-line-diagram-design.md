# 综合视图交互式线路图设计

> 日期: 2026-07-07
> 状态: 草案
> 组件: frontend/src/components/views/overview/

## 1. 背景与目标

现有综合视图中的 `TrainAnimation` 组件是一个 80px 高的简单横条，硬编码 3 个车站，
仅用 CSS 定位列车图标。当车站数量增长到 10-30 个时，该方案无法承载详细信息展示。

**目标**: 替换为基于 SVG + React 的交互式线路图，支持：

- 全线 20+ 车站的可缩放横向展示
- 站内多股道布局（正线/侧线/存车线）
- 区间轨道电路区段占用状态可视化
- 列车实时位置动画与工况着色
- 锁定跟随 + 手动拖拽 + 重新锁定的视口控制
- 悬停/点击显示车站详细信息卡片

## 2. 技术方案

**选型: SVG + React 自定义组件**

选择理由：

- SVG 原生支持任意几何图形，可自由绘制站内多股道布局
- DOM 事件天然可用（hover/click），无需手动碰撞检测
- CSS transition 可驱动列车平滑移动，GPU 加速
- 20-30 车站规模下 SVG 元素量约 200-300 个，远低于性能瓶颈
- 与项目现有 React + TypeScript 架构完全一致

弃选方案：

- ECharts 自定义系列: 站内多股道布局在 `renderItem` 中实现困难，交互受限
- Canvas 2D: 所有交互需手动碰撞检测，开发量过大

## 3. 组件架构

```
LineDiagram (主容器)
├── SVG 画布 (viewBox 控制可见区域)
│   ├── TrackSegment × N    — 区间轨道电路色块
│   ├── StationNode × N     — 站内股道布局渲染
│   └── TrainMarker × N     — 列车图标
├── ViewportControls        — 缩放滑块 + 跟随按钮 + 总览按钮
└── StationInfoCard         — 浮动信息卡片 (条件渲染)
```

### 3.1 LineDiagram — 主容器

职责: 渲染 SVG 画布、管理视口状态、协调子组件。

```tsx
interface LineDiagramProps {
  lineLayout: LineLayout;
  trains: TrainState[];
}
```

内部状态由 `useViewport` hook 管理。SVG 画布尺寸自适应父容器，
通过 `viewBox` 属性控制可见范围。

### 3.2 StationNode — 站内股道渲染

职责: 绘制单个车站的股道布局。

渲染规则：

- 每条股道为一条水平线，X 范围 = `[station.chainage, station.chainage + station.length]`
- 正线 (main): 线宽 3px，实线，颜色 `#e0e0e0`
- 侧线 (siding): 线宽 2px，实线，颜色 `#a0a0a0`
- 存车线 (parking): 线宽 2px，虚线，颜色 `#808080`
- 股道间垂直间距 16px
- 车站两端竖线封边（线宽 1px，颜色 `#4a4a6a`）
- 站名标注在车站上方居中，公里标在下方
- 被占用的股道叠加红色半透明底色

### 3.3 TrackSegment — 区间轨道电路

职责: 绘制两站之间的轨道电路区段。

渲染规则：

- 区间内按 `TrackCircuit[]` 切分为连续矩形色块
- 每个色块宽度 = `(circuit.end - circuit.start) / zoom`
- 高度 = 8px（与股道线对齐）
- 颜色:
  - 占用: `rgba(255, 77, 79, 0.6)` (红色半透明)
  - 空闲: `rgba(82, 196, 26, 0.3)` (绿色半透明)
- 色块间 1px 间隔线，颜色 `#2a2a4a`

### 3.4 TrainMarker — 列车图标

职责: 在 SVG 中渲染列车位置。

渲染规则：

- 使用 SVG `<g>` 组，包含列车图形（自定义 path 或 emoji 转 text 元素）
- 底色跟随工况: 牵引 `#1890ff`，惰行 `#faad14`，制动 `#ff4d4f`
- 定位: `transform: translate(X, Y)`，X 由 `train.position` 映射
- Y 坐标: 正线股道的垂直位置
- CSS `transition: transform 100ms linear` 实现平滑移动
- 可选: 列车后方淡色尾迹（最近 5 个位置点，透明度递减）

### 3.5 StationInfoCard — 浮动信息卡片

触发条件: 悬停或点击车站时显示。

内容:

```
站名 (车站代码)
公里标: K12+400
站长: 220m | 4条股道
到达: 08:32:15  出发: 08:33:00
停站: 45s
站台占用: ██████░░ 67%
各股道状态: 正线:空闲  侧线1:占用  存车线:空闲
```

实现: HTML `div` 浮层（非 SVG 内部元素），通过绝对定位跟随车站位置。
当视口滚动时，卡片位置通过坐标转换同步更新。
点击空白区域关闭。

### 3.6 ViewportControls — 视口控制栏

位置: LineDiagram 容器底部或右上角浮动。

控件:

- **缩放滑块**: range input, 范围 0.2-5.0, 步长 0.1
- **跟随锁定按钮**: 切换按钮，锁定/解锁跟随模式
- **全线总览按钮**: 一键缩放到显示全部车站
- 缩放按钮组: `+` / `-` 按钮，步长 0.5

## 4. 数据结构

### 4.1 新增类型（扩展 types/simulation.ts）

```typescript
/** 站内股道布局 */
export interface TrackLayout {
  track_id: string;
  name: string;           // "正线", "侧线1", "存车线"
  type: 'main' | 'siding' | 'parking';
  occupied: boolean;
}

/** 车站布局（扩展现有 Station 接口） */
export interface StationLayout extends Station {
  length: number;         // 站长 (m)
  tracks: TrackLayout[];
  arrival_time?: number;  // 到达仿真时间 (s)
  departure_time?: number;
  dwell_time?: number;    // 停站时长 (s)
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

### 4.2 AppState 扩展

```typescript
// 在 AppState 接口中新增:
lineLayout: LineLayout | null;
```

初始值为 `null`，后端连接成功后通过初始化消息填充。
Mock 模式下直接加载 Mock 数据。

## 5. 视口交互逻辑

### 5.1 useViewport Hook

**SVG 坐标系**: 采用世界坐标（米），X 轴 = 公里标，Y 轴 = 股道编号映射。
viewBox 直接以米为单位控制可见范围，缩放通过改变 viewBox 宽度实现。
屏幕像素到世界坐标的转换: `worldX = viewBox.minX + (screenX / containerWidth) * viewBox.width`。

```typescript
interface ViewportState {
  zoom: number;           // 缩放倍率 [0.2, 5.0]
  panX: number;           // 水平偏移 (m, 世界坐标/公里标)
  panY: number;           // 垂直偏移 (m, 世界坐标)
  followMode: boolean;    // 是否锁定跟随
  selectedStation: string | null;
}

interface UseViewportReturn {
  viewport: ViewportState;
  viewBox: string;        // 计算后的 SVG viewBox 字符串
  handleWheel: (e: WheelEvent) => void;
  handleMouseDown: (e: MouseEvent) => void;
  handleMouseMove: (e: MouseEvent) => void;
  handleMouseUp: () => void;
  setZoom: (z: number) => void;
  toggleFollow: () => void;
  fitAll: () => void;     // 缩放到全线可见
  focusStation: (id: string) => void;
}
```

### 5.2 跟随模式

- **初始化**: `followMode = true`，视口居中于第一列列车
- **每帧更新** (followMode=true): 平移 viewBox 使列车处于视口水平 30% 处（前方留 70% 视野）
- **手动拖拽**: `mousedown` 时设置 `isDragging = true`，同时 `followMode = false`
- **重新锁定**: 点击跟随按钮，通过 `requestAnimationFrame` 线性插值（约 300ms）平滑移动 viewBox 到列车位置

### 5.3 缩放

- **滚轮缩放**: 以鼠标当前位置为锚点，缩放 viewBox
- **范围**: 0.2×（全线总览）~ 5.0×（单站详情）
- **自适应细节**: 缩放 < 1.0× 时，隐藏站内股道细节，只显示车站方块概览

## 6. Mock 数据

8 个车站的完整线路数据，文件位置: `frontend/src/data/mockLineData.ts`

| 站名 | 公里标(m) | 站长(m) | 股道数 | 特点 |
|---|---|---|---|---|
| 始发站 | 0 | 200 | 4 (正线+2侧线+存车线) | 大型始发终到站 |
| 科技园 | 1800 | 150 | 2 (正线+1侧线) | 中等站 |
| 大学城 | 3500 | 120 | 1 (正线) | 简单通过站 |
| 市中心 | 5200 | 250 | 3 (正线+2侧线) | 大型换乘站 |
| 商业街 | 6800 | 130 | 2 (正线+1侧线) | 中等站 |
| 工业区 | 8500 | 180 | 3 (正线+1侧线+存车线) | 有折返功能 |
| 新城 | 10200 | 120 | 1 (正线) | 简单通过站 |
| 终点站 | 12000 | 200 | 4 (正线+2侧线+存车线) | 大型终到站 |

区间每 200-400m 一个轨道电路区段，全线约 40-50 个区段。
Mock 数据中预设部分区段为占用状态以展示效果。

## 7. 文件清单

### 新增

| 文件 | 职责 |
|---|---|
| `components/views/overview/LineDiagram.tsx` | 主容器，SVG 画布 + 控制栏 |
| `components/views/overview/StationNode.tsx` | 站内股道 SVG 渲染 |
| `components/views/overview/TrackSegment.tsx` | 区间轨道电路 SVG 渲染 |
| `components/views/overview/TrainMarker.tsx` | 列车图标 SVG 渲染 |
| `components/views/overview/StationInfoCard.tsx` | 浮动信息卡片 |
| `components/views/overview/ViewportControls.tsx` | 缩放/跟随控制栏 |
| `hooks/useViewport.ts` | 视口管理 hook |
| `data/mockLineData.ts` | 8 站 Mock 数据 |

### 修改

| 文件 | 改动 |
|---|---|
| `types/simulation.ts` | 新增 TrackLayout, StationLayout, InterStationSegment, LineLayout |
| `pages/OverviewView.tsx` | TrainAnimation → LineDiagram |
| `context/SimulationContext.tsx` | AppState 新增 lineLayout 字段 |

### 删除

| 文件 | 原因 |
|---|---|
| `components/views/overview/TrainAnimation.tsx` | 被 LineDiagram 完全取代 |

## 8. 性能考量

- SVG 元素总量: 约 200-300 个（8站 × 平均3股道 + 50轨道电路 + 列车），远低于性能瓶颈
- 列车移动使用 CSS `transform` + `transition`，利用 GPU 合成
- 子组件使用 `React.memo` 避免不必要重渲染
- 缩放 < 1.0× 时隐藏站内股道细节，降低渲染复杂度
- 视口外元素不做特殊剔除（SVG 引擎自身处理）

## 9. 与后端的对接

Mock 数据阶段完成后，后端就绪时:

- `LineLayout` 数据从 REST API `GET /api/v1/config/line` 获取
- 股道占用状态从 WebSocket `simulation_snapshot.track` 实时更新
- 列车到/离站时间从 `simulation_snapshot.trains` 推算
- Mock 数据保留为 fallback 和离线演示模式
