import io
import json
import runpy
from pathlib import Path
from typing import Any

import pytest

from junction_sim.cli import main
from junction_sim.cli.commands import instantiate_controller
from junction_sim.cli.parser import create_parser
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.exceptions import ConfigurationError


def create_scenario_file(path: Path) -> Path:
    data: dict[str, Any] = {
        "intersection": {
            "id": "cli_int",
            "approaches": [
                {
                    "id": "north",
                    "direction": "north",
                    "lanes": [
                        {
                            "id": "lane_n_0",
                            "approach_id": "north",
                            "allowed_movement_ids": ["N_T"],
                            "max_capacity": 50,
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
                            "max_capacity": 50,
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
            "id": "cli_plan",
            "phases": [
                {
                    "id": "P1",
                    "green_movement_ids": ["N_T"],
                    "green_duration": 15.0,
                    "yellow_duration": 3.0,
                    "all_red_duration": 1.0,
                    "min_green": 5.0,
                    "max_green": 30.0,
                },
                {
                    "id": "P2",
                    "green_movement_ids": ["S_T"],
                    "green_duration": 15.0,
                    "yellow_duration": 3.0,
                    "all_red_duration": 1.0,
                    "min_green": 5.0,
                    "max_green": 30.0,
                },
            ],
        },
        "demands": [
            {"movement_id": "N_T", "flow_rate_vph": 400.0},
            {"movement_id": "S_T", "flow_rate_vph": 200.0},
        ],
        "simulation": {
            "duration": 40.0,
            "step_size": 1.0,
            "seed": 42,
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_cli_parser_help_and_version() -> None:
    parser = create_parser()
    assert parser.prog == "junction-sim"

    stdout = io.StringIO()
    stderr = io.StringIO()
    ret = main([], stdout=stdout, stderr=stderr)
    assert ret == 0
    assert "Available simulation subcommands" in stdout.getvalue()

    ret_version = main(["--version"], stdout=stdout, stderr=stderr)
    assert ret_version == 0


def test_cli_run_fixed_time(tmp_path: Path) -> None:
    cfg_file = create_scenario_file(tmp_path / "scenario.json")
    stdout = io.StringIO()
    stderr = io.StringIO()

    ret = main(["run", "-c", str(cfg_file)], stdout=stdout, stderr=stderr)
    assert ret == 0
    output = stdout.getvalue()
    assert "Simulation Execution Summary" in output
    assert "Controller:      fixed-time" in output
    assert "Duration:        40.0 s" in output
    assert "Total Arrivals:" in output
    assert "Total Served:" in output


def test_cli_run_actuated_and_max_pressure_with_exports(tmp_path: Path) -> None:
    cfg_file = create_scenario_file(tmp_path / "scenario.json")
    csv_file = tmp_path / "results.csv"
    json_file = tmp_path / "results.json"

    stdout = io.StringIO()
    stderr = io.StringIO()

    ret_act = main(
        [
            "run",
            "-c",
            str(cfg_file),
            "--controller",
            "actuated",
            "--duration",
            "20.0",
            "--seed",
            "123",
            "--out-csv",
            str(csv_file),
            "--out-json",
            str(json_file),
        ],
        stdout=stdout,
        stderr=stderr,
    )
    assert ret_act == 0
    assert csv_file.exists()
    assert json_file.exists()
    assert "Exported CSV:" in stdout.getvalue()
    assert "Exported JSON:" in stdout.getvalue()

    stdout_mp = io.StringIO()
    stderr_mp = io.StringIO()
    ret_mp = main(
        ["run", "-c", str(cfg_file), "--controller", "max-pressure"],
        stdout=stdout_mp,
        stderr=stderr_mp,
    )
    assert ret_mp == 0
    assert "Controller:      max-pressure" in stdout_mp.getvalue()


def test_cli_benchmark_command_with_and_without_exports(tmp_path: Path) -> None:
    cfg_file = create_scenario_file(tmp_path / "scenario.json")
    csv_file = tmp_path / "bench.csv"
    json_file = tmp_path / "bench.json"

    stdout = io.StringIO()
    stderr = io.StringIO()

    ret = main(
        [
            "benchmark",
            "-c",
            str(cfg_file),
            "--controllers",
            "fixed-time,actuated,max-pressure",
            "--duration",
            "30.0",
            "--seed",
            "77",
            "--out-csv",
            str(csv_file),
            "--out-json",
            str(json_file),
        ],
        stdout=stdout,
        stderr=stderr,
    )
    assert ret == 0
    assert csv_file.exists()
    assert json_file.exists()

    output = stdout.getvalue()
    assert "Signal Controller Benchmark Results" in output
    assert "fixed-time" in output
    assert "actuated" in output
    assert "max-pressure" in output
    assert "Best by Delay:" in output
    assert "Best by Throughput:" in output

    stdout_no_export = io.StringIO()
    ret_no_export = main(
        ["benchmark", "-c", str(cfg_file), "--controllers", "fixed-time,actuated"],
        stdout=stdout_no_export,
        stderr=stderr,
    )
    assert ret_no_export == 0
    assert "Signal Controller Benchmark Results" in stdout_no_export.getvalue()


def test_cli_error_handling(tmp_path: Path) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    ret = main(
        ["run", "-c", str(tmp_path / "missing.json")], stdout=stdout, stderr=stderr
    )
    assert ret == 1
    assert "Error:" in stderr.getvalue()

    cfg_file = create_scenario_file(tmp_path / "scenario.json")
    stdout_b = io.StringIO()
    stderr_b = io.StringIO()
    ret_b = main(
        ["benchmark", "-c", str(cfg_file), "--controllers", ""],
        stdout=stdout_b,
        stderr=stderr_b,
    )
    assert ret_b == 1
    assert "Error:" in stderr_b.getvalue()


def test_instantiate_controller_guard() -> None:
    mov1 = Movement(
        id="M1",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov2 = Movement(
        id="M2",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    lane1 = Lane(id="L1", approach_id="north", allowed_movement_ids=("M1",))
    lane2 = Lane(id="L2", approach_id="south", allowed_movement_ids=("M2",))
    app1 = Approach(id="north", direction=Direction.NORTH, lanes=(lane1,))
    app2 = Approach(id="south", direction=Direction.SOUTH, lanes=(lane2,))
    inter = Intersection(
        id="I1",
        approaches=(app1, app2),
        movements=(mov1, mov2),
        conflicting_movement_pairs=frozenset(),
    )
    p1 = SignalPhase(id="P1", green_movement_ids=("M1",), green_duration=10.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("M2",), green_duration=10.0)
    plan = SignalPlan(id="SP1", phases=(p1, p2))

    with pytest.raises(ConfigurationError):
        instantiate_controller("unsupported_ctrl", plan, inter)


def test_cli_main_module_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["junction-sim", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("junction_sim.__main__", run_name="__main__")
    assert exc_info.value.code == 0


def test_cli_run_with_dashboard(tmp_path: Path) -> None:
    cfg_file = create_scenario_file(tmp_path / "scenario.json")
    stdout = io.StringIO()
    stderr = io.StringIO()

    ret = main(
        ["run", "-c", str(cfg_file), "--dashboard", "-d", "10.0"],
        stdout=stdout,
        stderr=stderr,
    )
    assert ret == 0
    val = stdout.getvalue()
    assert "QUEUE LENGTHS:" in val
    assert "INTERSECTION LAYOUT:" in val


def test_cli_run_with_preset() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    ret = main(
        ["run", "-p", "webster_four_way", "-d", "5.0"],
        stdout=stdout,
        stderr=stderr,
    )
    assert ret == 0
    val = stdout.getvalue()
    assert "Simulation Execution Summary" in val
    assert "Controller:      fixed-time" in val


def test_cli_benchmark_with_preset() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    ret = main(
        [
            "benchmark",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "--controllers",
            "fixed-time,actuated",
        ],
        stdout=stdout,
        stderr=stderr,
    )
    assert ret == 0
    val = stdout.getvalue()
    assert "Signal Controller Benchmark Results" in val
    assert "fixed-time" in val
    assert "actuated" in val


def test_cli_presets_list_and_bare() -> None:
    stdout_list = io.StringIO()
    ret_list = main(["presets", "list"], stdout=stdout_list)
    assert ret_list == 0
    assert "Available Scenario Presets" in stdout_list.getvalue()
    assert "webster_four_way" in stdout_list.getvalue()

    stdout_bare = io.StringIO()
    ret_bare = main(["presets"], stdout=stdout_bare)
    assert ret_bare == 0
    assert "Available Scenario Presets" in stdout_bare.getvalue()


def test_cli_presets_export(tmp_path: Path) -> None:
    export_path = tmp_path / "subdir" / "exported_webster.json"
    stdout = io.StringIO()
    ret = main(
        ["presets", "export", "-p", "webster_four_way", "-o", str(export_path)],
        stdout=stdout,
    )
    assert ret == 0
    assert export_path.exists()
    assert "Exported preset 'webster_four_way'" in stdout.getvalue()

    stdout_run = io.StringIO()
    ret_run = main(
        ["run", "-c", str(export_path), "-d", "5.0"],
        stdout=stdout_run,
    )
    assert ret_run == 0
    assert "Simulation Execution Summary" in stdout_run.getvalue()
