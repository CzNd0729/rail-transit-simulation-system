# 站停同站重入修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除上行停稳后同站反复进 DWELL 的死循环，并配套修正时刻表/recover 早点 hold。

**Architecture:** 在 `ThreeStageController.compute_commands` 中，若 `_dwell_station_id == target.id`，用 ε 推进 `next_station_ahead` 到下一站；ATS `recover` 早点分支加 `early_hold_margin` 上限；timetable 上行始发 departure 对齐下行。

**Tech Stack:** Python 3.10+, pytest, YAML

## Global Constraints

- 可调参数经 YAML/`AtsConfig` 注入（NFR-07）
- 从 `dev` 迁出 `feat/dwell-reentry-fix`；合并 rebase + `--ff-only`
- 提交用 caveman-commit；≤50 字符中文 subject
- 不改 `docs/需求文档.md` 争议正文

---

### Task 1: 失败单测 — 上行同站不重入

**Files:**
- Modify: `backend/tests/test_signaling.py`

- [x] **Step 1:** 增加三站上行线路 helper 与测试：在 ST02 站心略大侧、已设 `_dwell_station_id=ST02`、phase=TRACTION、speed=0，调用 `compute_commands`，断言 phase 非 DWELL 且目标推进到下一站（或不进入同站站停）。
- [x] **Step 2:** 跑该测试确认失败。

---

### Task 2: P0 实现 — 站停后推进目标

**Files:**
- Modify: `backend/sim_engine/signaling/three_stage.py`

- [x] **Step 1:** 在取得 `target = next_station_ahead(...)` 后（制动锁定前），若 `target.id == st._dwell_station_id`，按方向以 ε 再查下一站。
- [x] **Step 2:** 跑 Task 1 测试通过；跑 `test_signaling.py` 全量。

---

### Task 3: P1 — 时刻表 + recover early hold

**Files:**
- Modify: `backend/sim_engine/config/timetable.yaml`
- Modify: `backend/sim_engine/core/config.py`
- Modify: `backend/sim_engine/config/signal.yaml`（若有 ats 节）
- Modify: `backend/sim_engine/signaling/ats.py`
- Modify: `backend/tests/test_ats.py`

- [x] **Step 1:** ST24 `planned_departure: 150` → `35`。
- [x] **Step 2:** `AtsConfig.early_hold_margin` 默认 30；recover 早点分支封顶 `nominal + margin`。
- [x] **Step 3:** 单测 cover early hold 封顶；跑 `test_ats.py` + 相关集成。

---

### Task 4: 验证与收尾

- [x] **Step 1:** `pytest` 信号/ATS/相关集成。
- [ ] **Step 2:** 调用 finishing-a-development-branch（测试通过后呈现合并选项）。
