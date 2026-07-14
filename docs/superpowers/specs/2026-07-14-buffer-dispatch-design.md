# 存车线缓冲区调度方案设计

> **日期：** 2026-07-14
> **状态：** 设计完成
> **目标：** 解决双端持续发车时折返列车与反向新车冲突的问题

---

## 一、问题描述

当前系统在 `timetable.yaml` 中配置了 ST01（下行）和 ST24（上行）**双端同时发车**，发车间隔 150s。当 ST01 发出的列车到达 ST24 折返后，与 ST24 独立发出的上行列车在同一个方向上形成"两路车流"，导致：

- 上行方向列车密度翻倍，间隔不可控
- 折返列车与新车之间无协调机制
- 线路上的列车数量持续增长，无法进入稳态

## 二、设计原则

1. **有旧车发旧车，没旧车发新车** — 核心调度规则，一句说清
2. **两端对称** — ST01 和 ST24 执行完全相同的逻辑
3. **自然过渡** — 不需要复杂计算，系统自动从初始阶段过渡到稳态
4. **最小改动** — 在现有 `FleetScheduler` 基础上增量修改，不重构

## 三、核心概念

### 3.1 车辆的双重标识

| 标识 | 示例 | 生命周期 | 作用 |
|------|------|---------|------|
| `vehicle_id` | `VEH_001` | 物理车辆终身不变 | 跟踪总里程、总趟数、当前位置 |
| `train_id` | `D01`, `U01` | 每趟一换 | 运营车次号，前端展示 |

### 3.2 存车线缓冲区（Buffer）

两端终点站各设一个缓冲区，用于存放到达的列车：

- 下行列车到达 ST24 → 存入 ST24 缓冲区
- 上行列车到达 ST01 → 存入 ST01 缓冲区
- 缓冲区容量：可配置（默认 1 个车位，实际需要 ≥ 1）
- 调度时优先从缓冲区取车 → 缓冲区空才发新车

### 3.3 两阶段自然过渡

| 阶段 | 时间范围 | 描述 | 发车行为 |
|------|---------|------|---------|
| ① 初始阶段 | t=0 ~ t≈单程时间 | 两端缓冲区都为空 | 两端都发新车 |
| ② 稳态阶段 | t≈单程时间之后 | 第一列车到达对面后，缓冲区开始有车 | 有旧车发旧车，缓冲区空时才发新车 |

进入稳态后，**系统不再产生新车**，所有车辆在 A↔B 之间循环运行。

## 四、数据模型

### 4.1 新增：BufferSlot

```python
@dataclass
class BufferSlot:
    """存车线中的一列车。"""
    vehicle_id: str          # 终身不变的车辆ID，如 VEH_001
    previous_train_id: str   # 上一趟的服务号，如 D01
    total_trips: int         # 已跑趟数
    total_mileage: float     # 已跑总里程 (m)
    passenger_load: float    # 载客率，保留
    state: TrainState        # 保留列车物理状态（质量等）
    arrival_time: float      # 进入存车线的时间
```

### 4.2 修改：DispatchOrigin

```python
@dataclass(frozen=True)
class DispatchOrigin:
    # ... 原有字段不变 ...
    buffer_capacity: int = 1   # 存车线容量，默认1个车位
```

### 4.3 修改：TrainRun

```python
@dataclass
class TrainRun:
    # ... 原有字段不变 ...
    vehicle_id: str = ""       # 物理车辆ID
    total_trips: int = 0       # 已跑趟数
    total_mileage: float = 0.0 # 已跑总里程
```

## 五、调度核心逻辑

### 5.1 FleetScheduler.tick() 改造

```
tick(elapsed, active_runs, create_run):
  遍历每个发车端（origin）：
    while elapsed >= stream.next_departure_time 且 未超最大列车数 且 净空足够:
      ① 检查本端存车线 buffer
      ② 有旧车 → 弹出 → 换向 → 重命名服务号 → 发车
      ③ 没旧车 → 发新车（分配新 vehicle_id）
      ④ 推进下次发车时间
```

### 5.2 列车到达终点处理

```
Orchestrator.step_once() 中，每步检查：
  for each active train:
    if 到达终点站且停稳:
      ① 创建 BufferSlot（记录 vehicle_id, train_id, 趟数, 里程等）
      ② 存入本端存车线
      ③ 标记为 inactive（不再参与步进）
```

### 5.3 发车端"旧车换向"逻辑

从缓冲区取出的列车：
- **vehicle_id** 不变（终身跟踪）
- **train_id** 重新编号（运营车次号，如 D14, U14）
- **direction** 按发车端初始方向设置
- **position** 重置到始发站 chainage
- **total_trips** +1
- **total_mileage** 累加上一趟的行驶距离

### 5.4 列车 ID 命名规则

```
VEH_001 的旅程：
  D01  (ST01→ST24, 下行)   ← 新车
  U14  (ST24→ST01, 上行)   ← 折返后重命名
  D15  (ST01→ST24, 下行)   ← 再到 ST01 折返后重命名
  U15  (ST24→ST01, 上行)
  ...
```

前缀 `D`/`U` 表示当前方向，序列号全局递增。

## 六、配置改动

### timetable.yaml

```yaml
dispatch:
  mode: continuous
  max_active_trains: 40
  min_origin_clearance_m: 500
  origins:
    - origin_station: ST01
      initial_direction: down
      trip_legs: [down, up]
      train_id_prefix: D
      first_departure_s: 0
      headway_s: 150
      buffer_capacity: 1
    - origin_station: ST24
      initial_direction: up
      trip_legs: [up, down]
      train_id_prefix: U
      first_departure_s: 0
      headway_s: 150
      buffer_capacity: 1
```

## 七、WebSocket Snapshot 新增字段

每步推送新增 `bufferState`：

```json
{
  "data": {
    "trains": [...],
    "bufferState": {
      "ST01": [
        {"vehicleId": "VEH_012", "previousTrainId": "D12", "arrivalTime": 2150.0}
      ],
      "ST24": [
        {"vehicleId": "VEH_001", "previousTrainId": "D01", "arrivalTime": 2000.0}
      ]
    }
  }
}
```

## 八、前端展示

### 8.1 存车线可视化

在综合视图中，两端各增加一个存车线图标，显示当前停放的车辆数。

### 8.2 车辆追踪面板

控制面板新增"车辆列表"标签页：

| 车辆ID | 当前服务号 | 方向 | 位置 | 趟数 | 里程 | 状态 |
|--------|-----------|------|------|------|------|------|
| VEH_001 | D01 | 下行 | ST05→ST06 | 1 | 4.5km | active |
| VEH_002 | U01 | 上行 | ST20→ST19 | 1 | 16.2km | active |
| VEH_003 | — | — | ST24 | 0 | 0km | buffer |

### 8.3 列车总数曲线

显示列车总数随时间的变化曲线，从初始阶段上升到稳态后形成平台期。

## 九、代码改动清单

| 文件 | 改动 | 预估行数 |
|------|------|---------|
| `signaling/models.py` | 新增 `BufferSlot`，`DispatchOrigin` 增加 `buffer_capacity` | +20 行 |
| `signaling/fleet_scheduler.py` | 新增缓冲区管理、`receive_train()`、缓冲区优先调度 | +80 行 |
| `orchestrator.py` | 到站进存车线逻辑、`_create_train_run()` 支持 vehicle_id | +30 行 |
| `data/snapshot.py` | snapshot 新增 `bufferState` 字段 | +5 行 |
| `config/timetable.yaml` | 增加 `buffer_capacity: 1` | +2 行 |
| **总计** | | **~140 行** |

## 十、自审检查

- [x] 所有字段有明确含义和默认值
- [x] 无 TBD/TODO 占位
- [x] 架构与现有代码一致，增量修改
- [x] 边界情况明确（缓冲区空时发新车、缓冲区满时？——当前设计不会满，因为发车频率与到达频率一致）
- [x] 前端展示列为可选，不影响后端核心功能