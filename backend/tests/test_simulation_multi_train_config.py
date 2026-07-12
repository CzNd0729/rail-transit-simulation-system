"""多车仿真配置加载测试。"""

from __future__ import annotations

from sim_engine.core.config import SimulationParams, load_simulation_params


def test_simulation_params_defaults():
    p = SimulationParams()
    assert p.train_count == 1
    assert p.departure_interval == 120.0


def test_load_train_count_from_yaml(tmp_path):
    yaml_text = """
simulation:
  train_count: 3
  departure_interval: 90.0
  time_step: 0.1
"""
    p = tmp_path / "simulation.yaml"
    p.write_text(yaml_text, encoding="utf-8")
    params = load_simulation_params(p)
    assert params.train_count == 3
    assert params.departure_interval == 90.0
