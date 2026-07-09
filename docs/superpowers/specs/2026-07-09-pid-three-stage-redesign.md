# PID 三段式控车系统重新设计

## 概述

当前三段式控车系统（牵引→惰行→制动）存在制动不准/过冲、PID 参数不合理、阶段切换频繁 reset 导致控制割裂等问题。本设计彻底重写 `three_stage.py` 和 `pid_controller.py`，核心思路：

- **牵引**：开环满牵引，尽可能简单
- **制动**：前馈（运动学公式） + P 微调，精确可靠
- **阶段切换**：不再频繁 reset PID，保持连续性

## 架构

```
ThreeStageController
├── 牵引阶段: 开环满牵引 + 巡航前退坡
│     └── 不涉及 PID
├── 惰行阶段: 开环补偿（滚动+坡度，与原相同）
│     └── 不涉及 PID
├── 制动阶段: 前馈 + P 微调
│     ├── 前馈：运动学公式 a = v²/2d → 制动力
│     └── P 微调：修正风阻/坡度扰动
└── PIDController: 简化，只用 P 项
      └── 只在制动阶段使用
```

## 制动算法（核心）

### 前馈计算

```
输入：train（当前速度/位置/质量）, target（目标站）
输出：brake_level [0, 1]

1. 剩余距离
   remaining = target.chainage - train.position

2. 蠕行判断（近站低速）
   if remaining <= 1.0 and train.speed < 3.0:
       return creep_brake(remaining)

3. 前馈
   v_ms = train.speed / 3.6
   a_required = v_ms² / (2 × remaining)         # 要停稳需要的减速度

   resistance_force = davis + gradient + curve + tunnel
   a_from_resistance = resistance_force / mass

   a_from_brake = max(0, a_required - a_from_resistance)
   brake_ff = (mass × a_from_brake) / max_brake_force

4. P 微调
   v_target_kmh = sqrt(2 × comfort_decel × remaining) × 3.6
   error = (train.speed - v_target_kmh) / v_target_kmh    # 归一化误差
   trim = kp_brake × error

5. 合成
   brake = clamp(brake_ff + trim, 0, 1)
```

### 前馈优势

前馈能瞬间给出正确的制动级位（~0.7），无需 PID 花数秒建压。相比当前纯 PID 方案，响应速度从数秒提升到一步。

### 蠕行模式

```
brake = min(remaining × creep_gain, 0.5)
brake = max(brake, 0.02)
```

## 牵引算法

```
traction = 1.0（满牵引）
速度达到 v_cruise - 2.0 时 → 切惰行
惰行回切牵引 → 同样是 1.0
```

全程开环，无 PID 参与。短站距时跳过惰行直接制动。

## 阶段切换规则

| 切换 | PID 行为 |
|------|---------|
| DWELL → TRACTION | 不 reset（无 PID 可 reset） |
| TRACTION → COASTING | 无操作 |
| COASTING → TRACTION | 无操作 |
| COASTING → BRAKING | 不 reset |
| TRACTION → BRAKING | 不 reset |
| 到站 DWELL | reset 制动 PID（下次发车重新开始） |

## PIDController 简化

```python
class PIDController:
    def __init__(self, kp: float):
        self.kp = kp

    def compute(self, error: float) -> float:
        return self.kp * error

    def reset(self):
        pass
```

去除 I/D/deadband/anti-windup 等复杂逻辑，只用 P 项做微调修正。

## 配置参数

```yaml
simulation:
  pid:
    comfort_decel: 0.8          # 制动曲线减速度（前馈核心参数）
    kp_brake: 0.02              # 制动 P 微调增益
    creep_gain: 0.25            # 蠕行模式增益
    deadband_d: 1.0             # 蠕行触发距离 (m)
    brake_safety_factor: 1.02   # 触发距离安全系数
```

去除字段：kp, ki, kd, integral_max, deadband_v, output_min, output_max。

## 制动触发距离

```
brake_trigger = v² / (2 × comfort_decel) × 1.02
```

安全系数从 1.05 降为 1.02。前馈制动响应快，实际制动距离与理论值高度一致，不需要大的安全余量。

## 测试要点

- 制动前馈数值验证：给定速度/距离/质量，输出可预测
- 制动停车精度：多步模拟后停在站台容差内
- 牵引阶段满牵引行为
- 惰行补偿不变
- 跳站检测不变
- 短站距直接制动
- 蠕行模式

## 文件变更

| 文件 | 变更 |
|------|------|
| `backend/sim_engine/signaling/three_stage.py` | 重写制动和牵引逻辑 |
| `backend/sim_engine/signaling/pid_controller.py` | 简化为 P-only |
| `backend/sim_engine/config/simulation.yaml` | 精简 PID 参数 |
| `backend/sim_engine/core/config.py` | 精简 PidParams |
| `backend/tests/test_signaling.py` | 更新制动相关测试 |
| `backend/tests/test_pid_controller.py` | 更新为 P-only 测试 |