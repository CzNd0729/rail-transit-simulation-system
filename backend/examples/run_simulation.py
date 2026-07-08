"""运行 MVP 单列车仿真（CLI 演示，无需 WebSocket）。

用法（在 backend 目录下）::

    python examples/run_simulation.py
    python examples/run_simulation.py --steps 500 --csv out/run.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 保证从 backend/ 运行时能 import sim_engine
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim_engine.orchestrator import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="MVP 单列车仿真演示")
    parser.add_argument("--steps", type=int, default=None, help="最大步数（默认跑到终点）")
    parser.add_argument("--csv", type=str, default="", help="导出 CSV 路径")
    parser.add_argument("--print-every", type=int, default=50, help="每 N 步打印一次状态")
    args = parser.parse_args()

    orch = Orchestrator.from_config_dir()
    orch.reset(passenger_load=0.6)
    orch.start()

    step = 0
    while orch.run_state.value == "running":
        snap = orch.step_once()
        step += 1
        if args.print_every and step % args.print_every == 0 and snap:
            t = snap["data"]["trains"][0]
            print(
                f"t={snap['timestamp']:.1f}s "
                f"x={t['position']:.1f}m v={t['speed']:.1f}km/h "
                f"mode={t['mode']}"
            )
        if orch.clock.elapsed >= orch.sim_params.total_time:
            orch.stop()
            break
        if (
            orch.train_state
            and orch.train_state.position >= orch.track.track.total_length - 1.0
            and orch.train_state.speed < 0.1
        ):
            orch.stop()
            break
        if args.steps and step >= args.steps:
            orch.pause()
            break

    summary = orch.recorder.summary()
    print("--- 仿真结束 ---")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.csv:
        orch.recorder.export_csv(args.csv)
        print(f"CSV 已写入: {args.csv}")


if __name__ == "__main__":
    main()
