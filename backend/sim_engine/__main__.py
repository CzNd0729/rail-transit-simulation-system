"""CLI 入口 — 启动仿真引擎后端服务。

用法:
  python -m sim_engine                          # 常规后端（对接前端）
  python -m sim_engine --external               # 连接外部系统（PLC/网络屏/信号屏）
  python -m sim_engine --external --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# 将 backend 目录加入 sys.path，确保 import sim_engine 正常工作
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import uvicorn


def _configure_logging(level: str) -> None:
    """配置 root logger，让所有桥接等模块的日志也输出到控制台。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_banner(args: argparse.Namespace) -> None:
    """打印启动横幅（服务地址、外部设备目标等）。"""
    bind_addr = f"{args.host}:{args.port}"
    if args.external:
        print("=" * 60)
        print("  外部系统模式已启用")
        print(f"  ─────────────────────────────────────────")
        print(f"  本机服务         {bind_addr}")
        print(f"  WebSocket 端点   ws://{bind_addr}/ws")
        print(f"  API 文档         http://{bind_addr}/docs")
        print(f"  ─────────────────────────────────────────")
        print(f"  PLC:            192.168.100.123:8001")
        print(f"  网络屏 (HMI):   192.168.100.121:8888")
        print(f"  信号屏 (MMI):   192.168.100.122:9999")
        print(f"  UDP 总控:       192.168.200.110:23001 → 192.168.200.102:23002")
        print("=" * 60)
    else:
        print("=" * 60)
        print(f"  常规模式 — 仅提供 REST API + WebSocket 对接前端")
        print(f"  本机服务: {bind_addr}")
        print(f"  API 文档: http://{bind_addr}/docs")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="城市轨道交通运行仿真系统 — 后端服务",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="启用外部系统连接模式（连接真实 PLC/网络屏/信号屏硬件）",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="绑定地址（默认 127.0.0.1）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="监听端口（默认 8000）",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别（默认 info）",
    )

    args = parser.parse_args()

    # 配置 Python logging，确保桥接等模块的日志也输出到控制台
    _configure_logging(args.log_level)
    # 打印启动横幅
    _print_banner(args)

    # 通过环境变量传递 external_mode / host / port 给 app.py
    os.environ["SIM_ENGINE_EXTERNAL"] = "1" if args.external else "0"
    os.environ["SIM_ENGINE_HOST"] = args.host
    os.environ["SIM_ENGINE_PORT"] = str(args.port)

    uvicorn.run(
        "sim_engine.app:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()