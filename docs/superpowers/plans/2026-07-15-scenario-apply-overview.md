# 方案应用跳转综合视图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 点击方案「应用」后重置前端运行数据、同步参数面板、跳转综合视图。

**Architecture:** 保留后端 `PUT .../apply`；前端成功后依次 dispatch `RESET_RUN_DATA`、`SET_RUN_STATE(stopped)`、`getParams`→`INIT_PARAMS`、`beginSwitch`+`SET_VIEW(overview)`。

**Tech Stack:** React 19, TypeScript, Vitest

## Global Constraints

- 从 `dev` 迁出 `feat/scenario-apply-overview`；合并 rebase + ff-only
- 不改后端 apply 语义；运行中仍 409/前端拦截

---

### Task 1: 抽取可测的 apply 后前端动作（可选薄函数）+ 接线

**Files:**
- Create/Modify: `frontend/src/utils/applyScenarioClient.ts`（编排步骤说明性纯数据辅助可选）
- Modify: `frontend/src/components/scenario/ScenarioListPanel.tsx`
- Modify: `frontend/src/pages/ScenarioComparePage.tsx`（若回调签名变）

- [x] **Step 1:** `handleApply`：`applyScenario` → `RESET_RUN_DATA` → `SET_RUN_STATE stopped` → `getParams`+`parseApiParams` → `INIT_PARAMS` → `beginSwitch` + `SET_VIEW overview`
- [x] **Step 2:** 去掉无监听的 `scenario-applied` 派发，或改为在成功后由 panel 直接完成
- [x] **Step 3:** 失败保持 alert，不切视图
- [x] **Step 4:** 跑相关前端测试 / tsc 无新增错误

---

### Task 2: 验证与收尾

- [ ] 手动核对验收三条（运行中拦截 / 成功跳转 / 失败停留）
- [ ] finishing-a-development-branch（用户选择合并方式）
