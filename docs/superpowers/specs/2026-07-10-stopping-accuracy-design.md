# 停车精度测量与显示 — 设计文档

> 迭代一，MVP 范围
> 实现车辆停靠位置与目标站台之间距离的实时测量和前端显示

---

## 1. 动机

目前仿真系统在列车到站时只做布尔判断（是否在 `station_stop_tolerance` 范围内），不记录实际停靠位置与站台位置的偏差值。用户无法直观了解列车对标的精度。

## 2. 需求

- **实时显示**：列车运行中/停稳后，前端始终显示距前方目标站的距离
- **停车误差**：停稳后该距离值即为停车误差（正=冲过站台，负=未到站台）
- **历史可查**：每站停车误差在车站信息卡片中可查（StationLayout 扩展）

## 3. 架构

```
ThreeStageController                    Snapshot.build()               WebSocket
┌─────────────────────┐   每步写入     ┌──────────────────┐   推送     ┌──────────┐
│ distance_to_station │ ───────────→  │ distanceToStation │ ────────→ │ 前端状态  │
│ target_station_id   │               │ targetStationId   │           └──────────┘
│ stopping_error      │               │ stoppingError     │
└─────────────────────┘               └──────────────────┘
```

**核心公式**：`distanceToStation = station.chainage - train.position`

- 运行中：正数 = 距前方站还有多远
- 停稳后：正数 = 未到站，负数 = 冲过站，零 = 精准对标

## 4. 后端改造

### 4.1 `TrainSignalState`（`three_stage.py`）

新增字段：

```python
distance_to_station: float = 0.0   # 距当前目标站距离 (m)
target_station_id: str = ""         # 当前目标站 ID
```

在 `compute_commands` 方法末尾统一更新：

```python
target = self.track.next_station_ahead(train.position)
if target is not None:
    st.target_station_id = target.id
    st.distance_to_station = target.chainage - train.position
else:
    st.target_station_id = ""
    st.distance_to_station = 0.0
```

### 4.2 `TrainState`（`vehicle/models.py`）

`TrainState` 增加两个字段，供 snapshot 构建函数读取：

```python
distance_to_station: float = 0.0  # 距当前目标站距离 (m)
target_station_id: str = ""        # 当前目标站 ID
```

### 4.3 `Orchestrator.step_once`（`orchestrator.py`）

`step_once` 中调用 `signaling.compute_commands` 后，`TrainSignalState` 中已包含 `distance_to_station` 和 `target_station_id`。在 `vehicle.step()` 返回后，将这两个值从信号状态复制到 `TrainState`，供 snapshot 构建：

```python
cmd = self.signaling.compute_commands(self.train_state, dt)
# ... 执行车辆动力学 step ...
result = self.vehicle.step(self.train_state, cmd, track_params, dt, ...)
self.train_state = result.state

# 复制信号系统的距站距离到 TrainState
sig_st = self.signaling.signal_state
self.train_state.distance_to_station = sig_st.distance_to_station
self.train_state.target_station_id = sig_st.target_station_id
```

### 4.4 `build_simulation_snapshot`（`snapshot.py`）

在 `trains[]` 列表中新增两个字段：

```python
"distanceToStation": state.distance_to_station,  # 距目标站距离 (m)
"targetStationId": state.target_station_id,       # 目标站 ID
```

## 5. 前端改造

### 5.1 类型扩展（`types/simulation.ts`）

`TrainState` 增加：

```typescript
distance_to_station: number;  // 距目标站距离 (m)
target_station_id: string;    // 目标站 ID
```

`ApiTrainState` 增加对应 camelCase 字段：

```typescript
distanceToStation: number;
targetStationId: string;
```

### 5.2 API 适配（`apiAdapter.ts`）

`mapTrain` 中增加映射：

```typescript
distance_to_station: t.distanceToStation ?? 0,
target_station_id: t.targetStationId ?? "",
```

### 5.3 StatusCards 改造

新增第四张卡片「距站台距离」，替换原有的"信号授权"卡片：

```tsx
{
  label: '距站台',
  value: distanceText,
  icon: '📍',
  color: distanceColor,
}
```

显示逻辑：

| 条件 | 显示 |
|------|------|
| 有目标站，距离 > 0，列车运动 | `距 XX站 +12.3m` |
| 有目标站，距离 > 0，列车停稳 | `距 XX站 +1.2m 已停稳` |
| 有目标站，距离 ≤ 0，列车停稳 | `距 XX站 -0.5m 已过站` |
| 无目标站 | `--` |

颜色逻辑：
- 距离绝对值 ≤ 1.0m（容差内）：绿色 `#52c41a`
- 距离绝对值 > 1.0m：红色 `#ff4d4f`

### 5.4 StationInfoCard 改造

在车站信息卡片中增加"停车误差"行：

```tsx
<div style={styles.row}>
  <span style={styles.label}>停车误差:</span>
  <span style={{ color: errorColor }}>
    {station.stopping_error != null ? `${station.stopping_error > 0 ? '+' : ''}${station.stopping_error.toFixed(1)}m` : '--'}
  </span>
</div>
```

同时在 `StationLayout` 中增加 `stopping_error` 字段，供卡片读取。

## 6. 边界情况

| 场景 | 处理 |
|------|------|
| 无前方车站（终点已过） | `distanceToStation = 0`，前端显示 `--` |
| 列车刚启动（首站离站） | 目标站为下一站，显示正数距离 |
| 站停期间（DWELL 阶段） | 距离保持停稳时的误差值 |
| 负值（冲过站台） | 显示"已过 Xm"，红色高亮 |
| 精度显示 | 小数点后 1 位（±0.1m 精度足够） |
| WebSocket 断连重连 | 从最新快照恢复，无需额外同步 |

## 7. 测试

### 后端测试

- `test_distance_to_station_running`：列车在区间运行时距离为正
- `test_distance_to_station_stopped_accurate`：停稳时距离 ≈ 0
- `test_distance_to_station_stopped_overrun`：冲过站台时距离为负
- `test_distance_to_station_no_target`：无前方目标站时距离为 0

### 前端测试

- `StatusCards` 中距站台信息在列车运行/停稳时正确渲染
- 颜色逻辑正确（绿/红切换）

## 8. 不涉及的范围（迭代一不实现）

- 多列车场景下的各车独立距站距离
- 反向运行（下行方向）的站台匹配
- 历史停车精度统计图表