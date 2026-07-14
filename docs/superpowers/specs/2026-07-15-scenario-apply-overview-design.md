# 方案对比「应用」跳转综合视图 — 设计

> **日期：** 2026-07-15  
> **状态：** 已确认（方案 A）  
> **范围：** 前端方案列表「应用」按钮补齐 Context 同步与视图跳转；后端 `PUT /scenarios/{id}/apply` 不变

## 背景

按钮已调用后端 apply，但前端只派发无人监听的 `scenario-applied`，参数面板不更新，也不离开方案对比页。

## 行为（用户确认）

运行中禁止应用。成功后：

1. 清曲线历史（`RESET_RUN_DATA`）并 `SET_RUN_STATE: stopped`（对齐后端 reset）
2. `getParams` → `parseApiParams` → 写入参数（`UPDATE_PARAMS` / `INIT_PARAMS`）
3. `SET_VIEW: overview`；建议经 `beginSwitch` 与顶栏切视图一致
4. 失败：`alert`，不跳转

## 实现要点

- 主要改：`ScenarioListPanel` / `ScenarioComparePage`（或薄 hook）
- 复用：`applyScenario`、`getParams`、`parseApiParams`
- 可删除仅作占位的 `scenario-applied` 派发，或在成功路径保留并注明废弃
- Mock：若无真实 apply API，保持失败/跳过或将来补桩（本轮以真后端为准）

## 验收

1. 停止态点击应用 → 进入综合视图，参数面板为该方案配置  
2. 运行态点击 → 提示先停/暂停，不跳转  
3. apply 失败 → 提示失败，停留方案页  
