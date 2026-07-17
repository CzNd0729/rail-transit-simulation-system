# 🚇 NULL 城市轨道交通运行仿真系统

> 城市轨道交通运行仿真系统 — 模拟地铁线路中列车运行、供电潮流、信号控制和轨道基础设施的协同工作过程。

## 项目概述

本系统以 **仿真引擎** 为核心，配合 **前端可视化界面**，实现对列车运行状态、子系统运行参数的实时监控与分析。系统覆盖四大子系统（轨道、车辆、供电、信号），通过仿真编排器协调各子系统在每个仿真步中协同工作，并通过 WebSocket 实时推送状态到前端。

### 目标用户

| 角色 | 核心诉求 |
|------|---------|
| 轨道交通系统工程师 | 验证列车运行控制逻辑、供电方案、信号系统设计 |
| 运营规划人员 | 评估运行图可行性、测试晚点恢复策略、优化发车间隔 |
| 教学 / 科研人员 | 观察各子系统间的耦合关系、进行仿真实验和数据采集 |


## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| **后端框架** | Python 3.10+ / FastAPI | 异步 REST + WebSocket 服务 |
| **仿真引擎** | 纯 Python 实现 | 零外部依赖（仅 PyYAML 用于配置加载） |
| **前端框架** | React 19 + TypeScript | 组件化 UI |
| **图表** | ECharts 6 | 数据可视化（速度曲线、电压分布、运行图等） |
| **构建** | Vite 8 | 快速开发构建 |
| **通信** | WebSocket | 实时状态推送 |
| **测试** | pytest + pytest-cov（后端） / vitest（前端） | 单元测试 + 覆盖率 |
| **配置** | YAML | 所有可调参数通过配置文件注入 |

---

## 项目结构

```
├── backend/
│   ├── sim_engine/                    # 仿真引擎包
│   │   ├── __init__.py
│   │   ├── __main__.py               # CLI 入口 (python -m sim_engine)
│   │   ├── app.py                    # FastAPI 应用入口
│   │   ├── orchestrator.py           # 仿真编排器（主循环）
│   │   ├── core/
│   │   │   ├── clock.py              # 仿真时钟
│   │   │   └── config.py             # 配置加载器
│   │   ├── track/
│   │   │   ├── models.py             # 轨道数据模型（车站/区间/道岔/轨道电路）
│   │   │   ├── path_service.py       # 位置查询服务
│   │   │   ├── config.py             # 轨道配置加载
│   │   │   ├── switch.py             # 道岔控制逻辑
│   │   │   └── occupancy.py          # 区段占用检测
│   │   ├── vehicle/
│   │   │   ├── models.py             # 车辆数据模型
│   │   │   ├── dynamics.py           # 动力学解算（F=ma）
│   │   │   ├── traction.py           # 牵引特性曲线
│   │   │   ├── resistance.py         # 列车阻力计算（Davis 公式）
│   │   │   └── config.py             # 车辆配置加载
│   │   ├── power/
│   │   │   ├── models.py             # 供电数据模型
│   │   │   ├── static_power.py       # 固定网压（1500V）
│   │   │   ├── load_flow.py          # 欧姆压降计算
│   │   │   ├── substation.py         # 变电所模型
│   │   │   └── regeneration.py       # 再生制动统计
│   │   ├── signaling/
│   │   │   ├── models.py             # 信号数据模型（含时刻表）
│   │   │   ├── three_stage.py        # 三段式运行模式（牵引→惰行→制动）
│   │   │   ├── atp.py                # ATP 安全防护
│   │   │   ├── ato.py                # ATO 自动驾驶（PID 控制）
│   │   │   ├── ats.py                # ATS 运行图调整（赶点/延长）
│   │   │   ├── pid_controller.py     # PID 控制器
│   │   │   ├── train_following.py    # 多车追踪间隔
│   │   │   ├── manual_drive.py       # 手动驾驶（紧急制动）
│   │   │   ├── fleet_scheduler.py    # 持续派车调度器
│   │   │   ├── turnback.py           # 终点站折返（道岔联动+换向）
│   │   │   └── timetable_loader.py   # 时刻表 YAML 加载
│   │   ├── data/
│   │   │   ├── recorder.py           # 数据记录器
│   │   │   ├── snapshot.py           # 状态快照（供 WebSocket 推送）
│   │   │   └── scenarios/            # 方案 JSON 文件存储目录
│   │   ├── services/
│   │   │   └── simulation_manager.py # 仿真生命周期管理
│   │   ├── ws/
│   │   │   └── manager.py            # WebSocket 连接管理器
│   │   ├── api/
│   │   │   ├── config.py             # 配置 API
│   │   │   ├── health.py             # 健康检查
│   │   │   ├── params.py             # 参数管理 API
│   │   │   ├── simulation.py         # 仿真控制 API
│   │   │   └── scenarios.py          # 方案管理 API
│   │   └── config/                   # YAML 配置文件
│   │       ├── track.yaml            # 线路参数（24站，北京地铁4号线）
│   │       ├── vehicle.yaml          # 车辆参数
│   │       ├── simulation.yaml       # 仿真参数
│   │       ├── pid.yaml              # 制动/控车参数
│   │       ├── power.yaml            # 供电网络配置
│   │       ├── signal.yaml           # 信号系统配置
│   │       ├── timetable.yaml        # 时刻表（v2 服务运行图）
│   │       ├── timetable_legacy.yaml # 时刻表（v1 单车）
│   │       └── timetable_offpeak.yaml# 时刻表（非高峰）
│   ├── tests/                        # 后端单元测试（30+ 文件，覆盖核心模块）
│   ├── examples/
│   │   └── run_simulation.py         # 离线运行示例
│   └── requirements.txt              # Python 依赖
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                  # 应用入口
│   │   ├── App.tsx                   # 主组件 + 路由
│   │   ├── layouts/
│   │   │   ├── MainLayout.tsx        # 三栏布局
│   │   │   ├── TopBar.tsx            # 顶部栏（视图切换/时钟/连接状态）
│   │   │   └── StatusBar.tsx         # 底部状态栏（仿真时间/FPS/列车数）
│   │   ├── pages/
│   │   │   ├── OverviewView.tsx      # 综合视图（默认）
│   │   │   ├── PowerView.tsx         # 供电视图
│   │   │   ├── SignalView.tsx        # 信号视图
│   │   │   ├── VehicleView.tsx       # 车辆视图
│   │   │   ├── TrackView.tsx         # 轨道视图
│   │   │   └── ScenarioComparePage.tsx # 方案对比页面
│   │   ├── components/
│   │   │   ├── common/               # 通用组件（ECharts/ErrorBoundary等）
│   │   │   ├── control/              # 仿真控制（运行/暂停/停止/倍率/紧急制动）
│   │   │   ├── param/                # 参数编辑（车辆/线路/供电/信号/预设/评估）
│   │   │   ├── export/               # 数据导出（CSV/运行摘要）
│   │   │   ├── scenario/             # 方案对比（列表/表格/柱状图/参数）
│   │   │   └── views/                # 各视图子组件
│   │   │       ├── overview/         # 综合视图组件
│   │   │       ├── power/            # 供电视图组件
│   │   │       ├── signal/           # 信号视图组件
│   │   │       ├── track/            # 轨道视图组件
│   │   │       └── vehicle/          # 车辆视图组件
│   │   ├── context/
│   │   │   └── SimulationContext.tsx  # 全局状态管理
│   │   ├── hooks/                    # 自定义 Hooks（WebSocket/仿真/布局等）
│   │   ├── services/
│   │   │   └── api.ts                # REST API 请求封装
│   │   ├── types/
│   │   │   └── simulation.ts         # TypeScript 类型定义
│   │   ├── utils/                    # 工具函数（格式化/图表配置/数据适配等）
│   │   ├── data/                     # Mock 数据（线路布局/车辆参数）
│   │   └── mock/                     # Mock 仿真引擎
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── docs/                             # 需求文档与设计文档
│   ├── 需求文档.md                    # 完整需求文档（v1.3）
│   ├── 迭代一_MVP需求文档.md           # 迭代一 MVP 需求
│   ├── 迭代二_单列车增强需求文档.md      # 迭代二 增强需求
│   ├── API接口文档.md                 # REST API 与 WebSocket 协议
│   ├── 详细设计文档.md                 # 详细设计文档
│   └── 调研报告.md                    # 技术调研报告
│
├── CLAUDE.md                         # 项目开发指南（AI 辅助开发用）
└── README.md                         # 本文件
```

---

## 快速开始

### 环境要求

| 依赖 | 版本要求 |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm / pnpm | 任意 |

### 后端启动

```bash
# 1. 进入后端目录
cd backend

# 2. 创建虚拟环境（推荐）
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动后端服务（默认监听 127.0.0.1:8000）
python -m sim_engine

# 可选：指定地址和端口
python -m sim_engine --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器（默认 http://localhost:5173）
npm run dev
```

### 访问系统

1. 确保后端已启动（终端显示 `Uvicorn running on http://127.0.0.1:8000`）
2. 确保前端已启动
3. 浏览器打开 `http://localhost:5173`
4. 点击 **运行** 按钮开始仿真

### 离线运行（无前端）

```bash
cd backend
python -m sim_engine.examples.run_simulation
```

---

## 功能特性

### 视图模式

| 视图 | 功能 | 状态 |
|------|------|:----:|
| **综合视图** (默认) | 线路纵断面图、列车位置实时动画、速度-位置曲线、关键状态速览卡片、子系统状态指示器 | ✅ |
| **供电视图** | 接触网电压分布图（含变电所位置标注）、变电所状态面板（电流/功率） | ✅ |
| **信号视图** | 移动授权（MA）示意图、速度包络线、运行图（时间-距离）、信号状态栏 | ✅ |
| **车辆视图** | 速度-时间曲线、加速度-时间曲线、工况指示器、**阻力分解图**、**能耗累计图** | ✅ |
| **轨道视图** | 线路剖面图（坡度-距离）、区段占用状态、道岔状态图 | ✅ |
| **方案对比** | 方案列表（勾选/加载/删除）、**多方案指标对比表格**（5维度）、**柱状图对比** | ✅ |

### 仿真控制

| 功能 | 说明 | 状态 |
|------|------|:----:|
| 运行 / 暂停 / 继续 / 停止 | 完整的仿真生命周期控制 | ✅ |
| 速度倍率 | 1× / 2× / 5× / 10× 可选 | ✅ |
| 单步执行 | 每次推进一个仿真步长 | ✅ |
| 紧急制动 | 手动触发/解除紧急制动（停稳后可解除） | ✅ |
| 参数编辑 | 车辆参数、轨道参数、供电参数、信号参数、评估参数（仿真总时长/评估窗口） | ✅ |
| CSV 导出 | 导出仿真运行数据 | ✅ |

### 后端子系统

| 子系统 | 功能 | 状态 |
|--------|------|:----:|
| **轨道系统** | 一维线性路径、分段坡度/曲率/限速、车站位置、站台范围判断、**道岔建模**（定位/反位/转换中）、**轨道电路区段占用检测** | ✅ |
| **车辆系统** | 牛顿第二定律动力学解算（F=ma）、分段线性牵引特性曲线、Davis 基本阻力、坡度/弯道/隧道附加阻力、限速约束、站台对标停车（±1m）、**能耗累计**（牵引能耗+再生制动） | ✅ |
| **供电系统** | 固定网压（1500V）、**简单欧姆压降计算**、**变电所模型**、**再生制动统计** | ✅ |
| **信号系统** | **三段式运行模式**（牵引→惰行→制动）、**ATP 安全包络**（超速防护+固定安全距离MA）、**ATO 自动驾驶**（PID制动微调）、**ATS 运行图调整**（recover赶点/extend兼容）、**多车追踪间隔**、**时刻表管理**（YAML加载 v1/v2）、**持续派车调度**、**终点站折返**（道岔联动+换向） | ✅ |
| **方案管理** | 方案保存/列表/详情/删除/加载/重命名（JSON 文件存储）、自动保存 | ✅ |

### 多车仿真

| 功能 | 说明 | 状态 |
|------|------|:----:|
| 多列车并行仿真 | 同时运行多列车，独立动力学解算 | ✅ |
| 固定安全距离追踪 | 后车与前车距离 ≤ 安全距离时触发保护 | ✅ |
| 持续派车调度 | 按时刻表 headway 持续发车，始发站容量闸门控制 | ✅ |
| 折返运行 | 终点站道岔联动 + 换向，支持多交路 | ✅ |

---

## 配置说明

所有可调参数通过 YAML 配置文件注入，无需修改代码即可调参（`backend/sim_engine/config/`）：

| 配置文件 | 内容 |
|----------|------|
| `track.yaml` | 线路参数（车站、区间、坡度、曲率、限速、道岔、轨道电路） |
| `vehicle.yaml` | 车辆参数（质量、牵引特性、Davis 阻力系数、再生制动效率） |
| `simulation.yaml` | 仿真参数（步长、列车数、供电模式、信号模式） |
| `pid.yaml` | 制动/控车参数（舒适减速度、冲击率上限、蠕行参数） |
| `power.yaml` | 供电网络配置（变电所位置/容量、接触网/钢轨电阻） |
| `signal.yaml` | 信号系统配置（ATP 安全距离、ATO 目标速度比、ATS 模式） |
| `timetable.yaml` | 时刻表（v2 服务运行图，支持多交路/多折返） |

---

## 测试

### 后端测试

```bash
cd backend

# 运行全部测试
pytest

# 带覆盖率报告
pytest --cov=sim_engine --cov-report=html

# 运行特定测试
pytest tests/test_vehicle.py -v
pytest tests/test_signaling.py -v
```

后端测试覆盖 30+ 测试文件，涵盖轨道、车辆、供电、信号、编排器、API、WebSocket 等核心模块。

### 前端测试

```bash
cd frontend
npm test            # vitest run
npm run test:watch  # 监听模式
```

---

## API 与 WebSocket

### REST API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/config` | 获取全部仿真配置 |
| PUT | `/api/v1/config` | 更新仿真配置 |
| GET/PUT | `/api/v1/params` | 获取/更新运行时参数 |
| GET | `/api/v1/simulation/status` | 获取仿真状态 |
| POST | `/api/v1/simulation/start` | 启动仿真 |
| POST | `/api/v1/simulation/pause` | 暂停仿真 |
| POST | `/api/v1/simulation/resume` | 恢复仿真 |
| POST | `/api/v1/simulation/stop` | 停止仿真 |
| POST | `/api/v1/simulation/reset` | 重置仿真 |
| GET | `/api/v1/simulation/export/csv` | 导出 CSV |
| GET/POST/DELETE/PATCH | `/api/v1/scenarios` | 方案 CRUD |
| PUT | `/api/v1/scenarios/{id}/apply` | 应用方案 |

### WebSocket 实时通信

端点：`ws://localhost:8000/ws`

**前端发送消息类型：**
- `sim_control` — 仿真控制（start/pause/resume/stop/reset/step）
- `param_update` — 参数更新
- `manual_control` — 手动控制（紧急制动）

**后端推送消息类型：**
- `simulation_snapshot` — 仿真状态快照（每步推送）
- `simulation_status` — 状态变更通知
- `heartbeat` — 心跳（每 15 秒）

---

## 开发路线图

| 迭代 | 状态 | 范围 |
|:----|:----:|:----|
| **迭代一：MVP 最小可行系统** | ✅ 已完成 | 单列车三段式运行、基础轨道/车辆/供电/信号、综合视图+车辆视图、基础控制面板 |
| **迭代二：单列车增强 + 扩展视图** | 🔄 大部分已完成 | 道岔/占用检测、欧姆压降/变电所/再生制动、能耗累计、ATP/ATO/ATS、多车追踪、供电/信号/轨道/车辆视图增强、方案对比 ✅ |
| **迭代三：多车 + 信号闭环 + 手动驾驶 + 车门联控** | 📋 部分已提前实现 | 多车/折返/派车 ✅、手动驾驶(紧急制动) ✅、时刻表管理 ✅；车门/PSD/EPB/发车联控/手动驾驶面板 ❌ |
| **迭代四：精细化 + 高级功能** | 📋 远期规划 | 联锁逻辑、PDF 报告、参数方案管理、通信协议对接 |

---

## 贡献指南

### 分支策略

```
main              ← 生产分支（只合并不直接开发）
  └── dev         ← 开发集成分支（日常开发基准）
       └── feat/* ← 功能分支
```

- 新功能从 `dev` 迁出 `feat/<描述>` 分支
- 合并回 `dev` 使用 `rebase + --ff-only`，保持提交历史线性
- 禁止产生 merge commit

### 提交规范

```
<type>(<scope>): <中文描述（≤50字）>
```

类型：`feat` / `fix` / `refactor` / `docs` / `test` / `chore` / `perf` / `build` / `ci` / `style` / `revert`

---

## 许可证

本项目仅供学习和研究使用。