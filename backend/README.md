# 仿真引擎后端 — 车辆系统（迭代一 MVP）

本目录目前实现**车辆系统 (`sim_engine.vehicle`)** 纯模块，负责单质点列车动力学
解算，供仿真编排器集成。不包含编排器、轨道 / 信号 / 供电、REST API 与前端。

## 目录结构

```
backend/
├── requirements.txt
├── pytest.ini
├── sim_engine/
│   ├── __init__.py
│   ├── config/
│   │   └── vehicle.yaml          # 车辆默认参数（A 型车）
│   └── vehicle/
│       ├── __init__.py           # 对外导出类型 / 引擎 / 配置加载
│       ├── models.py             # I/O 数据类型（本模块类型契约）
│       ├── traction.py           # 牵引特性曲线插值（VHC-02）
│       ├── resistance.py         # Davis / 坡度 / 弯道 / 隧道阻力（VHC-03~06）
│       ├── dynamics.py           # 动力学解算 VehicleSystem（VHC-01/07/08/10）
│       └── config.py             # YAML 参数加载
└── tests/
    └── test_vehicle.py           # 单元测试（覆盖率 ≥ 80%）
```

## 覆盖的需求

| 编号 | 功能 | 实现位置 |
|------|------|----------|
| VHC-01 | 牛顿第二定律动力学解算 | `dynamics.VehicleSystem.step` |
| VHC-02 | 牵引特性曲线（分段线性） | `traction.py` |
| VHC-03 | Davis 基本阻力 | `resistance.davis_resistance` |
| VHC-04 | 坡度附加阻力 | `resistance.gradient_resistance` |
| VHC-05 | 弯道附加阻力 | `resistance.curve_resistance` |
| VHC-06 | 隧道空气阻力 | `resistance.tunnel_resistance` |
| VHC-07 | 限速约束 | `dynamics.step`（速度钳位） |
| VHC-08 | 站台对标停车（不倒退） | `dynamics.step`（过零钳位） |
| VHC-09 | 能耗计算 | `models.TrainState` 预留字段（迭代一不累计） |
| VHC-10 | 输出记录 | `models.ForceBreakdown` / `StepResult` |

## 集成接口

车辆系统与其他子系统通过 `sim_engine.vehicle.models` 中的 dataclass 交互：

- **输入**：`ControlCommands`（信号系统控车指令）、`TrackPointParams`（轨道系统线路参数）、当前 `TrainState`、步长 `dt`
- **输出**：`StepResult`（新 `TrainState` + `ForceBreakdown` 受力分解）

编排器典型用法：

```python
from sim_engine.vehicle import (
    VehicleSystem, ControlCommands, TrackPointParams,
)

# 方式一：直接构造对象（便于测试）
veh = VehicleSystem(params)

# 方式二：从 YAML 加载参数
veh = VehicleSystem.from_config("sim_engine/config/vehicle.yaml")

state = veh.create_initial_state(position=0.0, passenger_load=0.6)
cmd = ControlCommands(traction_level=1.0)        # 来自信号系统
track = TrackPointParams(gradient=5, speed_limit=80)  # 来自轨道系统

result = veh.step(state, cmd, track, dt=0.1)
state = result.state                              # 循环推进
```

**单位约定**：对外速度均为 km/h，位置为 m，力为 N，时间步长 `dt` 为秒；内部
动力学换算为 m/s。

**关键建模假设**：

- 积分采用显式（半隐式）欧拉法：先由合力更新速度，再用新速度更新位置。
- 制动力与速度无关：`F_brake = max_brake_force × brake_level`（紧急制动取最大值）。
- 弯道阻力按比阻力 `r_c(‰) = k / R` 折算为力（与坡度同量纲口径）。
- 隧道阻力为 Davis 基本阻力的 `(factor - 1)` 倍附加。
- 工况由控车指令派生：制动 > 牵引 > 惰行。

## 运行

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest          # 运行测试并输出覆盖率
```
