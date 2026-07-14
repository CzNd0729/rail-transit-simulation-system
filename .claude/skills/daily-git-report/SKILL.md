---
name: daily-git-report
description: Use when the user explicitly invokes /daily-git-report or asks to generate a personal daily report from git commits. Summarizes the user's own commits by date, organized by work themes, output as Markdown. Not auto-triggered — only runs on explicit user request.
---

# Daily Git Report

## 概述

生成个人日报 Markdown 文件：从当前 git 仓库中筛选出属于用户的提交记录，按**日期**分类，以**天为单位总结当天的工作内容**，输出到 `.daily-report/` 目录。

**核心原则：** 不是逐条罗列提交明细，而是以天为单位，概括当天做了什么。

## 使用方式

用户主动调用：

```
/daily-git-report [日期范围] [作者]
```

- 日期范围：`today`（默认）、`yesterday`、`2026-07-14`、`2026-07-10..2026-07-14`
- 作者：默认自动检测当前 git 配置的用户名

## 执行步骤

### Step 1: 确定查询参数

```bash
# 获取 git 用户
GIT_USER=$(git config user.name)
```

确定日期范围，默认为今天。

### Step 2: 获取提交列表（仅 dev 分支）

只查询 `dev` 分支上的提交，不包含功能分支：

```bash
git log dev --author="$GIT_USER" --since="<start>" --until="<end>" \
  --format="%H||%ai||%s" --reverse
```

输出格式：`commit_hash||2026-07-14 10:30:00 +0800||提交信息`

### Step 3: 按日期分组

将提交按日期（`%Y-%m-%d`）分组。每天一个章节。

### Step 4: 提炼每日工作主题

阅读每天的提交信息，从中提炼出当天的工作主题。**不是逐条列出提交，而是概括当天做了什么。**

例如，如果当天的提交是：
- `feat(sim): 支持 evaluation_time 运行时调整`
- `feat(scenario): 移除手动保存，支持自动保存重命名`

应该提炼为：

```
### 仿真引擎
- 实现了 evaluation_time 运行时调整能力
- 完成了自动保存方案的重命名功能
```

### Step 5: 生成 Markdown 日报

输出到 `.daily-report/YYYY-MM-DD.md`。**无论查询多少天，最终只生成一份报告文件。**

**单日报表格式：**

```markdown
# 个人日报 - 2026-07-14

共 3 条提交

## 当日工作

### 仿真引擎参数增强
- 完成了 evaluation_time 运行时调整的支持
- 实现了自动保存方案的重命名功能

### API 方案保存
- 新增 6 个指标字段和评估窗口截取功能
```

**多日报告格式（一份文件，按天划分）：**

```markdown
# 个人日报 - 2026-07-13 ~ 2026-07-14

---

## 2026-07-14

共 3 条提交

### 当日工作
...

---

## 2026-07-13

共 2 条提交

### 当日工作
...
```

### Step 6: 输出结果

告知用户文件生成路径。如果当天无提交，如实报告。

## 日报内容要求

- **标题：** `# 个人日报 - YYYY-MM-DD`
- **提交数量统计：** 共 N 条提交
- **当日工作：** 按主题/模块分组，用二级标题 `### 模块名`，下面是要点列表
- 每个要点是**概括性描述**，不是复述提交信息
- 不要逐条列出提交明细
- 不要包含 diff 内容
- 不要包含文件路径

## 无提交时的处理

```
# 个人日报 - 2026-07-14

当日无提交记录。
```

## 输出目录约定

- 输出目录：`.daily-report/`（项目根目录下）
- 文件名：`YYYY-MM-DD.md`（单日）或 `YYYY-MM-DD~YYYY-MM-DD.md`（多日范围，一份文件）
- 如果目录不存在，自动创建
- 如果文件已存在，覆盖
- `.daily-report/` 应加入 `.gitignore`

## 多个日期范围

如果查询跨多日，**最终只生成一份文件**，每个日期独立一个章节，按日期从早到晚排列：

```markdown
# 个人日报 - 2026-07-13 ~ 2026-07-14

---

## 2026-07-14

共 3 条提交

### 当日工作

...

---

## 2026-07-13

共 2 条提交

### 当日工作

...
```

## 常见问题

**找不到提交：**
- 确认 git 用户配置：`git config user.name`
- 确认 `dev` 分支是否存在：`git branch -a | grep dev`
- 确认日期范围内是否有提交：`git log dev --author="..." --oneline`

**跨分支：**
- 只查 `dev` 分支上的提交。功能分支上的提交不计入日报