# 手动紧急制动按钮 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在控制面板中添加独立紧急制动按钮，用户可在仿真运行中手动触发/解除紧急制动。

**Architecture:** 新增 `ManualDriveController` 在信号指令后叠加手动紧急制动标志，Orchestrator 集成，WebSocket 路由分发，前端按钮触发。

**Tech Stack:** Python 3.10+, dataclass, FastAPI WebSocket, React 19 + TypeScript

## Global Constraints

- 后端所有可调参数通过 YAML 配置文件注入，不得硬编码（NFR-07）
- 紧急制动触发时 `brake_level=0`（让 `dynamics.py` 的 `emergency_brake=True` 分支用 `max_brake_force`）
- 紧急制动为锁定式，用户手动点击解除
- 仅仿真运行（`runState === 'running'`）时按钮可点击

---

### Task 1: ManualDriveController 类 + 单元测试

**Files:**
- Create: `backend/sim_engine/signaling/manual_drive.py`
- Modify: `backend/sim_engine/signaling/__init__.py`
- Create: `backend/tests/test_manual_drive.py`

**Interfaces:**
- Produces: `ManualDriveController` class with `emergency_brake: bool`, `set_emergency_brake(active: bool)`, `get_commands(base_cmd: ControlCommands) -> ControlCommands`

- [ ] **Step 1: 创建 `backend/sim_engine/signaling/manual_drive.py`**

```python
"""手动驾驶控制器（迭代一仅实现紧急制动，迭代三扩展完整手动驾驶）。"""

from __future__ import annotations

from dataclasses import dataclass

from sim_engine.vehicle.models import ControlCommands


@dataclass
class ManualDriveController:
    """在自动信号指令之上叠加手动控制指令。

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

- [ ] **Step 2: 修改 `backend/sim_engine/signaling/__init__.py`**

```python
"""信号系统（MVP）：三段式运行模式（SIG-01 ~ SIG-03）。"""

from .manual_drive import ManualDriveController
from .three_stage import ThreeStageController, TrainSignalState

__all__ = ["ManualDriveController", "ThreeStageController", "TrainSignalState"]
```

- [ ] **Step 3: 创建 `backend/tests/test_manual_drive.py`**

```python
"""ManualDriveController 单元测试。"""

from __future__ import annotations

import pytest

from sim_engine.signaling.manual_drive import ManualDriveController
from sim_engine.vehicle.models import ControlCommands


class TestManualDriveController:
    """紧急制动开关 + get_commands 叠加逻辑。"""

    def test_eb_activated_overrides_commands(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, brake_level=0.0)

        ctrl.set_emergency_brake(True)
        result = ctrl.get_commands(base)

        assert result.emergency_brake is True
        assert result.traction_level == 0.0
        assert result.brake_level == 0.0

    def test_eb_deactivated_passthrough(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, brake_level=0.0)

        ctrl.set_emergency_brake(True)
        ctrl.set_emergency_brake(False)
        result = ctrl.get_commands(base)

        assert result is base  # 返回同一对象，未修改

    def test_eb_initial_state_is_false(self):
        ctrl = ManualDriveController()
        assert ctrl.emergency_brake is False

    def test_eb_preserves_phase(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=1.0, phase="coasting")

        ctrl.set_emergency_brake(True)
        result = ctrl.get_commands(base)

        assert result.phase == "coasting"

    def test_eb_toggle_twice(self):
        ctrl = ManualDriveController()
        base = ControlCommands(traction_level=0.5, brake_level=0.3)

        ctrl.set_emergency_brake(True)
        r1 = ctrl.get_commands(base)
        assert r1.emergency_brake is True

        ctrl.set_emergency_brake(False)
        r2 = ctrl.get_commands(base)
        assert r2 is base
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_manual_drive.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add backend/sim_engine/signaling/manual_drive.py backend/sim_engine/signaling/__init__.py backend/tests/test_manual_drive.py
git commit -m "feat(signaling): 新增 ManualDriveController 紧急制动叠加逻辑"
```

---

### Task 2: Orchestrator 集成 ManualDriveController

**Files:**
- Modify: `backend/sim_engine/orchestrator.py`

**Interfaces:**
- Consumes: `ManualDriveController` from `sim_engine.signaling`
- Produces: `Orchestrator.set_emergency_brake(active: bool)`, `Orchestrator.manual_driver` field

- [ ] **Step 1: 修改 `backend/sim_engine/orchestrator.py`**

在 import 区增加：
```python
from sim_engine.signaling.manual_drive import ManualDriveController
```

在 `Orchestrator` dataclass 字段中增加：
```python
manual_driver: ManualDriveController = field(default_factory=ManualDriveController)
```

新增方法：
```python
def set_emergency_brake(self, active: bool) -> None:
    self.manual_driver.set_emergency_brake(active)
```

修改 `step_once()`，在 `signaling.compute_commands()` 之后、`vehicle.step()` 之前插入一行：
```python
cmd = self.signaling.compute_commands(self.train_state, dt)
cmd = self.manual_driver.get_commands(cmd)  # 手动指令叠加（紧急制动覆盖）
result = self.vehicle.step(self.train_state, cmd, track_params, dt, self.sim_params.pid.max_jerk)
```

修改 `reset()`，在末尾增加：
```python
self.manual_driver = ManualDriveController()
```

完整修改后的 `reset()` 方法：
```python
def reset(self, passenger_load: float = 0.6) -> None:
    self.clock.reset()
    self.recorder.clear()
    self.signaling.reset()
    self.train_state = self.vehicle.create_initial_state(
        position=0.0, passenger_load=passenger_load
    )
    self.run_state = RunState.IDLE
    self.last_snapshot = None
    self.last_step = None
    self.manual_driver = ManualDriveController()
```

- [ ] **Step 2: 运行已有测试确认未破坏**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 3: 提交**

```bash
git add backend/sim_engine/orchestrator.py
git commit -m "feat(orchestrator): 集成 ManualDriveController 紧急制动覆盖"
```

---

### Task 3: WebSocket 路由 + SimulationManager 支持

**Files:**
- Modify: `backend/sim_engine/services/simulation_manager.py`
- Modify: `backend/sim_engine/app.py`

**Interfaces:**
- Consumes: `Orchestrator.set_emergency_brake(active: bool)`
- Produces: WS message type `manual_control` with `emergencyBrake: bool`

- [ ] **Step 1: 修改 `backend/sim_engine/services/simulation_manager.py`**

在 `SimulationManager` 类中新增方法（放在 `set_speed` 方法后面）：

```python
def set_emergency_brake(self, active: bool) -> dict:
    self.orchestrator.set_emergency_brake(active)
    return {"emergencyBrake": active}
```

- [ ] **Step 2: 修改 `backend/sim_engine/app.py`**

在 WebSocket 消息循环的 `elif msg_type == "param_update":` 之后增加：

```python
elif msg_type == "manual_control":
    eb = data.get("emergencyBrake")
    if eb is not None:
        sim_manager.set_emergency_brake(eb)
```

完整修改后的消息循环：
```python
while True:
    data = await websocket.receive_json()
    msg_type = data.get("type", "")
    if msg_type == "sim_control":
        action = data.get("action", "")
        if action == "start":
            sim_manager.start()
        elif action == "pause":
            await sim_manager.pause()
        elif action == "resume":
            sim_manager.resume()
        elif action == "stop":
            await sim_manager.stop()
        elif action == "reset":
            sim_manager.reset()
        elif action == "step":
            sim_manager.step()
    elif msg_type == "param_update":
        sim_manager.update_params(data.get("params", {}))
    elif msg_type == "manual_control":
        eb = data.get("emergencyBrake")
        if eb is not None:
            sim_manager.set_emergency_brake(eb)
```

- [ ] **Step 3: 运行测试确认未破坏**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 4: 提交**

```bash
git add backend/sim_engine/services/simulation_manager.py backend/sim_engine/app.py
git commit -m "feat(ws): 新增 manual_control WebSocket 消息路由"
```

---

### Task 4: 前端紧急制动按钮 + 类型

**Files:**
- Modify: `frontend/src/types/simulation.ts`
- Create: `frontend/src/components/control/EmergencyBrakeButton.tsx`
- Modify: `frontend/src/components/control/ControlPanel.tsx`

**Interfaces:**
- Consumes: `send` function, `runState` from props
- Produces: WS message `{ type: "manual_control", emergencyBrake: boolean }`

- [ ] **Step 1: 修改 `frontend/src/types/simulation.ts`**

在 `ClientMessage` 类型中增加 `manual_control` 消息：

```typescript
export type ClientMessage =
  | { type: 'sim_control'; action: 'start' | 'pause' | 'resume' | 'stop' | 'step' }
  | { type: 'param_update'; params: Partial<SimulationParams> }
  | { type: 'manual_control'; emergencyBrake: boolean };
```

- [ ] **Step 2: 创建 `frontend/src/components/control/EmergencyBrakeButton.tsx`**

```tsx
/**
 * EmergencyBrakeButton — 手动紧急制动按钮
 * 仅仿真运行中可点击，锁定式（点击触发/点击解除）。
 */
import { useState } from 'react';

interface Props {
  send: (data: object) => void;
  runState: string;
}

export default function EmergencyBrakeButton({ send, runState }: Props) {
  const [activated, setActivated] = useState(false);

  const handleClick = () => {
    const next = !activated;
    setActivated(next);
    send({ type: 'manual_control', emergencyBrake: next });
  };

  const isRunning = runState === 'running';

  return (
    <button
      onClick={handleClick}
      disabled={!isRunning}
      style={{
        ...styles.button,
        ...(activated ? styles.active : {}),
        ...(!isRunning ? styles.disabled : {}),
      }}
    >
      {activated ? '🚨 解除紧急制动' : '🚨 紧急制动'}
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  button: {
    width: '100%',
    padding: '12px 0',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#fff',
    backgroundColor: '#dc3545',
    border: '2px solid #b02a37',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  active: {
    backgroundColor: '#b02a37',
    boxShadow: 'inset 0 0 8px rgba(0,0,0,0.3)',
    animation: 'none',
  },
  disabled: {
    backgroundColor: '#6c757d',
    borderColor: '#5c636a',
    cursor: 'not-allowed',
    opacity: 0.65,
  },
};
```

- [ ] **Step 3: 修改 `frontend/src/components/control/ControlPanel.tsx`**

增加 `runState` 引入，在 `SpeedSelector` 与 `StepButton` 之间插入：

```tsx
import RunControlButtons from './RunControlButtons';
import SpeedSelector from './SpeedSelector';
import StepButton from './StepButton';
import EmergencyBrakeButton from './EmergencyBrakeButton';
import { useSimulationState } from '../../context/SimulationContext';

interface Props {
  send: (data: object) => void;
}

export default function ControlPanel({ send }: Props) {
  const { runState } = useSimulationState();

  return (
    <div className="panel">
      <div className="panel-title">🎮 仿真控制</div>
      <div style={styles.content}>
        <RunControlButtons send={send} />
        <SpeedSelector send={send} />
        <EmergencyBrakeButton send={send} runState={runState} />
        <StepButton send={send} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: 检查前端编译**

Run: `cd frontend && npx tsc --noEmit`
Expected: 编译通过，无类型错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/types/simulation.ts frontend/src/components/control/EmergencyBrakeButton.tsx frontend/src/components/control/ControlPanel.tsx
git commit -m "feat(ui): 控制面板新增紧急制动按钮"
```

---

### Task 5: Orchestrator 集成测试

**Files:**
- Create: `backend/tests/test_manual_drive.py`（追加到已有文件末尾）

- [ ] **Step 1: 在 `backend/tests/test_manual_drive.py` 末尾追加集成测试**

```python
# --- 编排器集成测试 ---


class TestOrchestratorEBIntegration:
    """验证手动紧急制动在编排器层面的完整链路。"""

    def test_eb_activates_max_brake_force(self, orchestrator):
        """EB 激活后一步 → 制动力 = max_brake_force。"""
        orch = orchestrator
        orch.start()

        # 先跑几步让列车有速度
        for _ in range(50):
            orch.step_once()
        assert orch.train_state.speed > 1.0

        # 触发紧急制动
        orch.set_emergency_brake(True)
        result = orch.step_once()

        assert result is not None
        assert result["data"]["signaling"]["controlCommands"][0]["emergencyBrake"] is True
        assert result["data"]["trains"][0]["speed"] < orch.train_state.speed

    def test_eb_clears_on_reset(self, orchestrator):
        """reset() 后紧急制动状态清除。"""
        orch = orchestrator
        orch.set_emergency_brake(True)
        assert orch.manual_driver.emergency_brake is True

        orch.reset()
        assert orch.manual_driver.emergency_brake is False
```

- [ ] **Step 2: 创建 conftest fixture**

创建 `backend/tests/conftest.py`（如果已存在则追加）：

```python
"""共享测试 fixtures。"""

from __future__ import annotations

import pytest

from sim_engine.orchestrator import Orchestrator


@pytest.fixture
def orchestrator() -> Orchestrator:
    """返回一个初始化的编排器实例（使用默认配置）。"""
    return Orchestrator.from_config_dir()
```

- [ ] **Step 3: 运行测试确认通过**

Run: `cd backend && python -m pytest tests/test_manual_drive.py -v`
Expected: 7 passed（5 unit + 2 integration）

- [ ] **Step 4: 提交**

```bash
git add backend/tests/test_manual_drive.py backend/tests/conftest.py
git commit -m "test(signaling): 紧急制动编排器集成测试"
```