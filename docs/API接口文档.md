# 城市轨道交通运行仿真系统 — API 接口文档

> 版本号:v1.0
> 本文档定义系统前后端之间的所有 API 接口规范，包括 RESTful API 和 WebSocket 实时通信协议。
> 基于《需求文档》和《详细设计文档》编写。

---

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|----------|
| v1.0 | 2026-07-06 | 全体成员 | 初版发布，覆盖全部 API 接口 |
| v1.1 | 2026-07-13 | 陈逸凡 | 新增方案管理 API 接口 |

---

## 目录

1. [通用约定](#1-通用约定)
2. [REST API 总览](#2-rest-api-总览)
3. [配置管理接口](#3-配置管理接口)
4. [仿真控制接口](#4-仿真控制接口)
5. [参数编辑接口](#5-参数编辑接口)
6. [数据导出接口](#6-数据导出接口)
7. [事件查询接口](#7-事件查询接口)
8. [WebSocket 实时通信协议](#8-websocket-实时通信协议)
9. [数据模型定义](#9-数据模型定义)
10. [错误码说明](#10-错误码说明)

---

## 1. 通用约定

### 1.1 基础 URL

| 环境 | 基础 URL |
|------|----------|
| 开发环境 | `http://localhost:8000/api/v1` |
| 生产环境 | `https://sim.example.com/api/v1` |

WebSocket 地址：

| 环境 | WebSocket URL |
|------|---------------|
| 开发环境 | `ws://localhost:8000/ws` |
| 生产环境 | `wss://sim.example.com/ws` |

### 1.2 请求格式

- 所有 REST API 请求体使用 **`application/json`** 格式
- 参数名称使用 **lowerCamelCase**（与前端 JS 风格一致）
- 时间相关字段使用 **浮点数秒数**（simulationTime）或 **ISO 8601**（realTime）

### 1.3 响应格式

**成功响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

**错误响应**：

```json
{
  "code": 40001,
  "message": "参数验证失败",
  "detail": "time_step 必须为正数",
  "requestId": "req_xxxxxxxx"
}
```

### 1.4 分页约定

分页接口统一使用以下参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码（从 1 开始） |
| pageSize | integer | 20 | 每页条数（最大 100） |

分页响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 156,
      "totalPages": 8
    }
  }
}
```

### 1.5 HTTP 状态码

| 状态码 | 说明 | 适用场景 |
|--------|------|----------|
| 200 | 请求成功 | 正常响应 |
| 201 | 创建成功 | POST 创建资源 |
| 400 | 请求参数错误 | 参数校验失败 |
| 404 | 资源不存在 | 查询 ID 不存在 |
| 409 | 资源冲突 | 重复创建、状态冲突 |
| 500 | 服务器内部错误 | 未捕获异常 |

---

## 2. REST API 总览

| 方法 | 路径 | 说明 | 迭代 |
|------|------|------|------|
| GET | /config | 获取当前全部仿真配置 | 一 |
| PUT | /config | 更新仿真配置 | 一 |
| GET | /config/line | 获取线路配置 | 一 |
| PUT | /config/line | 更新线路配置 | 一 |
| GET | /config/vehicle | 获取车辆配置 | 一 |
| PUT | /config/vehicle | 更新车辆配置 | 一 |
| GET | /simulation/status | 获取仿真运行状态 | 一 |
| POST | /simulation/start | 启动仿真 | 一 |
| POST | /simulation/pause | 暂停仿真 | 一 |
| POST | /simulation/resume | 恢复仿真 | 一 |
| POST | /simulation/stop | 停止仿真 | 一 |
| POST | /simulation/reset | 重置仿真 | 一 |
| POST | /simulation/step | 单步执行 | 二 |
| PUT | /simulation/speed | 设置速度倍率 | 二 |
| GET | /simulation/runs | 获取仿真运行记录列表 | 一 |
| GET | /simulation/runs/{runId} | 获取指定运行记录详情 | 一 |
| GET | /simulation/runs/{runId}/results | 获取运行结果汇总 | 一 |
| GET | /simulation/runs/{runId}/events | 获取运行事件记录 | 二 |
| GET | /simulation/export/csv | 导出 CSV 数据 | 一 |
| GET | /simulation/export/snapshot | 导出当前快照截图 | 二 |
| GET | /params | 获取当前运行时参数 | 一 |
| PUT | /params | 更新运行时参数 | 一 |
| GET | /params/presets | 获取参数预设方案列表 | 三 |
| POST | /params/presets | 创建参数预设方案 | 三 |
| GET | /params/presets/{presetId} | 获取预设方案详情 | 三 |
| PUT | /params/presets/{presetId} | 更新预设方案 | 三 |
| PUT | /params/presets/{presetId}/apply | 应用预设方案 | 三 |
| DELETE | /params/presets/{presetId} | 删除预设方案 | 三 |
| GET | /events | 获取仿真事件/告警 | 二 |
| GET | /health | 健康检查 | 一 |
| POST | /control/manual/activate | 切换手动驾驶模式 | 三 |
| POST | /control/manual/deactivate | 切回自动驾驶模式 | 三 |
| PUT | /control/manual/throttle | 设置手动牵引级位 | 三 |
| PUT | /control/manual/brake | 设置手动制动级位 | 三 |
| POST | /control/manual/emergency-brake | 触发手动紧急制动 | 三 |
| GET | /control/manual/status | 获取手动驾驶模式状态 | 三 |
| GET | /drivercab/status | 获取司机台连接状态 | 三 |
| POST | /drivercab/connect | 建立司机台连接（接口预留） | 三 |
| POST | /drivercab/disconnect | 断开司机台连接（接口预留） | 三 |
| GET | /scenarios | 获取所有方案摘要列表 | 三 |
| POST | /scenarios | 保存当前参数+结果为方案 | 三 |
| GET | /scenarios/{scenarioId} | 获取方案完整详情 | 三 |
| DELETE | /scenarios/{scenarioId} | 删除方案 | 三 |
| PUT | /scenarios/{scenarioId}/apply | 加载方案参数到引擎 | 三 |

---

## 3. 配置管理接口

### 3.1 获取当前全部仿真配置

获取当前加载的所有配置（线路、车辆、仿真参数）。

**请求**：

```
GET /config
```

**响应示例**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "line": {
      "name": "1号线",
      "direction": "up",
      "totalLength": 15000,
      "stations": [
        {
          "id": "ST01",
          "name": "A站",
          "chainage": 0,
          "platformHalfLength": 15,
          "defaultDwellTime": 30,
          "isTerminus": true
        },
        {
          "id": "ST02",
          "name": "B站",
          "chainage": 1500,
          "platformHalfLength": 15,
          "defaultDwellTime": 30,
          "isTerminus": false
        }
      ],
      "segments": [
        {
          "id": "SEC01",
          "startChainage": 0,
          "endChainage": 1500,
          "gradient": 5,
          "curvature": 800,
          "speedLimit": 80,
          "isTunnel": false
        }
      ]
    },
    "vehicle": {
      "id": "TYPE_A",
      "name": "A型车",
      "emptyMass": 200000,
      "passengerCapacity": 1500,
      "maxSpeed": 100,
      "maxTractionForce": 400000,
      "maxBrakeForce": 350000,
      "davisA": 0.01,
      "davisB": 0.0001,
      "davisCFrontArea": 10,
      "davisCDragCoeff": 0.5,
      "curveResistCoeff": 600,
      "tunnelResistFactor": 1.2,
      "regenerationEfficiency": 0.3,
      "length": 120,
      "tractionCurve": [
        { "speed": 0, "forcePercent": 1.0 },
        { "speed": 40, "forcePercent": 1.0 },
        { "speed": 80, "forcePercent": 0.5 },
        { "speed": 100, "forcePercent": 0.5 }
      ]
    },
    "simulation": {
      "timeStep": 0.1,
      "totalTime": 600,
      "speedMultiplier": 1,
      "signalMode": "three_stage",
      "targetSpeedRatio": 0.8,
      "stationStopTolerance": 1.0,
      "powerMode": "static",
      "trainCount": 1,
      "departureInterval": 120
    }
  }
}
```

### 3.2 更新仿真配置

**请求**：

```
PUT /config
Content-Type: application/json
```

**请求体**（所有字段可选，只更新提供的新值）：

```json
{
  "simulation": {
    "totalTime": 900,
    "speedMultiplier": 5,
    "trainCount": 3,
    "departureInterval": 180
  }
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "updated": ["simulation.totalTime", "simulation.speedMultiplier", "simulation.trainCount", "simulation.departureInterval"],
    "config": { "...": "更新后的完整配置" }
  }
}
```

**错误**：

| code | message | 触发条件 |
|------|---------|----------|
| 40001 | 参数验证失败 | 参数值超出合法范围 |
| 40003 | 仿真运行中无法修改配置 | 当前仿真状态为 running |

### 3.3 获取线路配置

**请求**：

```
GET /config/line
```

**响应**：同 3.1 中的 `data.line` 部分。

### 3.4 更新线路配置

**请求**：

```
PUT /config/line
Content-Type: application/json
```

**请求体**：

```json
{
  "stations": [
    { "id": "ST03", "name": "C站", "chainage": 3200, "defaultDwellTime": 25, "isTerminus": true }
  ],
  "segments": [
    { "id": "SEC03", "startChainage": 1500, "endChainage": 3200, "gradient": 30, "curvature": 1200, "speedLimit": 80 }
  ]
}
```

### 3.5 获取车辆配置

**请求**：

```
GET /config/vehicle
```

**响应**：同 3.1 中的 `data.vehicle` 部分。

### 3.6 更新车辆配置

**请求**：

```
PUT /config/vehicle
Content-Type: application/json
```

**请求体**：

```json
{
  "emptyMass": 220000,
  "maxTractionForce": 420000,
  "tractionCurve": [
    { "speed": 0, "forcePercent": 1.0 },
    { "speed": 50, "forcePercent": 0.9 },
    { "speed": 100, "forcePercent": 0.4 }
  ]
}
```

---

## 4. 仿真控制接口

### 4.1 获取仿真运行状态

**请求**：

```
GET /simulation/status
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runState": "running",
    "simulationTime": 123.456,
    "totalTime": 600,
    "speedMultiplier": 5,
    "trainCount": 1,
    "fps": 16.7,
    "realTimeElapsed": 24.7,
    "startedAt": "2026-07-06T10:00:00Z"
  }
}
```

`runState` 可选值：`idle` / `running` / `paused` / `stopped`

### 4.2 启动仿真

**请求**：

```
POST /simulation/start
Content-Type: application/json
```

**请求体**（可选，不传则使用当前配置）：

```json
{
  "config": {
    "timeStep": 0.1,
    "totalTime": 600,
    "speedMultiplier": 5,
    "trainCount": 1
  }
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runId": 1,
    "runState": "running",
    "simulationTime": 0
  }
}
```

**错误**：

| code | message | 触发条件 |
|------|---------|----------|
| 40002 | 仿真已在运行中 | 当前状态不为 idle |
| 40003 | 配置不完整 | 缺少必要配置项 |
| 50001 | 仿真启动失败 | 内部初始化异常 |

### 4.3 暂停仿真

**请求**：

```
POST /simulation/pause
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runState": "paused",
    "simulationTime": 123.456
  }
}
```

**错误**：

| code | message |
|------|---------|
| 40002 | 仿真未在运行中 |

### 4.4 恢复仿真

**请求**：

```
POST /simulation/resume
```

**响应**：同 4.3（`runState` 为 `running`）。

### 4.5 停止仿真

**请求**：

```
POST /simulation/stop
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runState": "stopped",
    "runId": 1,
    "summary": {
      "simulatedDuration": 600.0,
      "realDuration": 42.3,
      "totalSteps": 6000,
      "trains": [
        {
          "trainId": "TRAIN_01",
          "totalDistance": 15000,
          "avgSpeed": 45.2,
          "maxSpeed": 78.5,
          "totalEnergy": 320.5,
          "totalRegeneration": 28.3,
          "stopCount": 5
        }
      ]
    }
  }
}
```

### 4.6 重置仿真

**请求**：

```
POST /simulation/reset
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runState": "idle",
    "simulationTime": 0
  }
}
```

### 4.7 单步执行

**请求**：

```
POST /simulation/step
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runState": "paused",
    "simulationTime": 0.1,
    "snapshot": { "..." }
  }
}
```

`snapshot` 字段内容同 WebSocket `simulation_snapshot` 消息（详见第 8.4 节）。

### 4.8 设置速度倍率

**请求**：

```
PUT /simulation/speed
Content-Type: application/json
```

**请求体**：

```json
{
  "speedMultiplier": 10
}
```

合法值：`0.5` / `1` / `2` / `5` / `10` / `50`

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "speedMultiplier": 10
  }
}
```

### 4.9 获取仿真运行记录列表

**请求**：

```
GET /simulation/runs?page=1&pageSize=10
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "runId": 1,
        "status": "completed",
        "startedAt": "2026-07-06T10:00:00Z",
        "endedAt": "2026-07-06T10:00:42Z",
        "simulatedDuration": 600.0,
        "realDuration": 42.3,
        "totalSteps": 6000,
        "trainCount": 1,
        "notes": null
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 10,
      "total": 3,
      "totalPages": 1
    }
  }
}
```

### 4.10 获取指定运行记录详情

**请求**：

```
GET /simulation/runs/{runId}
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| runId | integer | 运行记录 ID |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runId": 1,
    "status": "completed",
    "startedAt": "2026-07-06T10:00:00Z",
    "endedAt": "2026-07-06T10:00:42Z",
    "simulatedDuration": 600.0,
    "realDuration": 42.3,
    "totalSteps": 6000,
    "simulationConfig": { "...": "该次运行使用的完整配置快照" },
    "trains": [
      {
        "trainId": "TRAIN_01",
        "totalDistance": 15000.0,
        "avgSpeed": 45.2,
        "maxSpeed": 78.5,
        "totalEnergy": 320.5,
        "totalRegeneration": 28.3,
        "tripTime": 593.2,
        "stopCount": 5
      }
    ]
  }
}
```

### 4.11 获取运行结果汇总

**请求**：

```
GET /simulation/runs/{runId}/results
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "runId": 1,
    "trains": [
      {
        "trainId": "TRAIN_01",
        "totalDistance": 15000.0,
        "avgSpeed": 45.2,
        "maxSpeed": 78.5,
        "totalEnergyConsumption": 320.5,
        "totalRegeneration": 28.3,
        "tripTime": 593.2,
        "stopCount": 5
      }
    ]
  }
}
```

### 4.12 获取运行事件记录

**请求**：

```
GET /simulation/runs/{runId}/events?page=1&pageSize=50&severity=warning
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| severity | string | — | 过滤：info / warning / error / critical |
| eventType | string | — | 过滤：overspeed / emergency_brake / door_fault / ... |
| page | integer | 1 | 页码 |
| pageSize | integer | 50 | 每页条数 |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "simulationTime": 45.2,
        "eventType": "overspeed",
        "severity": "warning",
        "trainId": "TRAIN_01",
        "message": "TRAIN_01 速度 82.5 km/h 超过区段限速 80 km/h",
        "rawData": {
          "speed": 82.5,
          "limit": 80,
          "position": 850.0
        }
      }
    ],
    "pagination": { "page": 1, "pageSize": 50, "total": 1, "totalPages": 1 }
  }
}
```

---

## 5. 参数编辑接口

### 5.1 获取当前运行时参数

**请求**：

```
GET /params
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "vehicle": {
      "emptyMass": 200000,
      "passengerCapacity": 1500,
      "maxSpeed": 100,
      "maxTractionForce": 400000,
      "maxBrakeForce": 350000,
      "davisA": 0.01,
      "davisB": 0.0001,
      "davisCFrontArea": 10,
      "davisCDragCoeff": 0.5,
      "curveResistCoeff": 600,
      "tunnelResistFactor": 1.2
    },
    "track": {
      "gradient": 5,
      "curvature": 800,
      "speedLimit": 80
    },
    "power": {
      "pantographVoltage": 1500,
      "substationCapacity": 5000
    },
    "signal": {
      "dwellTime": 30,
      "departureInterval": 120,
      "targetSpeedRatio": 0.8
    }
  }
}
```

> 注：track 的参数为当前选中区段的参数（可在前端选中后修改）。

### 5.2 更新运行时参数

**请求**：

```
PUT /params
Content-Type: application/json
```

**请求体**：

```json
{
  "vehicle": {
    "emptyMass": 220000,
    "passengerCapacity": 1800
  },
  "signal": {
    "dwellTime": 35,
    "departureInterval": 180
  }
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "updated": ["vehicle.emptyMass", "vehicle.passengerCapacity", "signal.dwellTime", "signal.departureInterval"],
    "params": { "...": "更新后的完整参数" }
  }
}
```

### 5.3 获取参数预设方案列表

**请求**：

```
GET /params/presets
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "presetId": 1,
        "name": "高峰时段配置",
        "description": "发车间隔 120s，站停 25s",
        "createdAt": "2026-07-01T10:00:00Z",
        "updatedAt": "2026-07-05T14:30:00Z"
      },
      {
        "presetId": 2,
        "name": "平峰时段配置",
        "description": "发车间隔 300s，站停 35s",
        "createdAt": "2026-07-02T09:00:00Z",
        "updatedAt": "2026-07-02T09:00:00Z"
      }
    ]
  }
}
```

### 5.4 创建参数预设方案

**请求**：

```
POST /params/presets
Content-Type: application/json
```

**请求体**：

```json
{
  "name": "高峰时段配置",
  "description": "发车间隔 120s，站停 25s",
  "params": {
    "vehicle": { "emptyMass": 220000 },
    "power": { "pantographVoltage": 1500 },
    "signal": { "dwellTime": 25, "departureInterval": 120 }
  }
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "presetId": 3,
    "name": "高峰时段配置",
    "createdAt": "2026-07-06T10:00:00Z"
  }
}
```

### 5.5 获取预设方案详情

**请求**：

```
GET /params/presets/{presetId}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "presetId": 1,
    "name": "高峰时段配置",
    "description": "发车间隔 120s，站停 25s",
    "params": {
      "vehicle": { "emptyMass": 220000, "passengerCapacity": 1800 },
      "power": { "pantographVoltage": 1500 },
      "signal": { "dwellTime": 25, "departureInterval": 120, "targetSpeedRatio": 0.85 }
    },
    "createdAt": "2026-07-01T10:00:00Z",
    "updatedAt": "2026-07-05T14:30:00Z"
  }
}
```

### 5.6 更新预设方案

**请求**：

```
PUT /params/presets/{presetId}
Content-Type: application/json
```

**请求体**：

```json
{
  "name": "高峰时段配置 v2",
  "description": "更新后的高峰配置",
  "params": {
    "signal": { "dwellTime": 20 }
  }
}
```

### 5.7 应用预设方案

**请求**：

```
PUT /params/presets/{presetId}/apply
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "applied": true,
    "updated": ["vehicle.emptyMass", "signal.dwellTime", "signal.departureInterval"],
    "params": { "...": "应用后的完整参数" }
  }
}
```

### 5.8 删除预设方案

**请求**：

```
DELETE /params/presets/{presetId}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

---

## 6. 数据导出接口

### 6.1 导出 CSV 数据

**请求**：

```
GET /simulation/export/csv?runId=1&format=full
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| runId | integer | — | 运行记录 ID（必填） |
| format | string | full | full（全部数据）/ summary（摘要数据） |
| trainId | string | — | 指定列车（不传则导出全部列车） |
| fields | string | — | 指定字段逗号分隔，如 "time,position,speed,mode" |

**响应**：

```
Content-Type: text/csv
Content-Disposition: attachment; filename="simulation_run_1.csv"

time,position,speed,mode,acceleration,power_demand,voltage
0.0,0.0,0.0,traction,1.0,4000,1500
0.1,0.1,0.36,traction,0.98,3950,1500
0.2,0.2,0.71,traction,0.95,3900,1500
...
```

### 6.2 导出当前快照截图

**请求**：

```
GET /simulation/export/snapshot?view=overview
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| view | string | overview | 视图模式：overview / power / signal / vehicle / track |
| width | integer | 1920 | 截图宽度 |
| height | integer | 1080 | 截图高度 |

**响应**：

```
Content-Type: image/png
Content-Disposition: attachment; filename="snapshot_overview.png"
```

> 注：该接口由前端实现截图功能并下载，后端不提供服务端渲染截图。

---

## 7. 事件查询接口

### 7.1 获取仿真事件/告警

**请求**：

```
GET /events?page=1&pageSize=50&severity=warning&eventType=emergency_brake
```

**查询参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| pageSize | integer | 50 | 每页条数 |
| severity | string | — | 过滤：info / warning / error / critical |
| eventType | string | — | 过滤事件类型 |
| runId | integer | — | 指定运行记录 |
| startTime | float | — | 仿真起始时间过滤 |
| endTime | float | — | 仿真结束时间过滤 |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "id": 1,
        "runId": 1,
        "simulationTime": 45.2,
        "eventType": "emergency_brake",
        "severity": "critical",
        "trainId": "TRAIN_01",
        "message": "TRAIN_01 ATP触发紧急制动：速度超过限速",
        "rawData": {
          "speed": 85.0,
          "speedLimit": 80,
          "position": 850.3,
          "brakeForce": 350000
        }
      }
    ],
    "pagination": { "page": 1, "pageSize": 50, "total": 1, "totalPages": 1 }
  }
}
```

---

## 8. 方案管理接口（Scenario Management — 新增）

### 8.1 获取方案列表

获取所有已保存方案的摘要（不含完整 params，含结果摘要指标）。

**请求**：

```
GET /scenarios
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": [
    {
      "id": "scenario_20260713_001",
      "name": "ATO经济模式",
      "description": "ATO模式+低目标速度系数，节能优先",
      "createdAt": "2026-07-13T10:30:00Z",
      "totalTime": 185.3,
      "avgSpeed": 45.2,
      "netEnergy": 24.3,
      "tractionEnergy": 28.5
    },
    {
      "id": "scenario_20260713_002",
      "name": "三段式重载",
      "description": "三段式+高载重",
      "createdAt": "2026-07-13T11:00:00Z",
      "totalTime": 210.0,
      "avgSpeed": 38.5,
      "netEnergy": 32.1,
      "tractionEnergy": 35.0
    }
  ]
}
```

### 8.2 保存方案

将当前引擎参数 + 最新仿真结果保存为一个命名方案。

**请求**：

```
POST /scenarios
Content-Type: application/json
```

**请求体**：

```json
{
  "name": "ATO经济模式",
  "description": "ATO模式+低目标速度系数，节能优先"
}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "scenario_20260713_001",
    "name": "ATO经济模式",
    "createdAt": "2026-07-13T10:30:00Z"
  }
}
```

**错误**：

| code | message | 触发条件 |
|------|---------|----------|
| 40002 | 仿真正在运行中，请先暂停或停止 | 当前引擎状态为 running |
| 40003 | 尚无仿真结果，请先运行一次仿真 | 引擎从未运行过或结果为空 |

### 8.3 获取方案详情

**请求**：

```
GET /scenarios/{scenarioId}
```

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| scenarioId | string | 方案 ID，如 `scenario_20260713_001` |

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "scenario_20260713_001",
    "name": "ATO经济模式",
    "description": "ATO模式+低目标速度系数，节能优先",
    "createdAt": "2026-07-13T10:30:00Z",
    "params": {
      "vehicle": { "emptyMass": 220000, "maxSpeed": 80, "maxTractionForce": 300000 },
      "signal": { "mode": "ato", "targetSpeedRatio": 0.7, "dwellTime": 30 },
      "power": { "mode": "simple_ohm", "substationCapacity": 5000 },
      "simulation": { "trainCount": 1, "departureInterval": 120 }
    },
    "result": {
      "totalTime": 185.3,
      "totalDistance": 3200.0,
      "avgSpeed": 45.2,
      "maxSpeed": 64.1,
      "tractionEnergy": 28.5,
      "regenEnergy": 4.2,
      "netEnergy": 24.3,
      "minVoltage": 1380,
      "peakPower": 3200
    }
  }
}
```

### 8.4 删除方案

**请求**：

```
DELETE /scenarios/{scenarioId}
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": null
}
```

### 8.5 加载方案到引擎

将方案参数应用到引擎（重置后加载），前端参数面板刷新为该方案配置。

**请求**：

```
PUT /scenarios/{scenarioId}/apply
```

**响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "applied": true,
    "config": { "...": "更新后的完整配置" }
  }
}
```

**错误**：

| code | message | 触发条件 |
|------|---------|----------|
| 40002 | 仿真正在运行中，请先暂停或停止 | 当前引擎状态为 running |
| 40004 | 方案不存在 | scenarioId 对应的文件不存在 |

---

## 9. 手动驾驶控制接口（迭代三）

### 9.1 切换手动驾驶模式

**请求**：
```
POST /control/manual/activate
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "manualMode": true,
    "trainId": "TRAIN_01"
  }
}
```

**错误**：

| code | message | 触发条件 |
|------|---------|----------|
| 40002 | 仿真未在运行中 | 当前仿真状态非 running |

### 9.2 切回自动驾驶模式

**请求**：
```
POST /control/manual/deactivate
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "manualMode": false,
    "trainId": "TRAIN_01"
  }
}
```

### 9.3 设置手动牵引级位

**请求**：
```
PUT /control/manual/throttle
Content-Type: application/json
```

**请求体**：
```json
{
  "trainId": "TRAIN_01",
  "level": 0.8
}
```

`level` 取值范围：`[0, 1]`，`0` 为零牵引，`1` 为最大牵引力。

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "trainId": "TRAIN_01",
    "tractionLevel": 0.8
  }
}
```

### 9.4 设置手动制动级位

**请求**：
```
PUT /control/manual/brake
Content-Type: application/json
```

**请求体**：
```json
{
  "trainId": "TRAIN_01",
  "level": 0.5
}
```

`level` 取值范围：`[0, 1]`，`0` 为零制动，`1` 为最大制动力。

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "trainId": "TRAIN_01",
    "brakeLevel": 0.5
  }
}
```

### 9.5 触发手动紧急制动

**请求**：
```
POST /control/manual/emergency-brake
Content-Type: application/json
```

**请求体**：
```json
{
  "trainId": "TRAIN_01"
}
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "trainId": "TRAIN_01",
    "emergencyBrake": true
  }
}
```

### 9.6 获取手动驾驶模式状态

**请求**：
```
GET /control/manual/status?trainId=TRAIN_01
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "trainId": "TRAIN_01",
    "manualMode": true,
    "tractionLevel": 0.8,
    "brakeLevel": 0.0,
    "emergencyBrake": false
  }
}
```

---

## 10. 实体司机台通信接口（迭代三，接口预留）

### 10.1 设计说明

> 本组接口为**预留接口层**，用于未来与外部实体司机台（硬件设备）进行通信。当前阶段（迭代三）：
> - 接口定义已固定，后续扩展时不会破坏已有接口
> - 具体通信协议（CAN / Modbus / OPC UA / 串口 / Ethernet）待后续确定
> - 后端提供 Mock 实现，用于前端联调和测试
> - 实体司机台对接将在迭代四协议确定后实施

### 10.2 获取司机台连接状态

**请求**：
```
GET /drivercab/status
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "connected": false,
    "driverCabType": "mock",
    "protocol": "pending",
    "lastHeartbeat": null
  }
}
```

### 10.3 建立司机台连接

**请求**：
```
POST /drivercab/connect
Content-Type: application/json
```

**请求体**：
```json
{
  "protocol": "mock",
  "endpoint": "",
  "config": {}
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| protocol | string | 协议类型：`mock`（模拟）/ `can` / `modbus` / `opcua` / `serial` / `tcp`，当前仅 `mock` 可用 |
| endpoint | string | 连接端点地址（具体协议确定后定义格式） |
| config | object | 协议特定配置（待后续确定） |

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "connected": true,
    "driverCabType": "mock",
    "connectedAt": "2026-07-07T10:00:00Z"
  }
}
```

### 10.4 断开司机台连接

**请求**：
```
POST /drivercab/disconnect
```

**响应**：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "connected": false
  }
}
```

---

## 11. WebSocket 实时通信协议

### 11.1 连接建立

客户端连接：

```
ws://localhost:8000/ws
wss://sim.example.com/ws
```

连接成功后，服务端立即发送初始化消息 `init_state`。

### 11.2 连接心跳

- 服务端每 **15 秒** 发送心跳消息
- 客户端收到后无需回复
- 客户端若连续 **60 秒** 未收到任何消息，认为连接断开

```json
{
  "type": "heartbeat",
  "serverTime": "2026-07-06T10:00:00Z"
}
```

### 11.3 消息类型总览

| 方向 | 类型 | 说明 | 频率 |
|------|------|------|------|
| S→C | `init_state` | 连接建立后的初始化全量状态 | 连接时一次 |
| S→C | `simulation_snapshot` | 每仿真步的状态快照 | 仿真运行时每步 |
| S→C | `simulation_status` | 仿真状态变更通知（开始/暂停/停止） | 状态变化时 |
| S→C | `simulation_complete` | 仿真运行完成通知 | 运行时一次 |
| S→C | `event_alert` | 事件/告警推送 | 事件发生时 |
| S→C | `manual_mode_status` | 手动驾驶模式状态变更通知 | 模式切换时 |
| S→C | `drivercab_status` | 司机台连接状态变更通知 | 连接状态变化时 |
| S→C | `heartbeat` | 心跳 | 每 15s |
| C→S | `sim_control` | 仿真控制指令 | 按需 |
| C→S | `param_update` | 参数更新指令 | 按需 |
| C→S | `manual_control` | 手动驾驶控制指令（牵引/制动级位） | 按需（手动模式下） |
| C→S | `drivercab_data` | 实体司机台数据透传（预留） | 按需 |

### 11.4 消息格式详解

#### 8.4.1 init_state

服务端在 WebSocket 连接建立后立即发送：

```json
{
  "type": "init_state",
  "config": {
    "line": {
      "name": "1号线",
      "direction": "up",
      "totalLength": 15000,
      "stations": [
        { "id": "ST01", "name": "A站", "chainage": 0, "platformHalfLength": 15 },
        { "id": "ST02", "name": "B站", "chainage": 1500, "platformHalfLength": 15 },
        { "id": "ST03", "name": "C站", "chainage": 3200, "platformHalfLength": 15 }
      ],
      "segments": [
        { "id": "SEC01", "startChainage": 0, "endChainage": 1500, "gradient": 5, "curvature": 800, "speedLimit": 80 },
        { "id": "SEC02", "startChainage": 1500, "endChainage": 3200, "gradient": 30, "curvature": 1200, "speedLimit": 80 }
      ]
    },
    "vehicle": {
      "id": "TYPE_A",
      "emptyMass": 200000,
      "maxSpeed": 100,
      "tractionCurve": [...]
    },
    "simulation": {
      "timeStep": 0.1,
      "totalTime": 600,
      "speedMultiplier": 1
    }
  },
  "state": {
    "runState": "idle",
    "simulationTime": 0
  }
}
```

#### 8.4.2 simulation_snapshot

仿真运行时每步推送（仅当有 WebSocket 连接时）：

```json
{
  "type": "simulation_snapshot",
  "timestamp": 123.4,
  "data": {
    "clock": {
      "elapsed": 123.4,
      "speedMultiplier": 5
    },
    "trains": [
      {
        "id": "TRAIN_01",
        "position": 1520.5,
        "speed": 72.3,
        "acceleration": 0.5,
        "mode": "traction",
        "mass": 215000,
        "passengerCount": 750,
        "pantographVoltage": 1485.0,
        "powerDemand": 3200.0,
        "tractionForce": 280000,
        "totalResistance": 42000,
        "brakeForce": 0,
        "doorStatus": "closed",
        "runningBrakeForce": 0,
        "faultAlarm": null
      }
    ],
    "power": {
      "substations": [
        { "id": "SUB_01", "chainage": 0, "outputCurrent": 1200, "outputPower": 1800, "energyAccumulated": 45.2 }
      ],
      "voltageProfile": [
        { "chainage": 0, "voltage": 1500 },
        { "chainage": 500, "voltage": 1492 },
        { "chainage": 1000, "voltage": 1485 },
        { "chainage": 1500, "voltage": 1490 }
      ],
      "totalConsumption": 320.5,
      "totalRegeneration": 28.3
    },
    "signaling": {
      "controlCommands": [
        {
          "trainId": "TRAIN_01",
          "tractionLevel": 0,
          "brakeLevel": 0.6,
          "emergencyBrake": false
        }
      ],
      "emergencyBrakes": [],
      "atsDisplay": {
        "trains": [
          { "id": "TRAIN_01", "position": 1520.5, "speed": 72.3, "status": "running" }
        ],
        "trainIntervals": []
      },
      "speedLimits": [
        { "trainId": "TRAIN_01", "permanentLimit": 80, "temporaryLimit": null, "atpLimit": 78.5 }
      ]
    },
    "track": {
      "occupancy": [
        { "circuitId": "TC_01", "occupied": true },
        { "circuitId": "TC_02", "occupied": false },
        { "circuitId": "TC_03", "occupied": false }
      ],
      "switchStates": [
        { "id": "SW_01", "state": "normal" }
      ],
      "currentSegment": {
        "id": "SEC01",
        "gradient": 5,
        "curvature": 800,
        "speedLimit": 80,
        "isTunnel": false
      }
    },
    "events": [
      {
        "time": 123.4,
        "type": "info",
        "severity": "info",
        "trainId": "TRAIN_01",
        "message": "TRAIN_01 通过 B站 站台中心"
      }
    ]
  }
}
```

#### 8.4.3 simulation_status

仿真运行状态变更通知：

```json
{
  "type": "simulation_status",
  "data": {
    "runState": "paused",
    "simulationTime": 123.4,
    "reason": "user_pause"
  }
}
```

`reason` 可选值：`user_start` / `user_pause` / `user_resume` / `user_stop` / `completed` / `error`

#### 8.4.4 simulation_complete

仿真运行正常完成：

```json
{
  "type": "simulation_complete",
  "data": {
    "runId": 1,
    "simulationTime": 600.0,
    "summary": {
      "trains": [
        { "trainId": "TRAIN_01", "totalDistance": 15000, "avgSpeed": 45.2, "maxSpeed": 78.5 }
      ]
    }
  }
}
```

#### 8.4.5 event_alert

仿真事件/告警实时推送：

```json
{
  "type": "event_alert",
  "data": {
    "simulationTime": 45.2,
    "eventType": "overspeed",
    "severity": "warning",
    "trainId": "TRAIN_01",
    "message": "TRAIN_01 速度 82.5 km/h 超过区段限速 80 km/h",
    "rawData": { "speed": 82.5, "limit": 80 }
  }
}
```

### 11.5 客户端 → 服务端消息

#### 8.5.1 sim_control — 仿真控制指令

```json
{
  "type": "sim_control",
  "action": "start",
  "config": {
    "speedMultiplier": 5,
    "totalTime": 900
  }
}
```

`action` 可选值：`start` / `pause` / `resume` / `stop` / `reset` / `step`

#### 8.5.3 manual_control — 手动驾驶控制指令

手动模式下，前端或实体司机台通过此消息发送牵引/制动操作指令：

```json
{
  "type": "manual_control",
  "data": {
    "trainId": "TRAIN_01",
    "tractionLevel": 0.0,
    "brakeLevel": 0.6,
    "emergencyBrake": false
  }
}
```

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| trainId | string | — | 目标列车 ID |
| tractionLevel | float | [0, 1] | 牵引级位，0=零牵引，1=最大牵引力 |
| brakeLevel | float | [0, 1] | 制动级位，0=零制动，1=最大制动力 |
| emergencyBrake | bool | — | 紧急制动触发标志 |

> **注意：** 牵引级位和制动级位不应同时 > 0。若同时发送，制动优先。

#### 8.5.4 drivercab_data — 实体司机台数据透传（预留）

用于未来与实体司机台进行数据透传，当前阶段（迭代三）仅定义消息格式，不做具体处理：

```json
{
  "type": "drivercab_data",
  "data": {
    "direction": "inbound",
    "payload": {}
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| direction | string | `inbound`（司机台→系统）/ `outbound`（系统→司机台） |
| payload | object | 透传数据，格式由具体通信协议确定 |

#### 8.5.2 param_update — 参数更新

```json
{
  "type": "param_update",
  "params": {
    "vehicle": { "emptyMass": 220000 },
    "signal": { "dwellTime": 35, "departureInterval": 180 }
  }
}
```

---

## 12. 数据模型定义

### 12.1 TrainState（列车实时状态）

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| id | string | — | 列车唯一标识，如 `TRAIN_01` |
| position | float | m | 实时公里标位置 |
| speed | float | km/h | 瞬时速度 |
| acceleration | float | m/s² | 瞬时加速度 |
| mode | enum | — | 当前工况：`traction` / `coasting` / `braking` / `stopped` |
| mass | float | kg | 当前总质量（含乘客） |
| passengerCount | int | — | 当前载客数 |
| pantographVoltage | float | V | 受电弓端电压 |
| powerDemand | float | kW | 受电弓功率请求（正=牵引，负=再生） |
| tractionForce | float | N | 当前牵引力 |
| brakeForce | float | N | 当前制动力 |
| totalResistance | float | N | 当前总阻力 |
| doorStatus | enum | — | 车门状态：`open` / `closed` / `opening` / `closing` |
| faultAlarm | object | — | 故障告警，null 表示无故障 |

### 12.2 SubstationState（变电所状态）

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| id | string | — | 变电所 ID |
| chainage | float | m | 位置公里标 |
| outputCurrent | float | A | 当前输出电流 |
| outputPower | float | kW | 当前输出功率 |
| energyAccumulated | float | kWh | 累计供能 |

### 12.3 ControlCommand（信号控制指令）

| 字段 | 类型 | 范围 | 说明 |
|------|------|------|------|
| trainId | string | — | 目标列车 ID |
| tractionLevel | float | [0, 1] | 牵引级位 |
| brakeLevel | float | [0, 1] | 制动级位 |
| emergencyBrake | bool | — | 是否紧急制动 |

### 12.4 OccupancyInfo（轨道区段占用）

| 字段 | 类型 | 说明 |
|------|------|------|
| circuitId | string | 轨道电路/计轴器 ID |
| occupied | bool | 是否被占用 |

### 12.5 SwitchState（道岔状态）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 道岔 ID |
| state | enum | `normal` / `reverse` / `transitioning` |

### 12.6 SimEvent（仿真事件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 事件 ID |
| runId | int | 所属运行记录 |
| simulationTime | float | 仿真时间（s） |
| eventType | enum | 事件类型 |
| severity | enum | 严重级别 |
| trainId | string | 关联列车（可选） |
| message | string | 事件描述 |
| rawData | object | 附加数据（可选） |

`eventType` 可选值：`overspeed` / `emergency_brake` / `door_fault` / `power_trip` / `switch_failure` / `station_arrival` / `station_departure` / `info`

`severity` 可选值：`info` / `warning` / `error` / `critical`

---

## 13. 错误码说明

### 13.1 错误码列表

| code | message | HTTP 状态码 | 说明 |
|------|---------|-------------|------|
| 0 | success | 200 | 请求成功 |
| 40001 | 参数验证失败 | 400 | 请求参数不合法 |
| 40002 | 操作冲突 | 409 | 当前状态不允许此操作 |
| 40003 | 配置不完整 | 400 | 缺少必要配置 |
| 40004 | 资源不存在 | 404 | 请求的资源不存在 |
| 40005 | 资源已存在 | 409 | 尝试创建已存在的资源 |
| 50001 | 内部错误 | 500 | 服务端未捕获异常 |
| 50002 | 仿真引擎错误 | 500 | 仿真计算异常 |
| 50003 | 数据库错误 | 500 | 数据库操作异常 |
| 50004 | WebSocket 推送错误 | 500 | 消息推送失败 |

### 13.2 错误码扩展规则

- `400xx`：客户端请求错误
- `401xx`：认证/授权错误（未来扩展）
- `500xx`：服务端错误
- 新错误码按顺序递增分配

---

## 附录 A：接口-迭代对照矩阵

| 接口 | 迭代一 | 迭代二 | 迭代三 | 迭代四 |
|------|--------|--------|--------|--------|
| GET /config | ✅ | ✅ | ✅ | ✅ |
| PUT /config | ✅ | ✅ | ✅ | ✅ |
| GET /config/line | ✅ | ✅ | ✅ | ✅ |
| GET /config/vehicle | ✅ | ✅ | ✅ | ✅ |
| GET /simulation/status | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/start | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/pause | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/resume | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/stop | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/reset | ✅ | ✅ | ✅ | ✅ |
| POST /simulation/step | ✅ | ✅ | ✅ | ✅ |
| PUT /simulation/speed | ✅ | ✅ | ✅ | ✅ |
| GET /simulation/runs | ✅ | ✅ | ✅ | ✅ |
| GET /simulation/runs/{id} | ✅ | ✅ | ✅ | ✅ |
| GET /simulation/runs/{id}/results | ✅ | ✅ | ✅ | ✅ |
| GET /simulation/runs/{id}/events | | ✅ | ✅ | ✅ |
| GET /simulation/export/csv | ✅ | ✅ | ✅ | ✅ |
| GET /params | ✅ | ✅ | ✅ | ✅ |
| PUT /params | ✅ | ✅ | ✅ | ✅ |
| GET /params/presets | | | ✅ | ✅ |
| POST /params/presets | | | ✅ | ✅ |
| DELETE /params/presets/{id} | | | ✅ | ✅ |
| GET /events | | ✅ | ✅ | ✅ |
| WebSocket 初始化 | ✅ | ✅ | ✅ | ✅ |
| WebSocket 快照推送 | ✅ | ✅ | ✅ | ✅ |
| WebSocket 事件推送 | | ✅ | ✅ | ✅ |
| POST /control/manual/activate | | | ✅ | ✅ |
| POST /control/manual/deactivate | | | ✅ | ✅ |
| PUT /control/manual/throttle | | | ✅ | ✅ |
| PUT /control/manual/brake | | | ✅ | ✅ |
| POST /control/manual/emergency-brake | | | ✅ | ✅ |
| GET /control/manual/status | | | ✅ | ✅ |
| GET /drivercab/status | | | ✅ | ✅ |
| POST /drivercab/connect | | | ✅ | ✅ |
| POST /drivercab/disconnect | | | ✅ | ✅ |
| GET /scenarios | | | ✅ | ✅ |
| POST /scenarios | | | ✅ | ✅ |
| GET /scenarios/{id} | | | ✅ | ✅ |
| DELETE /scenarios/{id} | | | ✅ | ✅ |
| PUT /scenarios/{id}/apply | | | ✅ | ✅ |
| WebSocket manual_control | | | ✅ | ✅ |
| WebSocket drivercab_data | | | ✅ | ✅ |

## 附录 B：WebSocket 消息体大小估算

| 消息类型 | 1 列车 | 10 列车 | 说明 |
|----------|--------|---------|------|
| init_state | ~5 KB | ~5 KB | 配置数据与列车数无关 |
| simulation_snapshot | ~1.2 KB | ~6 KB | 每列车约 0.5 KB |
| event_alert | ~0.3 KB | ~0.3 KB | 单次事件 |

> 按 100ms 步长、10 列车估算：推送带宽 ≈ 60 KB/s（WebSocket 帧开销约 30% → 实际约 78 KB/s），远低于现代 WebSocket 上限。按 10× 倍率运行时，推送频率仍为 10 次/s，只是快照间隔变大，带宽需求不变。