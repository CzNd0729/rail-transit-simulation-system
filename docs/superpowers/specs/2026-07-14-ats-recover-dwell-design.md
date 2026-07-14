# ATS recover 赶点站停设计

> **日期：** 2026-07-14  
> **状态：** 已确认  
> **决策：** 采用策略 A（`dwell_adjust_mode: recover`）

---

## 一、问题

当前 `extend` 模式：`adjusted = nominal + max(0, delay)`，晚点越多站停越长，并被 `max_dwell_time=300` 封顶。  
continuous 多车 + 150s 发车间隔下形成正反馈：前车长停 → 后车贴近 → SIG-07 区间制动。

## 二、目标

1. 切断晚点–加站停雪崩  
2. continuous 默认启用赶点策略  
3. 保留 `extend` 仅作兼容/对照（默认不用）  
4. 最小改动：ATS + 配置 + 测试；本轮不改时刻表时分、不做派车拥堵闸门

## 三、规则（`recover`）

```
delay = actual_arrival - planned_arrival

晚点 (delay > 0):
  adjusted = max(min_dwell, nominal_dwell - delay)

准点/早点 (delay ≤ 0):
  若存在 planned_departure:
    adjusted = max(nominal_dwell, planned_departure - actual_arrival)
  否则:
    adjusted = nominal_dwell - delay   # = nominal + 早点量

最后:
  adjusted = clamp(adjusted, min_dwell, max_dwell)
```

| 场景 | 行为 |
|------|------|
| 晚点 30s，nominal 30 | → `min_dwell`（尽量赶点） |
| 准点 | → `nominal` |
| 早点 20s，计划发车 = 到 + 30 | → 等到计划发车（约 50s 站停） |

## 四、配置

| 项 | 变更 |
|----|------|
| `signal.yaml` `ats.dwell_adjust_mode` | `extend` → **`recover`** |
| `AtsConfig.dwell_adjust_mode` 默认 | **`recover`** |
| `extend` / 其他未知 mode | `extend` 保留旧公式；未知 mode 视为不调整（=`nominal`） |

## 五、代码落点

| 文件 | 变更 |
|------|------|
| `signaling/models.py` | `Timetable.planned_departure(station_id)` |
| `signaling/ats.py` | 实现 `recover` 分支；模块注释更新 |
| `core/config.py` | 默认 `recover` |
| `config/signal.yaml` | 默认 `recover` |
| `tests/test_ats.py` 等 | 覆盖 recover；原 extend 用例显式 `AtsConfig(dwell_adjust_mode="extend")` |

## 六、非本轮范围

- 时刻表区间时分重标定  
- 发车侧拥堵闸门（MR-04）  
- `max_dwell` 与 headway 强制绑定  
- 前端站停根因大展示（可后续加）

## 七、验收

1. 单测：晚点缩短、早点 hold、clamp、未知站、`extend` 回归  
2. 集成：~2000–3000s continuous，站停不应大面积顶满 300s  
3. 全量 pytest 通过  

## 八、文档冲突（报告组长）

需求 SIG-06 写「延长/缩短」，旧实现却是「晚点加站停」。默认改为 `recover` 后语义为：晚点缩短、早点可延长。请同步需求文档状态列/表述，**勿在未通知组长时擅自改 `docs/需求文档.md` 正文争议处以外的范围**——本功能以本设计为准。
