# CLAUDE.md — frontend

This file provides guidance to Claude Code, Cursor, and CodeBuddy when working in the `frontend/` directory.

## 当前分支

日常开发在 `frontend` 分支进行，功能完成后合并回 `dev`。

## 技术栈

- React 19 + TypeScript 6.0
- Vite 8.1（构建工具）
- ECharts 6.1 + echarts-for-react（图表可视化）
- oxlint 1.71（代码静态检查）

## 常用命令

```bash
# 安装依赖
npm install

# 开发模式启动（热更新，默认 :5173）
npm run dev

# TypeScript 类型检查
npx tsc -b

# 生产构建（输出到 dist/）
npm run build

# 代码静态检查
npm run lint

# 预览生产构建
npm run preview
```

## 项目结构

```
src/
├── main.tsx                     # React 入口
├── App.tsx                      # 主应用组件
├── index.css                    # 全局样式（暗色主题）
│
├── types/                       # 类型定义
│   └── simulation.ts            # 仿真相关类型（列车/供电/信号/轨道等）
│
├── utils/                       # 工具函数
│   ├── constants.ts             # 常量（API 地址/视图配置/倍率选项）
│   └── format.ts                # 格式化（时间/速度/距离/电压/工况颜色）
│
├── context/                     # 全局状态管理
│   └── SimulationContext.tsx     # Context + useReducer（AppState）
│
├── hooks/                       # 自定义 Hooks
│   ├── useWebSocket.ts          # WebSocket 连接管理（自动重连）
│   └── useSimulation.ts         # 仿真控制逻辑（启停/视图/参数）
│
├── services/                    # 服务层
│   └── api.ts                   # REST API 请求封装
│
├── layouts/                     # 布局组件
│   ├── MainLayout.tsx           # 整体布局（TopBar + 主视图 + Sidebar + StatusBar）
│   ├── TopBar.tsx               # 顶部栏（视图切换 + 仿真时钟 + 连接状态）
│   └── StatusBar.tsx            # 底部状态栏（仿真时间/FPS/列车数/倍率）
│
├── pages/                       # 视图页面（五个视图模式）
│   ├── OverviewView.tsx         # 综合视图（默认）
│   ├── PowerView.tsx            # 供电视图（迭代二）
│   ├── SignalView.tsx           # 信号视图（迭代二）
│   ├── VehicleView.tsx          # 车辆视图
│   └── TrackView.tsx            # 轨道视图（迭代二）
│
└── components/                  # 可复用组件
    ├── control/                 # 仿真控制（运行/暂停/停止/倍率/单步）
    ├── param/                   # 参数配置面板（车辆/线路/供电/信号/预设）
    ├── export/                  # 数据导出（CSV/截图/报告）
    └── views/                   # 各视图的子组件（ECharts 图表 + 可视化）
        ├── overview/            # 线路纵断面/列车动画/速度曲线/状态卡片
        ├── power/               # 电压分布/变电所面板（迭代二）
        ├── signal/              # MA图/速度包络/运行图（迭代二）
        ├── vehicle/             # 速度-时间/加速度/工况/阻力/能耗
        └── track/               # 线路剖面/区段占用/道岔状态（迭代二）
```

## 编码规范

### 文件命名

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 组件文件 | PascalCase | `ControlPanel.tsx` |
| Hook 文件 | camelCase，`use` 前缀 | `useWebSocket.ts` |
| 工具/服务 | camelCase | `format.ts`、`api.ts` |
| 类型文件 | camelCase | `simulation.ts` |
| 样式文件 | kebab-case | `index.css` |

### 组件编写
- 使用**函数组件 + Hooks**，不使用 class 组件
- Props 类型用 `interface` 定义并 `export`
- ECharts 图表使用 `echarts-for-react` 的按需引入模式
- 迭代二/三/四的功能用 `// TODO: 迭代N实现` 注释占位

### 状态管理
- 全局状态通过 `SimulationContext.tsx`（Context + useReducer）管理
- 局部状态使用 useState / useReducer

### 通信规范
- REST API：通过 `src/services/api.ts` 封装
- WebSocket：通过 `useWebSocket` hook 管理（断线自动重连）
- 环境变量通过 `.env` 文件配置，以 `VITE_` 前缀开头（详见 `.env.example`）

## 后端联调

```bash
# 后端启动（参考 backend/README.md）
cd backend
uv sync --extra dev          # 安装后端依赖（uv 替代 pip）
uv run uvicorn sim_engine.app:app --reload --host 0.0.0.0 --port 8000
```

- REST API 默认：`http://localhost:8000`
- WebSocket 默认：`ws://localhost:8000/ws`

## 迭代一实现范围

| 编号 | 功能 | 状态 |
|------|------|------|
| UI-TOP-01 | 顶部栏两个视图按钮（综合、车辆） | 待实现 |
| UI-TOP-02 | 当前视图高亮显示 | 待实现 |
| UI-TOP-03 | 仿真时钟显示 | 待实现 |
| UI-VW-01~04 | 综合视图：线路纵断面 + 列车动画 + 速度-位置曲线 + 状态卡片 | 待实现 |
| UI-VHC-01~03 | 车辆视图：速度-时间 + 加速度 + 工况指示器 | 待实现 |
| UI-CTRL-01~03 | 控制面板：运行/暂停/停止 + 倍率选择 + 单步 | 待实现 |
| UI-PARAM-01/02/05 | 参数编辑：车辆参数 + 线路参数 + 重置 | 待实现 |
| UI-EXPORT-01 | CSV 导出 | 待实现 |
| UI-BAR-01~04 | 状态栏：仿真时间 + FPS + 列车数 + 倍率 | 待实现 |