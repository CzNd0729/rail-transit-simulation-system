# 站停同站重入死循环修复 — 设计

## 问题

上行列车停在站中心略大侧（如 ST23=17700，位姿 17700.1）时：
`next_station_ahead(..., "up")` 因 `chainage < position` 仍返回本站 →
站停结束后 speed≈0 且 |dist|≤tol → 再次 `_start_dwell` → 约每 `min_dwell` 循环，无法离站；后车追踪紧急制动，表现为「卡住」。

## 方案（已批准）

### P0（必做）

站停完成后 `_dwell_station_id` 仍等于当前 `next_station_ahead` 目标时，将目标推进到该站之后的下一站（下行：`chainage+ε`，上行：`chainage-ε` 再查 `next_station_ahead`），避免同站再次进入 DWELL。

不动 `next_station_ahead` 语义；到站判定与「刚停完本站」解耦。

### P1（配套）

1. 上行时刻表 ST24 `planned_departure: 150` → `35`（与下行始发 ST01 对齐），减轻跳过始发站停导致的系统性早点 hold。
2. `recover` 早点 hold：`adjusted = min(max(nominal, planned_dep - arrival), nominal + early_hold_margin)`；`early_hold_margin` 经 `AtsConfig`/YAML 注入（默认 30s）。

### P2（本轮不做）

缓冲 vs Turnback 交路冲突（既有 xfail）。

## 验收

- 单元：上行在站心略大侧完成站停后，不得在 dt 循环内再次进入同站 DWELL；应牵引驶向下站。
- 回归：既有 `test_signaling` / `test_ats` / continuous 相关用例通过。
