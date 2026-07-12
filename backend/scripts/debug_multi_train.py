"""Verify multi-train simulation after timetable offset fix."""
from sim_engine.orchestrator import Orchestrator


def main() -> None:
    orch = Orchestrator.from_config_dir()
    orch.sim_params.train_count = 3
    orch.reset()
    orch.start()
    for _ in range(80000):
        if orch.step_once() is None:
            break
    for tr in orch.trains:
        print(f"{tr.train_id} pos={tr.state.position:.1f} spd={tr.state.speed:.2f}")


if __name__ == "__main__":
    main()
