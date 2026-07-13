# 真实时刻表 + 折返交路设计

**日期：** 2026-07-13  
**范围：** 北京地铁 4 号线参考运行图（手工 YAML）+ 时刻表驱动发车 + 道岔折返  
**数据源决策：** **方案 A** — 手工编写高峰参考运行图（发车间隔约 2–3 min，平峰约 4–5 min 作为后续预设）

---

## 1. 背景与目标

### 1.1 现状问题

| 问题 | 现状 |
|------|------|
| 发车 | `spawn_time = i × departure_interval`（默认 120s 等间隔） |
| 时刻表 | `timetable.yaml` 仅 ST01–ST03，多车靠整体平移 |
| 双向 | `bidirectional: true` 时上下行**两端同时独立发车**，非折返 |
| 道岔 | `SwitchManager` 已实现，无信号/折返联动 |
| 终点 | 到终点站停稳即仿真结束，无换向 |

### 1.2 目标

1. **时刻表驱动发车**：按 YAML 定义的发车间隔（高峰 150s / 平峰 270s）从始发站**持续派车**，不再固定 `train_count=3`。
2. **线路容量饱和**：单次运行内尽可能多发车，直至因 **SIG-07 追踪间隔**（`following_min_interval` 默认 500m）等原因无法从始发站安全加车——模拟地铁“跑满”状态。
3. **全线运行图**：覆盖 4 号线 24 站下行/上行站序，含站停与区间运行时分（leg 模板）。
4. **折返交路**：列车到达终点站后，经道岔（SW01/SW04）折返，换向后按下一 leg 继续运行。
5. **配置注入**：全部参数走 YAML（NFR-07），不硬编码。

### 1.3 不在范围（本阶段）

- 外部 CSV/JSON 导入（SIG-16 完整版，迭代三）
- 联锁 CI、发车条件联控（SIG-14）
- 平峰运行图自动生成工具（仅预留 `profile` 字段，手工另备一份 YAML）
- 前端时刻表在线编辑（UI-PARAM-07，迭代三）

---

## 2. 参考运行图参数（4 号线）

### 2.1 线路常量

- 线路：安河桥北（ST01, 0m）→ 公益西桥（ST24, 18600m），全长约 18.6 km
- 折返道岔：北端 **SW01**（50m）、南端 **SW04**（18550m）
- 站停时间：取自 `track.yaml` 各站 `dwell_time`

### 2.2 时分推算规则（手工基准）

手工编写时采用以下约定（与仿真 ATO 目标速度比 0.8 大致匹配，实施时可微调）：

| 参数 | 值 | 说明 |
|------|-----|------|
| 区间均速 | 50 km/h | 站间运行时分 = Δchainage ÷ (50/3.6) m/s，四舍五入取整秒 |
| 折返时间 | **150 s**（已确认） | 终点站停稳 → 道岔切换 + 进/出折返线 + 换端；与 4 号线站后/站前折返量级一致 |
| 高峰始发间隔 | **150 s**（已确认，严格等间隔） | 0 / 150 / 300 / 450 / … 每 2.5 min 尝试派车 |
| 平峰始发间隔（已确认） | **270 s** | 4.5 min；另备 `timetable_offpeak.yaml`，结构相同仅 `headway_s` 不同 |

推算结果（下行 leg 模板，相对首站发车）：

- 全线运行时分（ST01 发车 → ST24 停稳）：**1995 s**（约 33.3 min）
- ST24 站停后发车（相对仿真起点对 TRAIN_01）：**2030 s**
- 折返后上行首站（ST24）发车：**2180 s**（+150s 折返）
- 上行全线（ST24 → ST01 停稳）：再 **1995 s**，TRAIN_01 全程约 **4175 s**（≈69.6 min）

### 2.3 持续派车与线路饱和（核心变更）

**不再预置固定列车数。** 改为“运行图时钟 + 容量闸门”：

```
每 headway_s（高峰 150s）触发一次派车尝试：
  if 始发站（ST01）前方同向安全距离 ≥ following_min_interval:
    动态创建 TRAIN_NN，绑定 down→up leg 模板，立即发车
  else:
    本次派车阻塞（hold），下一仿真步继续重试，直至空隙满足或仿真结束
```

**饱和粗算（高峰 150s）：**

| 指标 | 估算 |
|------|------|
| 下行单程 | ~2030 s |
| 稳态下行管道车数 | ⌈2030 ÷ 150⌉ ≈ **14 列** |
| 理论里程上限 | ⌊18600 ÷ 500⌋ ≈ **37 列**（同向纯追踪间隔，实际上限更低） |
| 折返与上下行混跑后 | 实际“跑满”车数由仿真动态决定，以 snapshot 观测为准 |

**仿真结束条件（变更）：**

- 默认：**仅** `total_time` 到达或用户手动停止（不再依赖“预置 N 车全部到终点”）。
- 单次运行内尽可能多地派车；末班未能跑完全程亦属正常。

**安全上限：** `max_active_trains`（YAML，默认 40）防止无限创建列车拖垮性能。

### 2.4 已确认的设计决策

| 项 | 决策 |
|----|------|
| 发车间隔 | 高峰严格 **150 s** 等间隔（0/150/300/450/…） |
| 折返时间 | **150 s** 保留 |
| 平峰 | 本阶段高峰 `timetable.yaml` + 平峰 `timetable_offpeak.yaml`（270s） |
| 列车数量 | **动态派车**，替代 `train_count` 固定车队 |

---

## 3. YAML Schema（v2）

### 3.1 顶层结构

```yaml
timetable:
  meta:
    line_name: "北京地铁4号线"
    profile: peak_reference          # peak_reference | offpeak_reference
    turnback_time_s: 150
    default_turnback_switch:
      down: SW04
      up: SW01

  # 持续派车（替代固定 trains[] 列表）
  dispatch:
    mode: continuous                 # continuous | fixed（fixed 兼容旧 train_count）
    origin_station: ST01             # 派车起点
    initial_direction: down
    first_departure_s: 0
    headway_s: 150                   # 高峰 2.5 min；平峰文件改为 270
    # 可选：不均匀间隔模式，优先于 headway_s
    # headway_pattern_s: [150, 150, 180, 150]
    max_active_trains: 40            # 性能安全上限
    min_origin_clearance_m: 500      # 默认对齐 signal.following_min_interval

  # leg 模板：每列动态创建的车均执行 down → turnback → up
  leg_templates:
    down:
      direction: down
      terminal_station: ST24
      entries: [ ... ]               # 见 §3.2
    up:
      direction: up
      terminal_station: ST01
      entries: [ ... ]               # 见 §3.3
    trip_legs: [down, up]            # 每趟交路顺序
```

### 3.2 下行 leg 模板 `leg_templates.down.entries`

（`planned_arrival` / `planned_departure` 相对本 leg 首站 ST01 发车时刻，单位：秒）

```yaml
entries:
  - { station_id: ST01, planned_arrival: 0,    planned_departure: 35 }
  - { station_id: ST02, planned_arrival: 114,  planned_departure: 139 }
  - { station_id: ST03, planned_arrival: 204,  planned_departure: 234 }
  - { station_id: ST04, planned_arrival: 292,  planned_departure: 317 }
  - { station_id: ST05, planned_arrival: 375,  planned_departure: 400 }
  - { station_id: ST06, planned_arrival: 450,  planned_departure: 480 }
  - { station_id: ST07, planned_arrival: 538,  planned_departure: 568 }
  - { station_id: ST08, planned_arrival: 618,  planned_departure: 643 }
  - { station_id: ST09, planned_arrival: 701,  planned_departure: 726 }
  - { station_id: ST10, planned_arrival: 776,  planned_departure: 806 }
  - { station_id: ST11, planned_arrival: 878,  planned_departure: 908 }
  - { station_id: ST12, planned_arrival: 973,  planned_departure: 1013 }
  - { station_id: ST13, planned_arrival: 1071, planned_departure: 1096 }
  - { station_id: ST14, planned_arrival: 1146, planned_departure: 1176 }
  - { station_id: ST15, planned_arrival: 1226, planned_departure: 1251 }
  - { station_id: ST16, planned_arrival: 1294, planned_departure: 1319 }
  - { station_id: ST17, planned_arrival: 1369, planned_departure: 1404 }
  - { station_id: ST18, planned_arrival: 1462, planned_departure: 1487 }
  - { station_id: ST19, planned_arrival: 1545, planned_departure: 1570 }
  - { station_id: ST20, planned_arrival: 1635, planned_departure: 1660 }
  - { station_id: ST21, planned_arrival: 1710, planned_departure: 1750 }
  - { station_id: ST22, planned_arrival: 1822, planned_departure: 1847 }
  - { station_id: ST23, planned_arrival: 1905, planned_departure: 1930 }
  - { station_id: ST24, planned_arrival: 1995, planned_departure: 2030 }
```

### 3.3 上行 leg 模板 `leg_templates.up.entries`

（相对本 leg 在终点站的发车时刻；首条 ST24 的 `planned_arrival` 为终到站停稳，`planned_departure` 为折返后上行发车）

```yaml
entries:
  - { station_id: ST24, planned_arrival: 0,    planned_departure: 150 }   # 含折返作业
  - { station_id: ST23, planned_arrival: 215,  planned_departure: 240 }
  - { station_id: ST22, planned_arrival: 298,  planned_departure: 323 }
  - { station_id: ST21, planned_arrival: 395,  planned_departure: 435 }
  - { station_id: ST20, planned_arrival: 485,  planned_departure: 510 }
  - { station_id: ST19, planned_arrival: 575,  planned_departure: 600 }
  - { station_id: ST18, planned_arrival: 658,  planned_departure: 683 }
  - { station_id: ST17, planned_arrival: 741,  planned_departure: 776 }
  - { station_id: ST16, planned_arrival: 826,  planned_departure: 851 }
  - { station_id: ST15, planned_arrival: 894,  planned_departure: 919 }
  - { station_id: ST14, planned_arrival: 969,  planned_departure: 999 }
  - { station_id: ST13, planned_arrival: 1049, planned_departure: 1074 }
  - { station_id: ST12, planned_arrival: 1132, planned_departure: 1172 }
  - { station_id: ST11, planned_arrival: 1237, planned_departure: 1267 }
  - { station_id: ST10, planned_arrival: 1339, planned_departure: 1369 }
  - { station_id: ST09, planned_arrival: 1419, planned_departure: 1444 }
  - { station_id: ST08, planned_arrival: 1502, planned_departure: 1527 }
  - { station_id: ST07, planned_arrival: 1577, planned_departure: 1607 }
  - { station_id: ST06, planned_arrival: 1665, planned_departure: 1695 }
  - { station_id: ST05, planned_arrival: 1745, planned_departure: 1770 }
  - { station_id: ST04, planned_arrival: 1828, planned_departure: 1853 }
  - { station_id: ST03, planned_arrival: 1911, planned_departure: 1941 }
  - { station_id: ST02, planned_arrival: 2006, planned_departure: 2031 }
  - { station_id: ST01, planned_arrival: 2110, planned_departure: 2145 }
```

### 3.4 向后兼容

- 保留旧版单列车格式（`timetable.train_id` + `entries`）只读兼容一个版本周期。
- 保留 `dispatch.mode: fixed` + `simulation.train_count` 作为单车/固定车队 fallback。
- `simulation.yaml` 的 `departure_interval` / `train_count` 在 `dispatch.mode: continuous` 时**忽略**。

---

## 4. 架构

### 4.1 新增模块

```
signaling/
  fleet_scheduler.py    # 持续派车：headway 时钟 + 始发站容量闸门 + 动态 TrainRun 创建
  turnback.py           # 折返状态机 + 道岔联动
  timetable_loader.py   # 扩展 v2 加载、模板展开、绝对时刻换算
```

### 4.2 TrainRun 扩展

```python
@dataclass
class TrainRun:
    # ... 现有字段 ...
    leg_index: int = 0                    # 当前 leg（0=首趟下行）
    legs: list[Timetable] = ...           # 展开后的时刻表列表
    turnback_state: str | None = None     # None | "turnbacking" | "ready"
    spawn_time: float                     # 首趟绝对发车时刻（来自 origin_departure）
```

### 4.3 发车流程（持续派车，替代 `_spawn_trains` + 固定 `train_count`）

```
reset():
  trains = []                         # 空车队，无预创建
  FleetScheduler.reset()
  next_departure_time = first_departure_s
  train_serial = 0

每步 step_once() 开头:
  FleetScheduler.tick(elapsed):
    while elapsed >= next_departure_time
          and len(active_trains) < max_active_trains:
      if origin_clearance_ok(ST01, direction=down, min_origin_clearance_m):
        train_serial += 1
        create TrainRun(TRAIN_{serial:02d}, legs=[down,up])
        activate immediately
        next_departure_time += headway_s   # 或 headway_pattern 下一项
      else:
        break   # 线路“爆满”，本步不再派车，下步重试（不推进 next_departure_time）

  # 可选：若持续阻塞超过 max_departure_delay_s，记录调度告警（P2）

折返（TurnbackController）:
  列车在 terminal_station 停稳且 dwelled:
    → turnback_state = "turnbacking"
    → switch_manager.set_state(SW04|SW01, "reverse")
    → 等待 transition_time + turnback_time_s
    → flip direction, leg_index += 1
    → 加载 legs[leg_index] 到 ATS（绝对时刻 = 当前 elapsed + 相对偏移）
    → signaling.reset(direction=new_dir)
    → turnback_state = None
```

### 4.4 `bidirectional` 语义变更

| 配置 | 旧行为 | 新行为 |
|------|--------|--------|
| `bidirectional: true` | 上下行双端同时发车 | **废弃**；改读 `timetable.trains[].legs` 交路 |
| `bidirectional: false` | 单方向多车 | 默认；配合折返 leg |

`simulation.yaml` 将 `bidirectional` 默认改回 `false`，交路由时刻表 legs 定义。

### 4.5 折返状态机

```
IDLE
  → (到达 terminal & speed≈0 & 当前 leg 有下一 leg)
TURNBACK_REQUESTED
  → set_state(switch, reverse)
SWITCH_TRANSITIONING
  → (switch.state == reverse)
TURNBACK_DWELL
  → (elapsed >= turnback_time_s)
REVERSE_DIRECTION
  → load next leg timetable, signaling.reset
DEPARTING
  → 正常三段式运行
```

### 4.6 Snapshot 扩展（可选，P2）

```json
{
  "trainId": "TRAIN_01",
  "legIndex": 1,
  "turnbackState": "turnbacking",
  "direction": "up"
}
```

`track.switchStates` 已有，折返时可见 SW04 从 `normal` → `transitioning` → `reverse`。

---

## 5. 配置变更摘要

| 文件 | 变更 |
|------|------|
| `config/timetable.yaml` | 重写为 v2 高峰参考运行图（§3 全文） |
| `config/timetable_offpeak.yaml` | 新增（平峰 270s 间隔，结构相同） |
| `config/simulation.yaml` | `bidirectional: false`；`train_count` 在 continuous 模式下仅作 fallback |
| `core/config.py` | 检测 `dispatch.mode`；continuous 时忽略 `train_count` / `departure_interval` |

---

## 6. 测试与验收

| ID | 场景 | 预期 |
|----|------|------|
| AC-01 | t=0 首班发车 | TRAIN_01 从 ST01 下行出发 |
| AC-02 | t=150/300/450s | 严格每 150s 派一班，直至阻塞 |
| AC-03 | 线路饱和 | 始发站前方 &lt;500m 有同向车时停止派车；空隙出现后恢复 |
| AC-04 | `total_time=6000s` 高峰 | 累计派车数 ≥10（粗算），snapshot 同向多车可见 |
| AC-05 | TRAIN_01 到 ST24 | SW04 折返，换向上行 |
| AC-06 | ATS 偏离 | 每车每 leg 独立 `timetableDeviation` |
| AC-07 | `timetable_offpeak.yaml` | headway 270s，派车更稀疏 |
| AC-08 | `dispatch.mode: fixed` | 旧 `train_count` + `departure_interval` 行为不变 |

---

## 7. 文档冲突（需组长确认）

- `docs/需求文档.md` SIG-16/17 标为**迭代三**；本设计提前实现其核心子集（YAML 时刻表 + 偏离检测复用）。
- `docs/迭代二_单列车增强需求文档.md` 写明时刻表管理留待迭代三。
- 建议组长确认：作为**迭代三预研合入 dev**，或正式调整迭代边界。

---

## 8. 实施阶段（概要）

| 阶段 | 内容 | 预估 |
|------|------|------|
| P1 | v2 数据模型 + loader + 完整 `timetable.yaml` | 2d |
| P2 | `FleetScheduler` 替换等间隔 spawn | 1d |
| P3 | `TurnbackController` + 道岔联动 + 换向 | 3d |
| P4 | 编排器集成、`bidirectional` 清理、仿真结束条件 | 1d |
| P5 | 测试 + 前端 `TimetableChart` 多车全线（可选） | 2d |

详细逐步实施计划见：`docs/superpowers/plans/2026-07-13-real-timetable-turnback.md`（设计批准后编写）。

---

## 9. 自审清单

- [x] 无 TBD 占位：时刻表数值已按 §2.2 规则填满
- [x] 内部一致：spawn 用 `origin_departure`，折返用 `turnback_time_s`，与 leg 模板相对时间不冲突
- [x] 范围：不含 CSV 导入、不含联锁
- [x] 歧义消除：`bidirectional` 新语义已写明；持续派车与 `train_count` 关系已写明
- [x] 用户确认：150s 折返、150s 高峰间隔、平峰另备 YAML、动态派车至线路饱和
