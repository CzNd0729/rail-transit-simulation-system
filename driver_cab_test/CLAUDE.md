# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in the `driver_cab_test/` directory.

## 项目概述

司机台联动测试模块 — 独立于仿真后端，负责对接司机驾驶模拟台（PLC/网络屏/信号屏），接收司机台信号并返回控制信号，在整个系统中起沟通司机台与信号系统的桥梁作用。

**核心文档**：`docs/轨交多系统平台接口协议汇总20260630.md`（第（二）节 司机台协议）

## 环境区分

| 环境 | 说明 | 配置开关 |
|------|------|---------|
| **本地模拟** | 无真实硬件，纯软件模拟 | `config.py` 中 `USE_REAL_HARDWARE = False`，IP 自动切换 `127.0.0.1` |
| **生产环境** | 有真实硬件，连接物理 PLC/屏 | `USE_REAL_HARDWARE = True`，使用真实 IP（192.168.100.x） |

## 文件结构

```
driver_cab_test/
├── __init__.py          # 包初始化
├── CLAUDE.md            # 本文件
├── README.md            # 使用说明文档
├── config.py            # 通信参数配置（IP/端口/位定义/枚举/偏移量）
├── protocols.py         # 协议编解码核心库（含自检，可独立运行）
├── plc_simulator.py     # PLC 模拟服务器（纯软件，TCP Server）
└── listen_plc.py        # PLC 数据监听器（TCP Client，只收不发）
```

## 涉及的协议（以 docs/ 文档为准）

| 协议 | 传输方式 | 服务器 | 端口 | 方向 | 报文大小 |
|------|---------|--------|------|------|---------|
| PLC协议 | TCP | 192.168.100.123 | 8001/8002/8003 | 上位机 ↔ PLC | 46B(PLC→上位机) / 26B(上位机→PLC) |
| 网络屏协议 | TCP | 192.168.100.122 | 8888 | 上位机 ↔ 网络屏 | 572B(上位机→网络屏) / 26B(网络屏→上位机, 牵引切除) |
| 信号屏协议 | TCP | 192.168.100.121 | 9999 | 上位机 → 信号屏 | 66B |
| 信号系统UDP | UDP | 192.168.100.10/20 | 9000/9001 | 信号系统 ↔ 总控数据库节点 | 动态 |

### PLC 协议注意点

- PLC 使用**三菱 PLC**，WORD 以**小端（little-endian）**方式存储
- 但报文在网络传输中**整体为大端序（big-endian）**——`protocols.py` 中 `struct.pack(">...")`/`unpack(">...")` 处理
- 字节偏移 0-23 为报文头（24字节），字节偏移 24-45 为数据区（22字节）
- 关键位定义（字节 24/25/28/29/34/35）以 `protocols.py` 中的 `PLC_BIT_*` 字典为准

## 常用命令

### 运行自检

```bash
# 协议编解码自检（无需任何外部依赖）
python -m driver_cab_test.protocols
```

### 启动 PLC 模拟器

```bash
# 后台运行（绑定 127.0.0.1）
python -m driver_cab_test.plc_simulator --local

# 交互模式（可实时调参数）
python -m driver_cab_test.plc_simulator --local -i
```

### 监听 PLC 数据

```bash
# 连接本地模拟器，持续接收
python -m driver_cab_test.listen_plc --local

# 接收 100 包后退出
python -m driver_cab_test.listen_plc --local --count 100

# 每 2 秒刷新一次显示
python -m driver_cab_test.listen_plc --local --interval 2
```

### 连接真实硬件

```bash
# 不加 --local 默认连接真实 PLC（192.168.100.123:8001）
python -m driver_cab_test.listen_plc
```

## 架构说明

### 通信架构

```
  司机驾驶模拟台                        上位机（本模块）
  ┌──────────────┐    TCP 46B/100ms    ┌──────────────────┐
  │  PLC 服务器   │ ←───────────────── │  listen_plc.py   │
  │  :8001/8002/ │ ─────────────────→ │  (TCP Client)    │
  │  8003        │    TCP 26B(按需)    │                  │
  └──────────────┘                     └──────────────────┘
  ┌──────────────┐    TCP 572B        ┌──────────────────┐
  │  网络屏 HMI   │ ←───────────────── │  protocols.py    │
  │  :8888       │ ──── TCP 26B ────→ │  (编解码核心库)   │
  │              │  (牵引切除请求)      │                  │
  └──────────────┘                     └──────────────────┘
  ┌──────────────┐    TCP 66B         ┌──────────────────┐
  │  信号屏 MMI   │ ←───────────────── │  pack_* / parse_*│
  │  :9999       │                    │                  │
  └──────────────┘                     └──────────────────┘
                                              │
                                    UDP 信号系统协议
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │  信号系统/总控节点  │
                                     │  (192.168.100.x)  │
                                     └──────────────────┘
```

### 核心模块职责

- **`config.py`**：集中管理所有 IP/端口/超时参数、位定义（ATP安全输入/输出、ATO非安全输入/输出）、驾驶模式枚举、信号机/道岔状态枚举
- **`protocols.py`**：所有协议的打包（pack_*）与解析（parse_*）函数，以及 ATP 位编解码辅助函数。含 `self_test()` 自检入口
- **`plc_simulator.py`**：`PlcSimulator` 类，TCP Server 模拟 PLC，支持交互式控制台调整所有模拟状态
- **`listen_plc.py`**：纯接收客户端，连接 PLC 接收 46 字节报文，完整解析并格式化显示

### 编解码函数命名约定

- `pack_*`：将 Python 对象打包为字节流（编码）
- `parse_*`：将字节流解析为 Python 字典（解码）
- `encode_*`：将位字典编码为 UINT32 整数值
- `_decode_bits` / `_encode_bits`：内部辅助，按位图字典编解码

## 开发注意事项

1. **协议一致性**：所有协议定义以 `docs/轨交多系统平台接口协议汇总20260630.md` 为准，发现不一致时提醒开发者向组长报告，不得自行修改
2. **字节序**：PLC 协议报文头为大端序，但 WORD 内部存储为小端（三菱 PLC 特性），`protocols.py` 已正确处理
3. **独立模块**：`driver_cab_test` 与 `backend/sim_engine` 完全独立，无依赖关系
4. **模拟 vs 生产**：通过 `--local` 参数或 `config.py` 中 `USE_REAL_HARDWARE` 控制连接目标
5. **无测试文件**：目前无独立测试文件，验证通过 `protocols.py` 的 `self_test()` 自检完成