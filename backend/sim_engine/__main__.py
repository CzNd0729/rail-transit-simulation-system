"""CLI 入口 — 启动仿真引擎后端服务。

**已弃用 --external 参数**：外部系统接入方案已废弃，后端默认直接对接前端。
`--external` 参数保留仅作兼容，未来版本将移除。

用法:
  python -m sim_engine                          # 常规后端（对接前端）
  # python -m sim_engine --external             # 已弃用
  python -m sim_engine --host 0.0.0.0 --port 8000
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


def main():
    parser = argparse.ArgumentParser(
        description="城市轨道交通运行仿真系统 — 后端服务",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="[已弃用] 启用外部系统连接模式 — 外部系统接入方案已废弃，前端对接无需此参数",
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

    if args.external:
        import warnings
        warnings.warn(
            "--external 参数已弃用：外部系统接入方案已废弃，后端默认直接对接前端。",
            DeprecationWarning,
            stacklevel=2,
        )
        print("=" * 60)
        print("  [已弃用] 外部系统模式已启用")
        print(f"  PLC:      192.168.100.123:8001")
        print(f"  网络屏:    192.168.100.121:8888")
        print(f"  信号屏:    192.168.100.122:9999")
        print(f"  UDP 总控: 192.168.200.110:23001 → 192.168.200.102:23002")
        print("  注意: 此模式已弃用，请使用默认模式（无 --external）对接前端")
        print("=" * 60)
    else:
        print("常规模式 — 仅提供 REST API + WebSocket 对接前端")

    # 通过环境变量传递 external_mode 给 app.py
    os.environ["SIM_ENGINE_EXTERNAL"] = "1" if args.external else "0"

    uvicorn.run(
        "sim_engine.app:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()