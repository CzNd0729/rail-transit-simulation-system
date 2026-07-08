# CLAUDE.md — backend

This file provides guidance to Claude Code, Cursor, and CodeBuddy when working in the `backend/` directory.

## 技术栈

- Python 3.10+
- 依赖：`PyYAML>=6.0`、`pytest>=7.4`、`pytest-cov>=4.1`
- 无额外非必要第三方依赖（NFR-06）

## 常用命令

```bash
# 安装依赖（含开发依赖）
uv sync --extra dev

# 运行所有测试（含覆盖率报告）
uv run pytest

# 运行特定测试文件
uv run pytest tests/test_vehicle.py

# 运行特定测试函数
uv run pytest tests/test_vehicle.py::test_function_name -v

# 仅运行带有特定标记的测试
python -m pytest -v -k "keyword"

# 覆盖率报告（HTML 格式）
python -m pytest --cov=sim_engine --cov-report=html
```

## 项目结构

```
backend/
├── sim_engine/
│   ├── __init__.py              # 包入口
│   ├── config/                  # YAML 配置文件
│   │   └── vehicle.yaml         # 车辆参数（A 型车默认值）
│   ├── vehicle/                 # 车辆系统（迭代一 MVP 已实现）
│   │   ├── models.py            # I/O 数据类型（模块间契约）
│   │   ├── dynamics.py          # 动力学解算（VehicleSystem）
│   │   ├── traction.py          # 牵引特性曲线
│   │   ├── resistance.py        # Davis/坡度/弯道/隧道阻力
│   │   └── config.py            # YAML 参数加载
│   ├── track/                   # 轨道系统（迭代二待实现）
│   ├── power/                   # 供电系统（迭代二待实现）
│   ├── signaling/               # 信号系统（迭代二待实现）
│   └── orchestrator.py          # 仿真编排器（迭代二待实现）
└── tests/
    └── test_vehicle.py          # 车辆系统单元测试（22 项，覆盖率 99%）
```

## 架构规则

### 模块间通信
- 所有子系统通过 `models.py` 中的 dataclass 交互（`ControlCommands`、`TrackPointParams`、`StepResult` 等）
- **禁止跨模块直接 import 内部实现**，只能通过 `__init__.py` 对外导出

### 车辆系统核心假设
- 积分采用显式（半隐式）欧拉法：先由合力更新速度，再用新速度更新位置
- 制动力与速度无关：`F_brake = max_brake_force × brake_level`
- 工况由控车指令派生：制动 > 牵引 > 惰行
- 对外速度均为 km/h，位置为 m，力为 N，时间步长 dt 为秒

### 单位约定
| 量 | 单位 |
|----|------|
| 速度 | km/h（对外接口一律 km/h，内部动力学换算为 m/s） |
| 位置 | m（公里标） |
| 力 | N |
| 时间步长 | s |
| 加速度 | m/s² |
| 电压 | V |
| 功率 | kW |

### 测试规范
- 测试文件命名：`test_*.py`
- 使用 `pytest` + `pytest-cov`
- 覆盖率目标 ≥ 80%（NFR-03）
- 测试应覆盖正常路径、边界条件（限速、停车等）和错误输入
