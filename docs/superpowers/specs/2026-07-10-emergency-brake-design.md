# 手动紧急制动按钮 — 设计文档

> 迭代一提前实现：在控制面板中添加独立紧急制动按钮，不引入完整手动驾驶模式。

---

## 1. 动机

当前仿真系统仅支持自动三段式信号控车，紧急制动只能由信号控制器在越站饱和制动时自动触发。用户（操作员）在仿真运行中无法手动干预列车施加紧急制动。

本设计在**不引入完整手动驾驶模式**的前提下，为控制面板添加一个独立紧急制动按钮，满足手动紧急制动需求。

---

## 2. 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 实现方式 | 精简 `ManualDriveController` | 与详细设计文档 ADR-09 对齐，为迭代三预留扩展点 |
| 解除方式 | 锁定式（手动点击解除） | 用户明确要求，操作员控制解除时机 |
| 制动优先级 | EB 覆盖所有自动信号 | 紧急制动最高优先级，运行时牵引/制动均归零 |
| 制动级位 | 触发 EB 时 `brake_level=0` | `dynamics.py` 中 `emergency_brake=True` 直接使用 `max_brake_force`，不读取 brake_level |

---

## 3. 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                       前端 ControlPanel                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  [EmergencyBrakeButton]  ← 点击 → send({manual_control, eb}) │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │ WS { type: "manual_control",         │
│                             │       emergencyBrake: true/false }   │
├─────────────────────────────┼───────────────────────────────────────┤
│                     后端 app.py (WebSocket 路由)                    │
│                             │                                       │
│                    sim_manager.set_emergency_brake()                │
│                             │                                       │
│                    orchestrator.set_emergency_brake()               │
│                             │                                       │
├─────────────────────────────┼───────────────────────────────────────┤
│                   Orchestrator.step_once()                          │
│                                                                     │
│  signaling.compute_commands()                                       │
│       ↓                                                             │
│  manual_driver.get_commands(cmd)  ← 叠加 EB 覆盖                   │
│       ↓                                                             │
│  vehicle.step()  ──→ dynamics.py: cmd.emergency_brake?             │
│                          → f_brake = params.max_brake_force         │
└─────────────────────────────────────────────────────────────────────┘
```

### 数据流

```
EB 按钮点击 → WS → app.py → SimulationManager → Orchestrator
  → manual_driver.emergency_brake = True
    → step_once(): manual_driver.get_commands(signaling_cmd)
      → ControlCommands(emergency_brake=True, traction=0, brake=0)
        → VehicleSystem.step() → f_brake = max_brake_force
```

---

## 4. 后端变更

### 4.1 新增文件：`backend/sim_engine/signaling/manual_drive.py`

```python
@dataclass
class ManualDriveController:
    """手动驾驶控制器（迭代一仅实现紧急制动，迭代三扩展完整手动驾驶）。

    职责：在自动信号指令之上叠加手动控制指令。
    紧急制动优先级最高——触发时覆盖所有信号输出。
    """
    emergency_brake: bool = False

    def set_emergency_brake(self, active: bool) -> None:
        """设置/解除紧急制动（锁定式，需手动解除）。"""
        self.emergency_brake = active

    def get_commands(self, base_cmd: ControlCommands) -> ControlCommands:
        """在自动信号指令上叠加手动指令。

        当紧急制动激活时，强制覆盖：
        - emergency_brake = True
        - traction_level = 0（牵引归零）
        - brake_level = 0（让 dynamics.py 的 emergency_brake 分支用 max_brake_force）
        """
        if not self.emergency_brake:
            return base_cmd
        return ControlCommands(
            traction_level=0.0,
            brake_level=0.0,
            emergency_brake=True,
            phase=base_cmd.phase,
        )
```

### 4.2 修改：`backend/sim_engine/orchestrator.py`

- 新增字段 `manual_driver: ManualDriveController = field(default_factory=ManualDriveController)`
- 新增方法 `set_emergency_brake(active: bool) → None`
- `step_once()` 中在 `signaling.compute_commands()` 之后插入：

```python
cmd = self.signaling.compute_commands(self.train_state, dt)
cmd = self.manual_driver.get_commands(cmd)  # ← 手动指令叠加
result = self.vehicle.step(self.train_state, cmd, track_params, dt, ...)
```

- `reset()` 中重置 `manual_driver = ManualDriveController()`

### 4.3 修改：`backend/sim_engine/services/simulation_manager.py`

新增方法：

```python
def set_emergency_brake(self, active: bool) -> dict:
    self.orchestrator.set_emergency_brake(active)
    return {"emergencyBrake": active}
```

### 4.4 修改：`backend/sim_engine/app.py`

WebSocket 消息循环中增加：

```python
elif msg_type == "manual_control":
    eb = data.get("emergencyBrake")
    if eb is not None:
        sim_manager.set_emergency_brake(eb)
```

---

## 5. 前端变更

### 5.1 修改：`frontend/src/types/simulation.ts`

`ClientMessage` 增加：

```typescript
export type ClientMessage =
  | { type: 'sim_control'; action: 'start' | 'pause' | 'resume' | 'stop' | 'step' }
  | { type: 'param_update'; params: Partial<SimulationParams> }
  | { type: 'manual_control'; emergencyBrake: boolean };  // ← 新增
```

### 5.2 新增：`frontend/src/components/control/EmergencyBrakeButton.tsx`

- 红色大按钮，白色文字
- 状态：`inactive`（显示"紧急制动"）→ 点击 → `active`（显示"解除紧急制动"）
- 仅 `runState === 'running'` 时可点击，其余状态 disabled
- 点击时发送 `send({ type: 'manual_control', emergencyBrake: true/false })`
- 通过 `runState` 和内部 `activated` 状态控制显示

### 5.3 修改：`frontend/src/components/control/ControlPanel.tsx`

在 `SpeedSelector` 与 `StepButton` 之间插入 `EmergencyBrakeButton`，传入 `send` 和 `runState`。

---

## 6. 测试

### 后端单元测试（2 个）

| 测试 | 说明 |
|------|------|
| `test_manual_drive_eb_toggle` | 设 true → `get_commands()` 输出 `emergency_brake=True`，牵引/制动归零；设 false → 原样透传 |
| `test_orchestrator_eb_integration` | 编排器集成：EB 激活后一步 → 制动力 = `max_brake_force` |

### 前端测试

不添加（按钮逻辑简单，依赖 WS 通信，属于集成测试范畴）。

---

## 7. 安全与边界

| 场景 | 行为 |
|------|------|
| 仿真未运行（idle/paused） | 按钮 disabled，不可点击 |
| 运行中触发 EB | 立即施加最大制动力，牵引归零 |
| 列车已停稳时触发 EB | 保持制动（最大制动力），不会溜车 |
| 解除 EB | 恢复自动信号控制，由信号系统决定下一步动作 |
| 仿真停止/重置 | 自动清除 EB 状态（`orchestrator.reset()` 中重置 `ManualDriveController`） |
| WebSocket 断开 | 后端保持当前 EB 状态，不会自动解除 |