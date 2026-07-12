# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code), Cursor, and CodeBuddy when working with code in this repository.

## 项目概述

城市轨道交通运行仿真系统 — 模拟地铁线路中列车运行、供电潮流、信号控制和轨道基础设施的协同工作过程。当前处于**迭代一（MVP 最小可行系统）**。

- **后端**：Python 3.10+，仿真引擎包 `sim_engine/`
- **前端**：React 19 + TypeScript + Vite + ECharts
- **通信**：REST API + WebSocket

## 文档权威性

`docs/` 目录下的文档拥有最高解释权。所有需求、架构、接口定义以 docs/ 为准。

**重要规则：**
- 如果发现文档中存在明显错误或不同文档之间存在不一致，**必须**提醒开发者向组长报告，不得自行修改或忽略
- 当前正在执行**迭代一**，所有实现应优先满足迭代一需求
- 迭代一范围：车辆动力学 MVP、三段式信号、固定网压供电、基础轨道查询、仿真编排器、综合视图 + 车辆视图、控制面板基础功能
- 非迭代一的功能应标注 `# TODO: 迭代N实现` 占位

## 分支管理策略

```
main              ← 生产分支（只合并不直接开发）
  └── dev         ← 开发集成分支（日常开发基准，从此迁出功能分支）
```

**当开发新功能时：**
1. 从 `dev` 分支迁出新分支，命名规则：`feat/<简短描述>` 或 `fix/<简短描述>`
2. 在功能分支上完成多次连续提交
3. 功能开发完成后，**调用 finishing-a-development-branch skill** 来处理合并
4. 合并回 `dev` 后，**删除**新创建的功能分支（不保留）

## 必须使用的 Skills（技能）

每次开启新对话或执行任务时，必须严格遵循以下技能要求：

### 1. using-superpowers（最高优先级）
- 每次开始对话时，必须先调用 `using-superpowers` skill
- 在做出任何响应或行动之前，先检查是否有技能适用于当前任务
- 如果有适用的技能，必须先调用再执行

### 2. caveman-commit（提交规范）
- 所有 git 提交必须使用 `caveman-commit` skill
- 提交信息格式：`<type>(<scope>): <中文描述>`（≤50 字符）
- 类型：feat / fix / refactor / docs / test / chore / perf / build / ci / style / revert
- 提交后必须主动询问开发者是否需要 push，得到确认后方可 push

### 3. finishing-a-development-branch（分支完成）
- 功能分支开发完成后，调用此 skill 处理合并/PR/清理
- 核心流程：验证测试 → 检测环境 → 呈现选项 → 执行选择 → 清理
- 合并回 `dev` 时默认以 **rebase + --ff-only** 方式变基合并，保持提交历史线性整洁
- 测试未通过时不得进行合并

### 4. 其他技能
- 实现复杂功能前：`brainstorming` → `writing-plans` → `executing-plans`
- 调试时：`systematic-debugging`
- 编写新技能时：`writing-skills`

## 每次新对话的必做事项

开启新对话时，在开始工作前必须：
1. **拉取远程仓库最新内容**：
   ```bash
   git checkout <当前分支>
   git pull origin <当前分支>
   ```
2. **检查当前分支是否是最新**：如果本地落后于远程，必须优先处理合并
3. **确认当前迭代阶段**：检查 `docs/` 确认当前执行的是迭代一

## 测试要求

- 后端核心函数单元测试覆盖率 **≥ 80%**（NFR-03）
- 提交前必须确保测试通过
- 测试命令见各子目录的 CLAUDE.md

## 参数配置规范

- 所有可调参数通过 YAML/JSON 配置文件注入，不得硬编码在代码中（NFR-07）
- 相关配置文件位于 `backend/sim_engine/config/`