# 前端渲染性能优化 — 设计文档

> **日期：** 2026-07-14
> **状态：** 设计确认
> **背景：** 车辆数 > 6 时 FPS 显著下降，后续随车辆增多（10+）将恶化至个位数

---

## 一、性能瓶颈诊断

### 1.1 渲染架构

```
WebSocket → RUNTIME_UPDATE dispatch → Reducer → 36 个 context 消费者重渲染 → ECharts setOption
```

每 tick 的完整链路。mock 模式下 1× 倍率 = 10Hz，10× 倍率 = 100Hz。

### 1.2 三个核心瓶颈

| # | 瓶颈 | 位置 | 影响 |
|:---|:-----|:-----|:-----|
| 1 | **数组扩散拷贝** | `chartHistory.ts:appendChartHistory` | 每帧每车 13 次 `[...prev, [t,v]]` 全量拷贝，50k 点后每次拷贝 5 万元组 |
| 2 | **option 未 memo** | `SpeedPositionCurve.tsx` / `LineProfile.tsx` | 每帧新 option 对象 + `notMerge` 触发 ECharts 全量重建 |
| 3 | **无降采样** | 所有图表组件 | 向 ECharts 传 50k 数据点，图表仅 400-800px 宽，30× 冗余 |

### 1.3 数据量测算

- 仿真 6000s，10fps = 每系列 60,000 点（cap 50k）
- 每车 13 个系列 × 6 车 = 78 个数组，~390 万数据点常驻内存
- 6 车 10fps：每秒 780 次数组全量拷贝（78 数组 × 10 帧）

---

## 二、优化方案（方案 A：外科手术）

> 原则：零架构变更、零公共接口变更、不改测试

### 2.1 chartHistory 写入路径改为可变 push

**现状：**
```typescript
speedTime: [...prev.speedTime, [t, train.speed]],  // 拷贝 50k 元组
```

**改为：**
```typescript
// 直接 push，不做拷贝
function appendToSeries(series: DataPoint[], point: DataPoint, max: number) {
  series.push(point);
  if (series.length > max) series.shift();
}
```

**兼容策略：**
- 数组类型 `[number, number][]` 不变，ECharts 直接读取，零下游改动
- reducer 中不再深拷贝 chartHistory，通过在 `AppState` 上维护 `chartVersion` 版本号驱动 useMemo 重算
- `clearChartHistory` 改为 `series.length = 0`

**预期收益：** 消除 90%+ 数组分配和 GC 压力

### 2.2 补缺失的 useMemo + React.memo

**useMemo 补全：**

| 组件 | 修复 |
|:-----|:-----|
| `SpeedPositionCurve` | 将 option 构建包入 `useMemo`，依赖 `[trainSeries, positionMarkers, ...]` |
| `LineProfile` | 将 option 构建包入 `useMemo`，依赖 `[lineLayout, profileSegments, ...]` |

**React.memo 包裹纯展示图表**（不直接读 context、仅通过 props 接收数据的组件）：

- `SpeedTimeCurve`、`AccelTimeCurve`、`JerkTimeCurve`
- `EnergyChart`、`ResistanceChart`
- `SpeedEnvelope`、`TimetableChart`
- `VoltageProfile`

> 读 context 的组件不适合 React.memo（context 变化本身触发重渲染）

**预期收益：** 消除无效的 notMerge 全量 ECharts 重建；跳过无数据变化的图表重渲染

### 2.3 图表数据降采样

新增工具函数 `downsample(data, maxPoints)`，在 option 构建时调用：

```typescript
/** 均匀降采样，保留首尾点确保范围完整 */
export function downsample(
  data: [number, number][],
  maxPoints: number = 1000
): [number, number][] {
  if (data.length <= maxPoints) return data;
  const step = data.length / maxPoints;
  const result: [number, number][] = [];
  for (let i = 0; i < maxPoints; i++) {
    result.push(data[Math.floor(i * step)]);
  }
  if (result[result.length - 1] !== data[data.length - 1]) {
    result.push(data[data.length - 1]);
  }
  return result;
}
```

**各图表 maxPoints 配置：**

| 图表类型 | maxPoints | 理由 |
|:---------|:----------|:-----|
| 速度/加速度/冲击率曲线 | 800 | 图表宽度 ~400px，2× 过采样 |
| 速度-位置曲线 | 500 | 受线路长度自然约束 |
| 能耗累计 | 800 | 线性增长，降采样无精度损失 |
| 阻力曲线 | 800 | 周期波动 |
| 网压分布 | 500 | 位置维度 |
| 运行图/时刻表 | 1000 | 宽度 ~600px |

**预期收益：** setOption 数据量降低 10-50×

---

## 三、改动清单

| # | 文件 | 操作 | 说明 |
|:---|:-----|:-----|:-----|
| 1 | `utils/chartHistory.ts` | 重写 | push 写入 + 版本号机制 |
| 2 | `utils/format.ts` (或新文件) | 新增 | `downsample()` 工具函数 |
| 3 | `context/SimulationContext.tsx` | 修改 | `chartVersion` 字段 + reducer 逻辑调整 |
| 4 | `components/views/overview/SpeedPositionCurve.tsx` | 修改 | 补 `useMemo` + `downsample` |
| 5 | `components/views/overview/LineProfile.tsx` | 修改 | 补 `useMemo` |
| 6 | `components/views/vehicle/SpeedTimeCurve.tsx` | 修改 | `React.memo` + `downsample` |
| 7 | `components/views/vehicle/AccelTimeCurve.tsx` | 修改 | `React.memo` + `downsample` |
| 8 | `components/views/vehicle/JerkTimeCurve.tsx` | 修改 | `React.memo` + `downsample` |
| 9 | `components/views/vehicle/EnergyChart.tsx` | 修改 | `React.memo` + `downsample` |
| 10 | `components/views/vehicle/ResistanceChart.tsx` | 修改 | `React.memo` + `downsample` |
| 11 | `components/views/signal/SpeedEnvelope.tsx` | 修改 | `React.memo` + `downsample` |
| 12 | `components/views/signal/TimetableChart.tsx` | 修改 | `React.memo` + `downsample` |
| 13 | `components/views/power/VoltageProfile.tsx` | 修改 | `React.memo` + `downsample` |

### 不改动的文件

- 所有类型定义（`types/simulation.ts`）
- API 层（`services/api.ts`）
- 非图表组件（控制面板、参数面板、状态栏等）
- ECharts 封装层（`SimEChart.tsx`）
- 所有测试文件

---

## 四、不做的事项

1. **Context 拆分** — 改动 36 个消费者，风险过高（留方案 B）
2. **TypedArray 环形缓冲区** — 破坏现有类型接口（留方案 C）
3. **WebSocket 帧节流** — 后端控制推送频率，前端不做二次节流
4. **虚拟化图表**（仅渲染可视窗口内的数据点）— ECharts 内部已有此优化

---

## 五、验收标准

| 编号 | 场景 | 预期结果 |
|:-----|:-----|:---------|
| AC-01 | 6 车 1× 倍率运行 600s | FPS ≥ 30 |
| AC-02 | 10 车 1× 倍率运行 600s | FPS ≥ 20 |
| AC-03 | TypeScript 编译零错误 | `npx tsc -b` 通过 |
| AC-04 | lint 无新增警告 | `npm run lint` 通过 |
| AC-05 | 现有测试全部通过 | `npm test`（如有） |
| AC-06 | 图表视觉效果无变化 | 人工对比优化前后截图 |

---

## 六、风险与回滚

- **最大风险项**：chartHistory 从不可变改为可变。若 `useMemo` 依赖检测失效 → 图表不更新
- **缓解**：`chartVersion` 版本号作为显式依赖，每次写入递增
- **回滚**：改动集中在 `chartHistory.ts`，出问题回退单个文件即可恢复全量拷贝模式
