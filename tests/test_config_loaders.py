import json
from pathlib import Path
from typing import Any

import pytest

from junction_sim.config.loader import (
    load_scenario_from_dict,
    load_scenario_from_file,
    load_scenario_from_json,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.signal import SignalPlan
from junction_sim.exceptions import ConfigurationError


def create_sample_scenario_dict() -> dict[str, Any]:
    return {
        "intersection": {
            "id": "cfg_int",
            "approaches": [
                {
                    "id": "north",
                    "direction": "north",
                    "lanes": [
                        {
                            "id": "lane_n_0",
                            "approach_id": "north",
                            "allowed_movement_ids": ["N_T"],
                            "max_capacity": 60,
                        }
                    ],
                },
                {
                    "id": "south",
                    "direction": "south",
                    "lanes": [
                        {
                            "id": "lane_s_0",
                            "approach_id": "south",
                            "allowed_movement_ids": ["S_T"],
                            "max_capacity": 60,
                        }
                    ],
                },
            ],
            "movements": [
                {
                    "id": "N_T",
                    "origin": "north",
                    "destination": "south",
                    "turn_type": "through",
                    "saturation_flow_rate": 1800.0,
                },
                {
                    "id": "S_T",
                    "origin": "south",
                    "destination": "north",
                    "turn_type": "through",
                    "saturation_flow_rate": 1800.0,
                },
            ],
            "conflicting_movement_pairs": [],
        },
        "signal_plan": {
            "id": "cfg_plan",
            "phases": [
                {
                    "id": "P1",
                    "green_movement_ids": ["N_T"],
                    "green_duration": 20.0,
                    "yellow_duration": 3.0,
                    "all_red_duration": 1.0,
                    "min_green": 5.0,
                    "max_green": 30.0,
                },
                {
                    "id": "P2",
                    "green_movement_ids": ["S_T"],
                    "green_duration": 20.0,
                    "yellow_duration": 3.0,
                    "all_red_duration": 1.0,
                    "min_green": 5.0,
                    "max_green": 30.0,
                },
            ],
        },
        "demands": [
            {"movement_id": "N_T", "flow_rate_vph": 500.0},
            {"movement_id": "S_T", "flow_rate_vph": 400.0},
        ],
        "simulation": {
            "duration": 120.0,
            "step_size": 0.5,
            "seed": 99,
        },
    }


def test_load_scenario_from_dict_and_build() -> None:
    data = create_sample_scenario_dict()
    scenario = load_scenario_from_dict(data)

    inter, plan, demands, sim_cfg = scenario.build_scenario()

    assert isinstance(inter, Intersection)
    assert isinstance(plan, SignalPlan)
    assert len(inter.approaches) == 2
    assert len(inter.movements) == 2
    assert len(plan.phases) == 2
    assert len(demands) == 2
    assert demands[0].movement_id == "N_T"
    assert demands[0].flow_rate_vph == 500.0
    assert sim_cfg.duration == 120.0
    assert sim_cfg.step_size == 0.5
    assert sim_cfg.seed == 99


def test_load_scenario_from_json_string() -> None:
    data = create_sample_scenario_dict()
    json_str = json.dumps(data)

    scenario = load_scenario_from_json(json_str)
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    assert inter.id == "cfg_int"
    assert plan.id == "cfg_plan"
    assert len(demands) == 2
    assert sim_cfg.duration == 120.0


def test_load_scenario_from_file(tmp_path: Path) -> None:
    data = create_sample_scenario_dict()
    file_path = tmp_path / "scenario.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    scenario = load_scenario_from_file(file_path)
    inter, plan, demands, sim_cfg = scenario.build_scenario()

    assert inter.id == "cfg_int"
    assert plan.id == "cfg_plan"
    assert sim_cfg.duration == 120.0


def test_load_scenario_invalid_inputs_and_syntax(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(["not", "a", "dict"])  # type: ignore[arg-type]

    with pytest.raises(ConfigurationError):
        load_scenario_from_json("{invalid_json: 123")

    with pytest.raises(ConfigurationError):
        load_scenario_from_file(tmp_path / "non_existent.json")


def test_load_scenario_schema_validation_errors() -> None:
    data_missing = create_sample_scenario_dict()
    del data_missing["intersection"]
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_missing)

    data_direction = create_sample_scenario_dict()
    data_direction["intersection"]["approaches"][0]["direction"] = "northwest"
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_direction)

    data_turn = create_sample_scenario_dict()
    data_turn["intersection"]["movements"][0]["turn_type"] = "invalid_turn"
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_turn)

    data_sat = create_sample_scenario_dict()
    data_sat["intersection"]["movements"][0]["saturation_flow_rate"] = -100.0
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_sat)

    data_phases = create_sample_scenario_dict()
    data_phases["signal_plan"]["phases"] = [data_phases["signal_plan"]["phases"][0]]
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_phases)

    data_demand = create_sample_scenario_dict()
    data_demand["demands"][0]["flow_rate_vph"] = -50.0
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_demand)

    data_duration = create_sample_scenario_dict()
    data_duration["simulation"]["duration"] = 0.0
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_duration)

    data_extra = create_sample_scenario_dict()
    data_extra["extra_forbidden_key"] = 123
    with pytest.raises(ConfigurationError):
        load_scenario_from_dict(data_extra)


def test_load_scenario_cross_model_validation_errors() -> None:
    data_mismatch_phase = create_sample_scenario_dict()
    data_mismatch_phase["signal_plan"]["phases"][0]["green_movement_ids"] = [
        "UNKNOWN_MOV"
    ]
    scenario = load_scenario_from_dict(data_mismatch_phase)
    with pytest.raises(ConfigurationError):
        scenario.build_scenario()

    data_mismatch_demand = create_sample_scenario_dict()
    data_mismatch_demand["demands"][0]["movement_id"] = "UNKNOWN_DEMAND_MOV"
    scenario_dem = load_scenario_from_dict(data_mismatch_demand)
    with pytest.raises(ConfigurationError):
        scenario_dem.build_scenario()
