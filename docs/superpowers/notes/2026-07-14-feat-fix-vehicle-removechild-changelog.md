# 工作区变更记录：`feat/fix-vehicle-removechild`

**记录日期：** 2026-07-14  
**分支：** `feat/fix-vehicle-removechild`（相对 `dev` / HEAD `0d7a35d` 的未提交工作区改动）  
**状态：** 全部为本地未提交变更（modified + untracked）；本文档为快照说明，便于交接与继续开发。

---

## 1. 目标与问题背景

本轮前端改动围绕**车辆视图 / 信号视图**，解决长跑仿真下的一批体验与稳定性问题：

| 问题 | 现象 | 处理方向 |
|------|------|----------|
| React 19 + ECharts DOM 冲突 | 切视图时 `NotFoundError: removeChild` | keep-alive、延迟 dispose、DOM 安全补丁、错误边界 |
| 切视图假死 / 花屏 | ≥约 600s 后车辆↔信号切换卡顿、曲线变形 | `ChartSwitchGate` 冻结绘制 + 显示抽稀 ≤800 点 |
| 曲线「不逻辑」长斜线 | 绑到已结束车且时间轴仍跟全局 clock | `followClock` / `isChartTrainLive` |
| 曲线前半段空白 | 「全部列车」绑到晚发车，或历史滑动窗口丢前缀 | 优先最早发车历史；历史超限**整段压缩保留起点** |
| 车辆 X 轴不从 0 起 | 曾按首点浮起 | 时间轴统一 `min: 0` |
| 参数/控制区 DOM 抖动 | 切车/状态变化触发不稳定树 | `TrainSelector` / `ModeIndicator` / `ParamPanel` / `RunControlButtons` 稳定结构 |

---

## 2. 文件清单

### 2.1 新增（untracked）

| 路径 | 说明 |
|------|------|
| `frontend/src/components/common/ChartLifecycleContext.tsx` | keep-alive 视图 `active`：隐藏时暂停刷新 |
| `frontend/src/components/common/ChartSwitchGate.tsx` | 切页闸门 Provider / hooks |
| `frontend/src/components/common/chartSwitchPhase.ts` | phase 状态机：`idle` → `switching` → `settling` → `idle` |
| `frontend/src/components/common/chartSwitchPhase.test.ts` | phase 单元测试 |
| `frontend/src/components/common/ViewErrorBoundary.tsx` | 视图级错误边界，隔离单页崩溃 |
| `frontend/src/utils/domSafetyPatch.ts` | React DOM `removeChild`/`insertBefore` 孤儿节点兜底 |
| `frontend/src/utils/resolveChartTrainId.ts` | 曲线绑定列车 ID + 是否在线 |
| `frontend/src/utils/resolveChartTrainId.test.ts` | 绑定逻辑测试 |
| `frontend/src/hooks/useDownsampledSeries.ts` | 历史序列 → 显示抽稀 hook |
| `frontend/src/utils/vehicleChart.test.ts` | 抽稀等车辆图工具测试 |
| `docs/superpowers/specs/2026-07-13-signal-vehicle-frontend-roadmap-design.md` | 信号/车辆前端路线图设计 |
| `docs/superpowers/plans/2026-07-13-signal-vehicle-frontend-roadmap.md` | 对应实施计划 |
| `docs/superpowers/specs/2026-07-14-smooth-view-switch-charts-design.md` | 丝滑切视图设计（已批准） |
| `docs/superpowers/plans/2026-07-14-smooth-view-switch-charts.md` | 丝滑切视图实施计划 |

### 2.2 修改（modified）

工作区 `git diff --stat`（约 **+587 / −223**，不含仅换行可能触发的文件）：

| 路径 | 变更要点 |
|------|----------|
| `frontend/src/App.tsx` | 车辆/信号 keep-alive；`ChartSwitchGate`；`ViewErrorBoundary`；切页 settling |
| `frontend/src/main.tsx` | 启动前 `applyReactDomSafetyPatch()` |
| `frontend/src/layouts/TopBar.tsx` | `beginSwitch` + `startTransition(SET_VIEW)` |
| `frontend/src/components/common/SimEChart.tsx` | 遵守闸门；idle 150ms 节流；settling 立即绘；data 浅拷贝 |
| `frontend/src/components/common/TrainSelector.tsx` | 稳定 DOM，减少因候选项文案变化导致的节点抖动 |
| `frontend/src/components/control/RunControlButtons.tsx` | 稳定按钮树结构 |
| `frontend/src/components/param/ParamPanel.tsx` | 稳定面板结构 |
| `frontend/src/components/param/SignalParams.tsx` | git 标为修改；内容可能仅为换行（`CRLF`），需提交前复核 |
| `frontend/src/pages/VehicleView.tsx` | `active` + `ChartLifecycleProvider` |
| `frontend/src/pages/SignalView.tsx` | 同上 |
| `frontend/src/components/views/vehicle/SpeedTimeCurve.tsx` | 抽稀、`min:0`、`followClock` |
| `frontend/src/components/views/vehicle/AccelTimeCurve.tsx` | 同上 |
| `frontend/src/components/views/vehicle/EnergyChart.tsx` | 同上 |
| `frontend/src/components/views/vehicle/ResistanceChart.tsx` | 同上 + 结构整理 |
| `frontend/src/components/views/vehicle/JerkTimeCurve.tsx` | 同上 |
| `frontend/src/components/views/vehicle/ModeIndicator.tsx` | 稳定 DOM |
| `frontend/src/components/views/signal/TimetableChart.tsx` | 抽稀、`min:0` 等 |
| `frontend/src/components/views/signal/SpeedEnvelope.tsx` | 绑定/轴相关小改 |
| `frontend/src/context/SimulationContext.tsx` | 历史追加等相关配合 |
| `frontend/src/context/SimulationContext.test.ts` | 上下文测试增补 |
| `frontend/src/hooks/useSelectedTrain.ts` | `useActiveChartTrainId` / `useActiveChartHistory` / `useChartFollowClock` |
| `frontend/src/utils/chartHistory.ts` | 原地 `pushPoint`；超限**压缩保起点**（非丢前缀） |
| `frontend/src/utils/chartHistory.test.ts` | 压缩保起点断言 |
| `frontend/src/utils/chartHistoryExport.ts` | git 标为修改；提交前请核对是否有实质 diff |
| `frontend/src/utils/chartHistoryExport.test.ts` | 同上 |
| `frontend/src/utils/format.ts` | `stableVehicleTimeMax(..., followClock)` |
| `frontend/src/utils/format.test.ts` | followClock 行为测试 |
| `frontend/src/utils/vehicleChart.ts` | `CHART_DISPLAY_MAX_POINTS=800` + `downsamplePoints` |

### 2.3 本文件

| 路径 | 说明 |
|------|------|
| `docs/superpowers/notes/2026-07-14-feat-fix-vehicle-removechild-changelog.md` | **本文**：工作区变更总录 |

---

## 3. 按主题说明实现要点

### 3.1 崩溃防护与 DOM 稳定

- **`domSafetyPatch`**：在 `createRoot` 之前包装父节点 `removeChild` / `insertBefore`，孤儿操作直接跳过并告警，避免整页白屏。
- **keep-alive**：访问过的 `vehicle` / `signal` 以 `display:none` 保留，避免长序列图表反复卸载。
- **双层 host / 延迟 dispose**（`SimEChart`）：降低 React 与 ECharts 争抢同一 DOM 节点的概率。
- **稳定控件树**：选择器、工况条、控制按钮、参数面板避免条件挂载导致结构跳变。
- **`ViewErrorBoundary`**：按视图隔离异常。

### 3.2 切视图丝滑（验收目标 A：约 1s 内切完，可接受稀疏曲线）

状态机：

```text
idle → (TopBar beginSwitch) → switching → (activeView 生效后 markSettling) → settling → (约 80ms) → idle
```

- **switching**：禁止 `setOption` / 重绘，避免切页瞬间大数据绘制堵主线程。
- **settling**：立刻补一帧目标可见页。
- **idle**：约 `150ms` 节流。
- **显示层抽稀**：`CHART_DISPLAY_MAX_POINTS = 800`（`useDownsampledSeries`）。
- **绘制数据拷贝**：避免 chartHistory 原地 mutate 与 ECharts 共享引用导致花屏。

设计/计划文档：`2026-07-14-smooth-view-switch-charts-*.md`。

### 3.3 曲线绑定与时间轴

- **`resolveChartTrainId`**
  - 显式选中车：绑该车历史（离线仍可回看）。
  - 「全部列车」：优先**发车最早**（`speedTime[0][0]` 最小）的历史，减轻前半段空洞。
- **`useChartFollowClock` / `isChartTrainLive`**：绑定车不在当前 snapshot → 时间轴 max **不跟随**全局 `clock.elapsed`，避免后半假直线。
- 车辆时间图与运行图：**X 轴 `min: 0`**。

### 3.4 历史缓存：长跑不丢前半段

- `CHART_HISTORY_MAX_POINTS = 12_000`。
- 旧行为（问题）：超限 `splice` 丢最旧点 ≈ 滑动窗口，长跑后曲线从 ~850s 才出现、轴仍从 0 起。
- 新行为：超过高水位（`1.25 * max`）后**整段均匀压缩**到约 `0.8 * max`，**保留首末点**（`compressSeriesPoints`）。

### 3.5 导出与其它

- `chartHistoryExport*` / `SignalParams.tsx`：工作区显示修改；若仅换行，提交前应用 `git diff` 确认后再决定是否纳入。

---

## 4. 测试与验证状态

- 前端 Vitest：近期记录约 **108** 通过；`tsc -b` 曾通过（以本地最新跑测为准）。
- 建议人工验收：
  1. 硬刷新后长跑 ≥600s，车辆↔信号反复切换：约 1s 内切完、无假死、无 `removeChild`。
  2. 长跑至历史接近/超过缓存上限：速度/运行图等曲线仍从 **t≈0 / 线路起点** 起，而非半截空白。
  3. 「全部列车」与显式选车：绑车与时间轴跟随行为符合 3.3。

---

## 5. 进行中 / 未完成项（Brainstorming）

用户反馈（**尚未实现，分析中**）：

> 仿真**未启动**时，运行图、速度-时间、加速度-时间、总阻力、能耗累计不要显示 `x>0` 后垂直于 X 轴的竖线；运行图不要显示「安河桥北」。

已澄清：

- 「车未发动」= **仿真未启动**（非“已运行但仍停站”）。
- 待确认展示形态（上次选项，用户尚未选）：
  - A. 保留轴框，隐竖网格；运行图无站名  
  - B. 完全空白面板  
  - C. `max` 压到 0  
  - D. 其他  

代码侧线索（供后续实现）：

- 车辆图空数据时默认 `xMax=600` → ECharts 竖向 `splitLine`。
- 运行图空数据时 `stableTimeMax([]) → 60` → 同理有竖网格。
- 「安河桥北」来自 `TimetableChart` 车站 `markLine`（`yAxis: chainage≈0`）标签。

---

## 6. 分支与提交约定（备忘）

- 合回 `dev`：rebase + `--ff-only`，禁止 merge commit。
- 提交需用户明确要求；信息风格 `type(scope): 中文`（≤50，caveman-commit）。
- 历史偏好：部分 docs 是否入库以用户当场指示为准；代码与已批准设计/计划建议与功能一并整理。

---

## 7. 变更量快照（命令参考）

```text
分支: feat/fix-vehicle-removechild
相对 HEAD 的 modified 约 25+ 文件，+587 / -223（核心前端逻辑）
另有 untracked：公共图表组件/工具 9 个 + superpowers 文档 4 个 + 本 notes 文档
```

生成本文时可用：

```bash
git status -u
git diff --stat
git branch --show-current
```

---

## 8. 一句话总结

本分支工作区已落地：**车辆/信号 keep-alive + 切页闸门抽稀 + DOM 兜底**，以及 **曲线绑车 / 时间轴 followClock / 历史压缩保起点**；**仿真未启动时的空图竖线与起点站名**仍停在需求澄清阶段，尚未改代码。
