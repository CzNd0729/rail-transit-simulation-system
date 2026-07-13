# 多方案对比决策功能 — 设计文档

> **日期：** 2026-07-13
> **状态：** 设计确认
> **关联需求：** 基于 UI-PARAM-06（参数预设方案保存/加载）扩展，全新功能

---

## 一、概述

### 1.1 目标

让用户可以方便地保存仿真方案、对比不同方案之间的成本与价值，辅助真实世界中的方案选择决策。

### 1.2 工作流（B 方案）

用户先跑仿真，再保存为方案，最后对比：

```
调参数 → 跑仿真 → 看结果满意 → 保存为方案（命名）
  ↓
改参数 → 再跑 → 再保存为另一个方案
  ↓
打开对比页 → 勾选方案 → 并排对比指标
```

### 1.3 设计原则

- **零新增依赖** — 不引入数据库，不引入新 Python 包
- **最小改动** — 尽量复用现有 API 和数据模型
- **渐进式** — 先做核心 CRUD + 对比，成本模型等后续扩展

---

## 二、数据模型

### 2.1 方案存储

每个方案一个 JSON 文件，存储在 `backend/sim_engine/data/scenarios/` 目录下。

```json
{
  "id": "scenario_20260713_001",
  "name": "ATO经济模式",
  "description": "ATO模式+低目标速度系数，节能优先",
  "createdAt": "2026-07-13T10:30:00Z",
  "params": {
    "vehicle": {
      "emptyMass": 220000,
      "passengerCapacity": 1460,
      "maxSpeed": 80,
      "maxTractionForce": 300000,
      "maxBrakeForce": 260000,
      "davisA": 0.012,
      "davisB": 0.0001,
      "davisCFrontArea": 8.5,
      "davisCDragCoeff": 0.5,
      "curveResistCoeff": 600,
      "tunnelResistFactor": 1.2,
      "tractionCurve": [{ "speed": 0, "forcePercent": 1.0 }, { "speed": 40, "forcePercent": 1.0 }, { "speed": 80, "forcePercent": 0.5 }]
    },
    "signal": {
      "mode": "ato",
      "targetSpeedRatio": 0.7,
      "dwellTime": 30,
      "departureInterval": 120
    },
    "power": {
      "mode": "simple_ohm",
      "substationCapacity": 5000
    },
    "simulation": {
      "trainCount": 1,
      "bidirectional": false
    }
  },
  "result": {
    "totalTime": 185.3,
    "totalDistance": 3200.0,
    "avgSpeed": 45.2,
    "maxSpeed": 64.1,
    "tractionEnergy": 28.5,
    "regenEnergy": 4.2,
    "netEnergy": 24.3,
    "minVoltage": 1380,
    "peakPower": 3200
  }
}
```

### 2.2 字段说明

| 字段 | 来源 | 说明 |
|:----|:-----|:-----|
| `params.vehicle` | `get_params()` 返回值 | 车辆全部运行时参数 |
| `params.signal` | `get_params()` 返回值中的 signal 部分 | 信号/驾驶策略参数 |
| `params.power` | `get_params()` 返回值中的 power 部分 | 供电策略参数 |
| `params.simulation` | `get_config()` 中的 simulation 部分 | 仿真运行参数 |
| `result.totalTime` | `DataRecorder.summary().total_time` | 总仿真运行时间 (s) |
| `result.totalDistance` | `DataRecorder.summary().max_position` | 总运行里程 (m) |
| `result.avgSpeed` | `DataRecorder.summary().avg_speed` | 平均速度 (km/h) |
| `result.maxSpeed` | `DataRecorder.summary().max_speed` | 最大速度 (km/h) |
| `result.tractionEnergy` | `snapshot.data.power.totalConsumption` | 总牵引能耗 (kWh) |
| `result.regenEnergy` | `snapshot.data.power.totalRegeneration` | 总再生制动电量 (kWh) |
| `result.netEnergy` | 计算：tractionEnergy - regenEnergy | 净能耗 (kWh) |
| `result.minVoltage` | 从 `voltageProfile` 中提取最小值 | 网压最低值 (V) |
| `result.peakPower` | 从 `substations[*].outputPower` 中提取最大值 | 变电所峰值功率 (kW) |

### 2.3 存储方式

```
backend/sim_engine/data/scenarios/
├── scenario_20260713_001.json
├── scenario_20260713_002.json
└── scenario_20260713_003.json
```

- 文件名 = 方案 ID（`scenario_<日期>_<序号>.json`）
- 增删改查直接操作 JSON 文件，`json` 标准库读写
- 方案列表从 `os.listdir()` 扫描目录获得

---

## 三、后端 API 设计

### 3.1 路由

在 `sim_engine/api/` 下新增 `scenarios.py`，注册到 `app.py`。

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|:----|:-----|:-----|:-------|:-----|
| `GET` | `/api/v1/scenarios` | 获取所有方案摘要列表 | — | `{ scenarios: [{ id, name, createdAt, totalTime, netEnergy, ... }] }` |
| `POST` | `/api/v1/scenarios` | 保存当前参数+结果为方案 | `{ name, description? }` | `{ id, name }` |
| `GET` | `/api/v1/scenarios/{id}` | 获取方案完整详情 | — | `{ id, name, params, result, ... }` |
| `DELETE` | `/api/v1/scenarios/{id}` | 删除方案 | — | `{ success: true }` |
| `PUT` | `/api/v1/scenarios/{id}/apply` | 加载方案参数到引擎 | — | `{ config }` |

### 3.2 核心逻辑

**POST** 保存方案时的数据收集流程：

```
1. 接收 { name, description? }
2. 检查当前引擎状态（允许空闲/刚跑完，不要求运行中）
3. 从 SimulationManager 获取：
   a. params = get_params()  → 当前车辆/信号/供电参数
   b. config = get_config()  → 当前 simulation 参数
   c. 从最新的 snapshot 提取 totalConsumption、totalRegeneration
   d. 从 recorder.summary() 提取 total_time、avg_speed、max_speed、max_position
   e. 从 voltageProfile 提取 min voltage
   f. 从 substation 数据提取 peak power
4. 组装为 scenario JSON 写入 scenarios/ 目录
5. 返回 { id, name }
```

**PUT /apply** 加载方案时的流程：

```
1. 读取方案 JSON 文件
2. 调用 simulation_manager.reset() 重置引擎
3. 逐项写入方案参数：
   a. update_params({ vehicle, signal, ... })
   b. update_config({ simulation, ... })
4. 返回当前配置给前端，前端刷新参数面板
5. 用户可在此基础上修改参数再跑
```

### 3.3 错误处理

| 场景 | 状态码 | 说明 |
|:-----|:------|:------|
| 引擎正在运行 | 409 | 运行中不允许保存/加载方案 |
| 方案 ID 不存在 | 404 | 文件不存在 |
| 场景目录无法写入 | 500 | 权限错误或磁盘满 |
| 保存时引擎无结果 | 400 | 引擎从未运行过，无结果可保存 |

---

## 四、前端设计

### 4.1 页面结构

在顶部栏新增一个导航按钮：

```
[综合] [供电] [信号] [车辆] [轨道]  |  [📊 方案对比]
```

点击后进入方案对比页面，页面分为左右两栏布局：

```
┌─────────────────────────────────────────────────────────────┐
│  顶部栏 (现有)                                                │
├──────────────────┬──────────────────────────────────────────┤
│  📋 方案管理      │  📊 多方案对比                            │
│                  │                                          │
│  [保存方案]       │  ┌───────┬──────────┬──────────┐        │
│  名称: [______]   │  │ 指标   │ ATO经济   │ 三段式重载 │        │
│  [💾 保存]       │  │ 总耗时  │ 185s     │ 210s     │        │
│                  │  │ 平均速度│ 45.2     │ 38.5     │        │
│  ☑ ATO经济       │  │ 净能耗  │ 24.3kWh  │ 32.1kWh  │        │
│  ☑ 三段式重载     │  │ ...     │          │          │        │
│  ☐ 高速方案       │  └───────┴──────────┴──────────┘        │
│                  │                                          │
│  [加载] [删除]   │  📈 能耗对比柱状图                        │
│                  │  ┌────────────────────────┐              │
│                  │  │  ████  ██████  ██      │              │
│                  │  │  ████  ██████  ██      │              │
│                  │  │  ATO   三段   高速     │              │
│                  │  └────────────────────────┘              │
└──────────────────┴──────────────────────────────────────────┘
```

### 4.2 组件树

```
ScenarioComparePage          ← 方案对比页面（新路由）
├── ScenarioSavePanel        ← 保存方案面板（左上）
├── ScenarioListPanel        ← 方案列表+勾选（左中）
│   └── ScenarioListItem     ← 单行显示
├── CompareTable             ← 对比表格（右上）
├── CompareChartBar          ← 柱状图对比（右下，ECharts）
└── ScenarioDetailModal      ← 点击方案可展开详情弹窗
```

### 4.3 交互流程

**保存方案：**
1. 用户输入名称，点击"保存"
2. 调用 `POST /api/v1/scenarios`
3. 成功后方案列表刷新，新方案出现在列表中

**加载方案：**
1. 选中一个方案，点击"加载"
2. 调用 `PUT /api/v1/scenarios/{id}/apply`
3. 成功后引擎重置，参数面板刷新为该方案的参数
4. 用户可在此基础上修改参数再跑

**对比方案：**
1. 勾选多个方案（复选框，至少选 2 个）
2. 右侧对比表格自动更新，显示各方案的指标
3. 柱状图自动更新
4. 指标优劣用颜色标识（绿色最优、红色最差）

### 4.4 新增/修改文件清单

| 文件 | 操作 | 说明 |
|:----|:----|:-----|
| `frontend/src/pages/ScenarioComparePage.tsx` | 新增 | 方案对比页面主入口 |
| `frontend/src/components/scenario/ScenarioSavePanel.tsx` | 新增 | 保存方案面板 |
| `frontend/src/components/scenario/ScenarioListPanel.tsx` | 新增 | 方案列表+勾选 |
| `frontend/src/components/scenario/CompareTable.tsx` | 新增 | 对比表格 |
| `frontend/src/components/scenario/CompareChartBar.tsx` | 新增 | 柱状图对比 |
| `frontend/src/services/api.ts` | 修改 | 新增方案 CRUD API 调用 |
| `frontend/src/components/topbar/TopBar.tsx` | 修改 | 加"方案对比"导航按钮 |
| `frontend/src/App.tsx` | 修改 | 注册新路由 |

---

## 五、DataRecorder 扩展

当前 `DataRecorder.summary()` 不包含能耗和网压数据，需要扩展：

```python
@dataclass
class SimulationSummary:
    steps: int = 0
    total_time: float = 0.0
    avg_speed: float = 0.0
    max_speed: float = 0.0
    total_distance: float = 0.0
    # 新增字段（迭代二已实现的数据）
    traction_energy: float = 0.0    # 总牵引能耗 (kWh)
    regen_energy: float = 0.0       # 总再生制动电量 (kWh)
    min_voltage: float = 1500.0     # 网压最低值 (V)
    peak_power: float = 0.0         # 变电所峰值功率 (kW)
```

但在方案保存的场景中，这些数据实际上可以从 `snapshot` 和 `TrainState` 中直接获取，不需要改 `DataRecorder` 的底层逻辑。方案保存时从最新状态提取即可。

---

## 六、不做的事项

以下内容明确不在本次设计范围内，后续迭代考虑：

1. **成本模型**（电费单价、时间价值折算）— 等对比功能本身跑通后再加
2. **批量无头运行** — 手动跑一个保存一个，不做自动批量
3. **方案编辑** — 保存后不可编辑参数，只能删除重建
4. **方案分组/标签** — 简单列表即可，不做复杂分类
5. **方案导入/导出** — 后续迭代再说
6. **雷达图/蜘蛛网图** — 后续迭代再说

---

## 七、边界情况与错误处理

| 场景 | 处理方式 |
|:-----|:---------|
| 引擎从未运行过就点保存 | 提示"请先运行一次仿真" |
| 引擎正在运行时点保存 | 提示"请先暂停或停止仿真" |
| 引擎正在运行时点加载 | 提示"请先暂停或停止仿真" |
| 方案列表为空 | 显示"暂无方案，请先运行仿真后保存" |
| 勾选 < 2 个方案 | 对比表格提示"请勾选至少 2 个方案进行对比" |
| 方案文件损坏 | 显示"方案数据异常"并跳过该方案 |
| 场景目录不存在 | 自动创建 `scenarios/` 目录 |

---

## 八、验收标准

| 编号 | 场景 | 操作步骤 | 预期结果 |
|:----|:-----|:---------|:---------|
| SC-01 | 保存方案 | 运行仿真 → 输入名称 → 点保存 | 方案出现在列表中，含指标摘要 |
| SC-02 | 加载方案 | 选中方案 → 点加载 | 引擎重置，参数面板刷新为该方案参数 |
| SC-03 | 多方案对比 | 勾选 2+ 个方案 | 对比表格显示各方案指标，颜色标识优劣 |
| SC-04 | 删除方案 | 选中方案 → 点删除 | 方案从列表移除，JSON 文件删除 |
| SC-05 | 运行中拦截 | 运行中点保存/加载 | 提示冲突，禁止操作 |
| SC-06 | 重复保存 | 连续跑 3 次各保存一次 | 列表出现 3 个方案，各自拥有独立结果 |