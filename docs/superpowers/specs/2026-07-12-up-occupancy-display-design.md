# 区段占用状态栏 — 上行展示条设计

**日期：** 2026-07-12
**状态：** 已确认

## 背景

当前 `OccupancyDisplay.tsx` 只渲染一条下行（`direction: down`）轨道电路色块条。
实际线路分上下行两条独立轨道，需要展示上行方向的区段占用状态。

## 数据结构

**TrackCircuit 类型（已有，无需修改）：**
```typescript
interface TrackCircuit {
  id: string;
  start_chainage: number;
  end_chainage: number;
  direction: 'up' | 'down' | 'both';
  occupied: boolean;
}
```

## 改动范围

### 后端（1 文件）

**`backend/sim_engine/config/track.yaml`**

现有 23 个下行区段（TC01-TC23, `direction: down`）保持不变。
新增 23 个上行区段（TC01U-TC23U, `direction: up`），公里标与下行完全一致：

```yaml
  - { id: TC01U, start_chainage: 0,     end_chainage: 1100,  direction: "up" }
  - { id: TC02U, start_chainage: 1100,  end_chainage: 2000,  direction: "up" }
  ...
  - { id: TC23U, start_chainage: 17700, end_chainage: 18600, direction: "up" }
```

无上行列车运行时，这些区段的 `occupied` 为 `false`（全绿）。
后续引入上行列车时，`OccupancyDetector` 自动按位置匹配并标记占用。

**其他后端文件：** `OccupancyDetector`、`orchestrator.py`、`models.py` 均无需修改。

### 前端（1 文件）

**`frontend/src/components/views/track/OccupancyDisplay.tsx`**

核心改动：

1. **数据拆分** — 从 `circuits` 中按 `direction` 过滤：
   ```typescript
   const downCircuits = circuits.filter(c => c.direction === 'down');
   const upCircuits   = circuits.filter(c => c.direction === 'up');
   ```

2. **SVG 双条渲染** — 下行 `y=30`，上行 `y=50`，共用标尺和车站标签。
   列车标记仍画在下行条上方。

3. **分方向统计** — 底部摘要拆为两行，各显示方向标签 + 区段数/占用/空闲。

## 视觉效果

```
┌──────────────────────────────────────────┐
│ 🔲 区段占用状态                           │
│                                          │
│  标尺: 0m  2000m  4000m  ...  18600m    │
│                                          │
│ ↓下行 ██████░░░░░░████████░░░░░░        │
│ ↑上行 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │
│                                          │
│  车站: 安河桥北 ... 公益西桥              │
│                                          │
│ ↓ 下行  ●23区段 ●占用2 ●空闲21          │
│ ↑ 上行  ●23区段 ●占用0 ●空闲23          │
└──────────────────────────────────────────┘
```

## 不做的事

- 不修改 `apiAdapter.ts` — 已在上次改动中映射 `track.occupancy`
- 不修改 `TrackCircuit` 类型 — 已有 `direction` 字段
- 不修改后端 `OccupancyDetector` — 按位置匹配，天然兼容上行区段
- 不添加新的后端 API — 数据流不变
