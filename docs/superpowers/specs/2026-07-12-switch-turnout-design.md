# 道岔子系统设计

> 迭代二 TRK-06/TRK-08/TRK-09：道岔建模、状态查询、控制接口
> 2026-07-12

## 一、范围

- 后端：`Switch` 数据模型 + YAML 配置 + `SwitchManager`（查询/控制/转换时延）+ snapshot 数据流
- 前端：`SwitchStatus.tsx` 对接后端实时数据（已有组件，仅打通数据流）
- 不涉及：SVG 轨道条带图修改、信号系统自动联动（接口预留，逻辑留待后续）

## 二、道岔配置

| ID | 位置 | chainage | 类型 | 用途 | 侧向限速 |
|----|------|----------|------|------|----------|
| SW01 | 安河桥北 | 50 | crossover | 北端折返 | 30 km/h |
| SW02 | 国家图书馆 | 7300 | single | 换乘站，侧线待避 | 30 km/h |
| SW03 | 北京南站 | 15900 | single | 枢纽站，侧线待避 | 30 km/h |
| SW04 | 公益西桥 | 18550 | crossover | 南端折返 | 30 km/h |

默认状态均为 `normal`（正线直向）。

## 三、数据模型

```python
@dataclass
class Switch:
    id: str                          # SW01~SW04
    chainage: float                  # 道岔中心公里标
    switch_type: str                 # "single" / "crossover"
    normal_direction: str            # "main"（正线直向）
    reverse_direction: str           # "siding"（侧线）
    lateral_speed_limit: float       # 侧向限速 km/h
    state: str                       # "normal" / "reverse" / "transitioning"
    transition_time: float = 3.0     # 转换时延 (s)
    transition_elapsed: float = 0.0  # 已转换时间
```

`Track` 新增字段：`switches: list[Switch]`

## 四、SwitchManager (`track/switch.py`)

```
SwitchManager(switches: list[Switch])
  ├── query(switch_id) → Switch | None
  ├── set_state(switch_id, target: "normal"|"reverse")
  │      → 设置 state="transitioning", transition_elapsed=0
  ├── update(dt: float) → 推进所有 transitioning 道岔
  │      └── 若 elapsed >= transition_time → state = target_state
  └── switch_list() → list[dict]  供 snapshot 序列化
       {"switchId", "chainage", "type", "normalDirection",
        "reverseDirection", "lateralSpeedLimit", "state",
        "transitionElapsed", "transitionTime"}
```

## 五、后端变更文件

| 文件 | 操作 |
|------|------|
| `track/models.py` | 新增 `Switch` dataclass；`Track` 增加 `switches` |
| `track/config.py` | 加载 `switches` 配置段 |
| `config/track.yaml` | 新增 `switches:` 配置（4 组） |
| `track/switch.py` | **新建** `SwitchManager` |
| `track/__init__.py` | 导出 `Switch`、`SwitchManager` |
| `orchestrator.py` | 初始化 `SwitchManager`；每步 `update(dt)`；传入 snapshot |
| `data/snapshot.py` | 新增 `switch_states` 参数，替换硬编码空数组 |

## 六、前端变更文件

| 文件 | 操作 |
|------|------|
| `utils/apiAdapter.ts` | 映射 `track.switchStates` → `Switch[]` |
| `SwitchStatus.tsx` | **无需改代码** — 已有 `track.switch_states` 消费逻辑，数据流通则自动生效 |

## 七、数据流

```
Orchestrator.step_once()
  → switch_manager.update(dt)              # 推进转换时延
  → snapshot["track"]["switchStates"]
      = switch_manager.switch_list()
  → WebSocket 推送
  → apiAdapter.ts 映射 switchId/chainage/type/state...
  → SimulationContext.track.switch_states
  → SwitchStatus.tsx 渲染状态面板
```

## 八、转换时延模拟

```
set_state("SW01", "reverse"):
  state ← "transitioning"
  transition_elapsed ← 0

每帧 update(dt):
  if state == "transitioning":
    transition_elapsed += dt
    if transition_elapsed >= transition_time:
      state ← target_state
      transition_elapsed ← transition_time
```

## 九、测试覆盖

- `SwitchManager.query()` — 存在/不存在 ID
- `SwitchManager.set_state()` — 正常切换、无效状态拒绝、已转换中拒绝
- `SwitchManager.update()` — 时延推进、到达阈值自动完成
- `SwitchManager.switch_list()` — 序列化格式验证
- 配置加载 — 4 组道岔字段完整性
- 覆盖率目标 ≥ 90%
