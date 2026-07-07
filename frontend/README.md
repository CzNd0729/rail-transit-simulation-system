# 城市轨道交通运行仿真系统 — 前端

> 基于 React 19 + TypeScript + Vite + ECharts 的仿真可视化前端

---

## 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [环境变量配置](#环境变量配置)
- [常用命令](#常用命令)
- [项目结构](#项目结构)
- [开发规范](#开发规范)
- [后端联调说明](#后端联调说明)
- [构建与部署](#构建与部署)
- [FAQ](#faq)

---

## 环境要求

| 工具 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| Node.js | 18+ | 20 LTS / 22 LTS | 推荐使用 [nvm](https://github.com/nvm-sh/nvm) 管理版本 |
| npm | 9+ | 10+ | 随 Node.js 安装 |
| Git | 2.30+ | 最新 | 版本控制 |

> **IDE 推荐**：VS Code，安装扩展 `ESLint`、`Prettier`、`TypeScript Vue Plugin (Volar)` 等（TypeScript 支持已内置）。

---

## 快速开始

### 1. 克隆仓库并切换到 frontend 分支

```bash
git clone <仓库地址>
cd rail-transit-simulation-system
git checkout frontend
```

### 2. 进入前端目录并安装依赖

```bash
cd frontend
npm install
```

### 3. 配置环境变量

复制环境变量模板文件，按需修改：

```bash
cp .env.example .env
```

`.env` 文件内容（默认值即可直接开发）：

```env
# 后端 REST API 地址
VITE_API_BASE_URL=http://localhost:8000

# 后端 WebSocket 地址
VITE_WS_BASE_URL=ws://localhost:8000/ws
```

> **注意**：`.env` 文件已被 `.gitignore` 忽略（通过 `*.local` 规则），不会被提交到仓库。如需新增环境变量，请同步更新 `.env.example`。

### 4. 启动开发服务器

```bash
npm run dev
```

启动后访问终端提示的地址（默认 `http://localhost:5173`）。

> 前端页面可独立打开浏览 UI 框架。连接后端仿真引擎后，WebSocket 会自动接收实时仿真数据。

---

## 环境变量配置

所有自定义环境变量必须以 `VITE_` 开头才能在客户端代码中访问。

| 变量名 | 默认值 | 说明 |
|--------|-------|------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 后端 REST API 基础地址 |
| `VITE_WS_BASE_URL` | `ws://localhost:8000/ws` | 后端 WebSocket 推送地址 |

### 多环境配置

Vite 支持按模式加载不同的 `.env` 文件：

```
.env                # 所有环境共用
.env.local          # 本地覆盖（不提交到 Git）
.env.development    # npm run dev 时加载
.env.production     # npm run build 时加载
```

**示例**：如果后端部署在其他地址，创建 `.env.development.local`：

```env
VITE_API_BASE_URL=http://192.168.1.100:8000
VITE_WS_BASE_URL=ws://192.168.1.100:8000/ws
```

---

## 常用命令

```bash
# 开发模式（热更新）
npm run dev

# TypeScript 类型检查（不构建）
npx tsc -b

# 生产构建（输出到 dist/）
npm run build

# 预览生产构建结果
npm run preview

# 代码静态检查
npm run lint
```

---

## 项目结构

```
frontend/
├── .env.example                    # 环境变量模板（提交到 Git）
├── .env                            # 本地环境变量（不提交）
├── package.json                    # 依赖与脚本
├── vite.config.ts                  # Vite 构建配置
├── tsconfig.json                   # TypeScript 配置
└── src/
    ├── main.tsx                    # React 入口
    ├── App.tsx                     # 主应用组件
    ├── index.css                   # 全局样式（暗色主题）
    │
    ├── types/                      # 类型定义
    │   └── simulation.ts           #   仿真相关类型（列车/供电/信号/轨道等）
    │
    ├── utils/                      # 工具函数
    │   ├── constants.ts            #   常量（API 地址/视图配置/倍率选项）
    │   └── format.ts               #   格式化（时间/速度/距离/电压/工况颜色）
    │
    ├── context/                    # 全局状态管理
    │   └── SimulationContext.tsx    #   Context + useReducer（AppState）
    │
    ├── hooks/                      # 自定义 Hooks
    │   ├── useWebSocket.ts         #   WebSocket 连接管理（自动重连）
    │   └── useSimulation.ts        #   仿真控制逻辑（启停/视图/参数）
    │
    ├── services/                   # 服务层
    │   └── api.ts                  #   REST API 请求封装
    │
    ├── layouts/                    # 布局组件
    │   ├── MainLayout.tsx          #   整体布局（TopBar + 主视图 + Sidebar + StatusBar）
    │   ├── TopBar.tsx              #   顶部栏（视图切换 + 时钟 + 连接状态）
    │   └── StatusBar.tsx           #   底部状态栏（仿真时间/FPS/列车数/倍率）
    │
    ├── pages/                      # 视图页面（对应五个视图模式）
    │   ├── OverviewView.tsx        #   综合视图（默认）
    │   ├── PowerView.tsx           #   供电视图
    │   ├── SignalView.tsx          #   信号视图
    │   ├── VehicleView.tsx         #   车辆视图
    │   └── TrackView.tsx           #   轨道视图
    │
    └── components/                 # 可复用组件
        ├── control/                #   仿真控制（运行/暂停/停止/倍率/单步）
        ├── param/                  #   参数配置面板（车辆/线路/供电/信号/预设）
        ├── export/                 #   数据导出（CSV/截图/报告）
        └── views/                  #   各视图的子组件（ECharts 图表 + 可视化）
            ├── overview/           #     线路纵断面/列车动画/速度曲线/状态卡片
            ├── power/              #     电压分布/变电所面板
            ├── signal/             #     MA图/速度包络/运行图
            ├── vehicle/            #     速度-时间/加速度/工况/阻力/能耗
            └── track/              #     线路剖面/区段占用/道岔状态
```

---

## 开发规范

### 分支策略

```
main                ← 生产分支
  └── dev           ← 开发集成分支
       └── frontend ← 前端开发分支（当前分支）
```

- 日常开发在 `frontend` 分支进行
- 功能完成后由负责人合并到 `dev`
- 里程碑发布时 `dev` 合并到 `main`

### 文件命名

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 组件文件 | PascalCase | `ControlPanel.tsx` |
| Hook 文件 | camelCase，`use` 前缀 | `useWebSocket.ts` |
| 工具/服务 | camelCase | `format.ts`、`api.ts` |
| 类型文件 | camelCase | `simulation.ts` |
| 样式文件 | kebab-case | `index.css` |

### 组件编写

- 使用函数组件 + Hooks，不使用 class 组件
- Props 类型用 `interface` 定义并 `export`
- ECharts 图表组件使用 `echarts-for-react` 的按需引入模式
- 迭代二/三/四的功能用 `// TODO: 迭代N实现` 注释占位

### 代码提交

```bash
git add .
git commit -m "feat(views): 实现综合视图线路纵断面图"
git push origin frontend
```

提交信息格式：`<type>(<scope>): <描述>`

| type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 Bug |
| refactor | 重构（不影响功能） |
| style | 样式/格式调整 |
| docs | 文档更新 |
| chore | 构建/工具链变更 |

---

## 后端联调说明

### 启动后端

前端依赖后端仿真引擎提供数据。后端启动方式参见 `backend/` 目录文档。简要流程：

```bash
cd backend
pip install -r requirements.txt
uvicorn sim_engine.app:app --reload --host 0.0.0.0 --port 8000
```

### 通信协议

| 方式 | 用途 | 端口 |
|------|------|------|
| REST API | 配置管理、参数编辑、数据导出 | 8000 |
| WebSocket | 仿真引擎实时推送状态快照 | 8000（同一个端口，路径 `/ws`） |

### 仅前端开发（后端未就绪时）

前端可独立运行，页面和 UI 框架正常显示。WebSocket 连接失败时会显示红色状态指示灯并自动重连，不影响开发调试。

如需模拟数据，可临时修改 `src/hooks/useWebSocket.ts` 或创建 mock 数据文件。

---

## 构建与部署

```bash
# 生产构建
npm run build

# 产物在 dist/ 目录，可部署到任意静态服务器
# 开发阶段预览
npm run preview
```

### 部署到 Nginx（生产环境）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /var/www/frontend/dist;
    index index.html;

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 反向代理后端 API
    location /api/ {
        proxy_pass http://backend:8000;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## FAQ

### Q: `npm install` 报错 `node_modules` 权限问题？

Windows 下以管理员身份运行终端，或检查是否有杀毒软件拦截。

### Q: 修改 `.env` 后没生效？

Vite 环境变量在启动时读取，修改后需**重启** `npm run dev`。

### Q: 构建警告 chunk 体积过大？

正常现象。ECharts 库体积较大，后续迭代可通过 Vite 的 `manualChunks` 配置或 `React.lazy()` 做代码分割优化。

### Q: 端口 5173 被占用？

Vite 会自动递增端口（5174、5175...）。也可指定端口：

```bash
npm run dev -- --port 3000
```


