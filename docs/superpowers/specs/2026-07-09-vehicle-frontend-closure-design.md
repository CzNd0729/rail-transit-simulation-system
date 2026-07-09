# 车辆系统前端闭环 — 设计规格

> 日期：2026-07-09  
> 负责人：车辆系统前端  
> 状态：待评审  
> 前置：`21c87da` 车辆联调适配、`1367701` REST 参数提交、`7e64bee` E2E 闭环

## 1. 范围界定

### 1.1 你负责（本规格范围）

| 模块 | 需求编号 | 文件域 |
|------|---------|--------|
| 车辆视图 | UI-VHC-01~03 | `pages/VehicleView.tsx`, `components/views/vehicle/*` |
| 车辆参数 | UI-PARAM-01 | `components/param/VehicleParams.tsx` |
| 仿真控制（影响车辆曲线） | UI-CTRL-01~03 | `hooks/useSimulation.ts`, `hooks/useMockReplay.ts` |
| 数据适配 | — | `utils/apiAdapter.ts`（vehicle 字段） |
| 运行摘要（车辆视图旁 ExportPanel） | 场景 3 | `components/export/RunSummaryPanel.tsx` |

### 1.2 不在本规格（他人负责）

| 模块 | 负责人 |
|------|--------|
| 综合视图线路图、StatusCards | Overview 前端 |
| 线路区段参数 SEC02 坡度 | Track 前端 + 后端 G1 |
| 后端动力学/信号/快照字段 | 后端 |

---

## 2. 现状（2026-07-09 最新 dev）

### 2.1 已完成

- **UI-VHC-01~03**：速度-时间、加速度-时间、工况指示器 — Mock 模式完整可用
- **UI-PARAM-01**：车辆参数表单 + 恢复默认 + 牵引曲线表
- **Live 适配层**：`apiAdapter.ts`、`useWebSocket.ts`、`useBootstrap.ts`
- **Live 参数 REST**：`useSimulation.updateParams` → `PUT /params`（`1367701`）
- **图表数据管道**：`chartHistory.ts` ← `RUNTIME_UPDATE` ← WS/Mock

### 2.2 阻塞验收的 Bug（P0）

| Bug | 现象 | 根因 |
|-----|------|------|
| **B1 停止清空曲线** | 点「停止」后速度/加速度曲线消失 | `useSimulation.stopSimulation()` dispatch `CLEAR_CHART_HISTORY` |
| **B2 Mock 停止无摘要** | Mock 手动停止不显示 RunSummaryPanel | `useMockReplay` stop 分支无 `SET_STATS` |
| **B3 stats 与 chart 绑定清除** | `CLEAR_CHART_HISTORY` 同时重置 `stats` | `SimulationContext` reducer 耦合 |

影响：**验收场景 3**（停止后显示运行摘要、曲线可回顾）无法通过。

### 2.3 部分完成（P1）

| 项 | 说明 |
|----|------|
| 工况「站停」 | `ModeIndicator` 无法区分 dwell vs 惰行停稳；后端 `runningPhase` 尚未消费 |
| 参数提示文案 | 「下次点击运行生效」与 Live 即时 REST 提交矛盾 |
| 牵引曲线 Live | 表单可编辑但后端不支持 `tractionCurve` PUT，Live 下为本地-only |
| `useParamSubmit.ts` | 已创建但未接入，与 `useSimulation` 重复 |
| VHC-04/05 占位 | 占 50% 车辆视图高度，挤压 iter1 核心图表 |
| 组件测试 | 联调计划 Task 6 未落地 |

### 2.4 后端依赖（你只需联调验证，不改后端）

| 依赖 | 场景 | 状态 |
|------|------|------|
| WS `simulation_snapshot` | 1 | ✅ 已有 |
| WS `simulation_complete.summary` | 3 | ✅ 已有 |
| `PUT /params` `emptyMass` | 4 | ✅ 已有 |
| `mode: stopped` in snapshot | 1/3 | ✅ 已有 |
| `runningPhase: dwell` | 1 工况指示 | ⏳ 后端 iter1-closure 计划 |
| `tractionCurve` PUT | 参数 | ❌ 迭代一不做 |
| 线路坡度 Live 更新 | 2 | ❌ Track 负责 |

---

## 3. 目标

**Mock + Live 双模式下，车辆视图通过验收场景 1、3、4 的车辆相关检查项。**

| 场景 | 车辆前端验收点 |
|------|---------------|
| 1 | 速度-时间上升→平→降；加速度正负零；工况牵引→惰行→制动→停稳 |
| 3 | 暂停冻结曲线；继续恢复；**停止后曲线保留 + 摘要显示**；10× 加速 |
| 4 | 质量 200t→220t 后加速度曲线降低、站间时间变长 |

场景 2（坡度）由 Track 模块负责；你可在 Live 就绪后做**只读验证**（看曲线是否变化）。

---

## 4. 方案对比

### 方案 A：修复生命周期 + 小幅 UX 打磨（推荐）

1. 拆分 `CLEAR_CHART_HISTORY` 与 stats 清除
2. stop 不清 chart；start 时清 chart
3. Mock stop 补 `SET_STATS`
4. 隐藏 VHC-04/05 占位；修正参数提示

- **优点**：改动集中、2~3 天可完成、直接解场景 3
- **缺点**：站停语义仍靠 speed+mode 推断

### 方案 B：大改 VehicleView 布局 + 新增阻力预览

- **优点**：视觉更完整
- **缺点**：UI-VHC-04 非 iter1；超出范围

### 方案 C：仅 Mock 补丁

- **优点**：最快
- **缺点**：Live 场景 3 仍失败；无法签字

**推荐方案 A。**

---

## 5. 详细设计

### 5.1 图表/统计生命周期

```
[空闲] ──start──▶ [运行] chartHistory 累积
                    │
         pause ──▶ [暂停] chartHistory 冻结（不追加）
                    │
         resume ──▶ [运行] 继续累积
                    │
         stop ────▶ [停止] chartHistory 保留 + SET_STATS
                    │
         start ───▶ 清空 chartHistory + stats，重新运行
```

**Reducer 变更：**

- `CLEAR_CHART_HISTORY`：仅清 `chartHistory`，**不动** `stats`
- 新增 `RESET_RUN_DATA`：`start` 时同时清 chart + stats（或 start 连续 dispatch 两个 action）

**`useSimulation.ts`：**

```typescript
// start: dispatch RESET_RUN_DATA（或 CLEAR_CHART + CLEAR_STATS）
// stop:  仅 send stop，不 dispatch clear
```

**`useMockReplay.ts` stop 分支：**

```typescript
case 'stop':
  replayer.stop();
  dispatch({ type: 'SET_STATS', payload: computeStats(runStatsRef) });
  dispatch({ type: 'SET_RUN_STATE', payload: 'stopped' });
  break;
```

### 5.2 ModeIndicator 站停（P1，可先做映射预留）

新增 `getDisplayMode(train, runningPhase?)` 工具：

```typescript
if (runningPhase === 'dwell') return 'stopped'; // 标签显示「停稳/站停」
if (train.mode === 'stopped') return 'stopped';
if (train.mode === 'coasting' && train.speed < 0.5) return 'stopped';
```

`runningPhase` 来源（优先级）：
1. `signaling.commands[0].running_phase`（后端就绪后 `apiAdapter` 映射）
2. 暂无则 fallback 现有逻辑

可选：停稳态 label 改为「站停」当 `clock` 在站台且 speed≈0（Mock 足够）。

### 5.3 VehicleParams Live 模式提示

```tsx
<div style={styles.hint}>
  {USE_MOCK
    ? '参数在下次点击「运行」时生效'
    : '参数已实时提交后端（运行中修改将在下一步生效）'}
</div>
```

牵引曲线表：Live 模式下表头加 `(仅本地，迭代一后端不支持)` 或 `readOnly`。

### 5.4 清理重复代码

删除 `useParamSubmit.ts`（`useSimulation.updateParams` 已覆盖 REST 路径），或合并为单一入口。**推荐删除**，避免双轨。

### 5.5 VehicleView iter1 布局

隐藏 `ResistanceChart` / `EnergyChart` 行（条件渲染 `import.meta.env.DEV && false` 或直接注释掉 iter1 布局块），让 VHC-01/02 占满剩余高度：

```tsx
{/* 迭代三占位，迭代一隐藏 */}
{false && (
  <div style={styles.chartRow}>...</div>
)}
```

### 5.6 测试

| 测试 | 文件 |
|------|------|
| stop 不清 chartHistory | `useSimulation.test.ts` 或 reducer test |
| ModeIndicator stopped 渲染 | `ModeIndicator.test.tsx` |
| parseApiParams emptyMass 往返 | 扩展 `apiAdapter.test.ts` |

---

## 6. 错误处理

| 场景 | 行为 |
|------|------|
| Live `PUT /params` 失败 | `console.error` + 保留本地值（现有行为） |
| stop 后无 summary（Live） | 依赖 `simulation_complete`；若无则 RunSummaryPanel 不显示 |
| WS 断连 | 曲线停止更新，已有 reconnect |

---

## 7. 自审

- [x] 范围仅车辆前端，不含 track/overview
- [x] 场景 3 Bug B1~B3 有明确修复方案
- [x] 不依赖后端新 API 即可交付 P0
- [x] P1（dwell、牵引曲线提示）可并行
- [x] 无 TBD
