# 信号视图前端设计（迭代二）

> 日期: 2026-07-10 | 迭代: 二 | 状态: 设计完成
> 分支: `feat/frontend-signal-view`

## 概述

在迭代一 `SignalView` 骨架基础上，采用**方案 A（前端自洽 + 现有数据）**实现三个子组件的数据对接与可视化，满足迭代二需求文档 UI-SIG-01~03 的**单列车简化版**范围。不依赖信号系统后端新增字段，不阻塞后端开发。

## 范围

### 包含

| 编号 | 组件 | 说明 |
|------|------|------|
| UI-SIG-01 | `MAChart` | 列车位置 + 前方站台 + 固定 300m 安全包络 |
| UI-SIG-02 | `SpeedEnvelope` | 区段限速 + 目标速度（限速×目标速度比）+ 实际速度 |
| UI-SIG-03 | `TimetableChart` | 单列车时间-距离运行图 |
| — | `chartHistory` 扩展 | 新增 `positionTime: [t, pos][]` 供运行图使用 |

### 不包含（留待后续迭代）

- UI-SIG-04 联锁状态表（迭代四）
- UI-SIG-05 时刻表对比图（迭代三）
- UI-SIG-06 车站联控状态面板（迭代三）
- ATP 紧急制动触发曲线（完整版，迭代三）
- 多车追踪间隔 MA 动态计算（迭代三）

## 文档冲突说明

`需求文档.md` 将 UI-SIG-01~03 标为迭代三；`迭代二_单列车增强需求文档.md` 标为迭代二（单车简化）。本设计按**迭代二单车简化版**实现，完整 ATP/多车能力留迭代三。需组长确认此裁剪策略。

## 架构与数据流

```
WebSocket snapshot ──→ apiAdapter ──→ SimulationContext
GET /config/line   ──→ lineLayout / profileSegments
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          MAChart      SpeedEnvelope    TimetableChart
         (SVG)          (ECharts)        (ECharts)
                              ▲
                    chartHistory（含 positionTime）
```

### 数据来源

| 数据 | 来源 | 用途 |
|------|------|------|
| `trains[0].position` | WebSocket | MA 图列车位置、运行图 Y 轴 |
| `trains[0].distance_to_station` | WebSocket | MA 图目标站台距离 |
| `trains[0].target_station_id` | WebSocket | MA 图站台标注 |
| `signaling.commands[0].running_phase` | WebSocket（可选） | 相位角标；缺失时从 mode/级位推导 |
| `lineLayout.stations` | REST 配置 | 站名与公里标 |
| `lineLayout.total_length` | REST 配置 | X 轴范围 |
| `profileSegments` | REST 配置 | 限速阶梯线 |
| `params.signal.target_speed_ratio` | 参数面板 | 目标速度线 |
| `chartHistory.speedPosition` | Context 累积 | 实际速度曲线 |
| `chartHistory.positionTime` | Context 累积（新增） | 运行图轨迹 |

### runningPhase 降级策略

后端 `orchestrator` 当前未输出 `runningPhase`。前端优先级：

1. `signaling.commands[0].running_phase`（若存在）
2. `train.mode` + `traction_level` / `brake_level` 推导

可选后续协调：后端在 `controlCommands` 增加 `runningPhase` 一行（非阻塞）。

## 组件设计

### MAChart — 移动授权示意图（UI-SIG-01）

**实现：** 自定义 SVG 横向示意图（参考 `OccupancyDisplay` 模式）

```
A站 ──── [🚃] ────→ ████████(300m) ──── B站
      当前位置      安全包络           目标站台
```

| 元素 | 逻辑 |
|------|------|
| 轨道基线 | `0 ~ total_length` 水平线 |
| 列车标记 | `position` 处矩形/图标 |
| 安全包络 | `[position, min(position+300, total_length)]` 半透明区域 |
| 目标站台 | `target_station_id` 匹配站名，或 `position + distance_to_station` |
| 车站标注 | 各站 `chainage` 竖线 + 站名 |
| 相位角标 | 牵引/惰行/制动/站停 中文标签 |

常量 `MA_ENVELOPE_LENGTH = 300`（米），迭代三再改为动态 ATP 包络。

### SpeedEnvelope — 速度包络线（UI-SIG-02）

**实现：** ECharts 折线图（复用 `SpeedPositionCurve` 模式）

| 系列 | 样式 | 数据 |
|------|------|------|
| 区段限速 | 红色虚线 | `profileSegments` 阶梯坐标 |
| 目标速度 | 橙色虚线 | `限速 × params.signal.target_speed_ratio` |
| 实际速度 | 蓝色实线 | `chartHistory.speedPosition` |

- X 轴：位置 (m)，范围 `0 ~ total_length`
- Y 轴：速度 (km/h)，上限 100
- 不绘制 ATP 紧急制动曲线（`// TODO: 迭代三实现`）

### TimetableChart — 运行图（UI-SIG-03）

**实现：** ECharts 折线图

| 系列 | 数据 |
|------|------|
| 单车轨迹 | `chartHistory.positionTime` → `[时间, 位置]` |
| 车站参考线 | `markLine` 水平线，Y = 各站 `chainage`，label = 站名 |

- X 轴：仿真时间 (s)
- Y 轴：位置 (m)
- 仿真 start/stop 时随 `clearChartHistory` 清空

## chartHistory 扩展

```typescript
// types/simulation.ts
export interface ChartHistory {
  speedTime: [number, number][];
  accelTime: [number, number][];
  jerkTime: [number, number][];
  speedPosition: [number, number][];
  positionTime: [number, number][];  // 新增：[elapsed, position]
}
```

```typescript
// utils/chartHistory.ts — appendChartHistory 内追加
positionTime: [...history.positionTime, [t, train.position]]
```

同步更新：`EMPTY_CHART_HISTORY`、`clearChartHistory`、`chartHistory.test.ts`、`chartHistoryExport.ts`（若导出需含位置列）。

## 改动文件清单

| 文件 | 改动类型 |
|------|----------|
| `frontend/src/types/simulation.ts` | 扩展 `ChartHistory` |
| `frontend/src/utils/chartHistory.ts` | 追加 `positionTime` |
| `frontend/src/utils/chartHistory.test.ts` | 测试更新 |
| `frontend/src/components/views/signal/MAChart.tsx` | 占位 → SVG 实现 |
| `frontend/src/components/views/signal/SpeedEnvelope.tsx` | 占位 → ECharts |
| `frontend/src/components/views/signal/TimetableChart.tsx` | 占位 → ECharts |
| `frontend/src/utils/format.ts` | 可选：`getSignalPhaseLabel()` |
| `frontend/src/pages/SignalView.tsx` | 更新注释（迭代二范围说明） |

**不改：** `SignalView` 布局结构、`SignalParams` 参数面板（已可用）。

## 实施顺序

1. 扩展 `chartHistory`（`positionTime`）
2. `TimetableChart`（运行图）
3. `SpeedEnvelope`（速度包络）
4. `MAChart`（MA 示意图）
5. 联调验证（Mock + 真后端）

## 验收标准

对照迭代二场景 4（多视图联动）：

- [x] 切换至信号视图，三张子图随仿真实时更新
- [x] MA 图：列车位置移动，前方站台与安全包络（300m / 后端 maProfile）正确
- [x] 速度包络：限速线、ATP 限速线、目标速度线、实际速度线同时显示
- [x] 运行图：时空轨迹累积，车站水平参考线标注清晰
- [x] `VITE_USE_MOCK=true` 与真后端模式均可运行
- [x] `npm run test` 与 `npx tsc -b` 通过（oxlint 本地 binding 缺失时跳过）

## 测试策略

- 单元测试：`chartHistory` 追加/清空 `positionTime`
- 手动验收：启动仿真，切换信号视图，观察三图联动
- 不新增 ECharts 组件快照测试（与项目现有模式一致）
