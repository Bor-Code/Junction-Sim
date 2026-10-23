import io
from pathlib import Path

from junction_sim.cli.commands import handle_run, handle_visualize
from junction_sim.cli.parser import create_parser
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import SignalState
from junction_sim.visualization.threejs_visualizer import (
    export_3d_html_visualizer,
    generate_3d_html_visualizer,
)


def create_sample_intersection() -> tuple[Intersection, SignalPlan]:
    movements = (
        Movement(
            id="N_T",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="S_T",
            origin="south",
            destination="north",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
    )
    approaches = (
        Approach(
            id="north",
            direction=Direction.NORTH,
            lanes=(
                Lane(
                    id="ln_n0",
                    approach_id="north",
                    allowed_movement_ids=("N_T",),
                ),
            ),
        ),
        Approach(
            id="south",
            direction=Direction.SOUTH,
            lanes=(
                Lane(
                    id="ln_s0",
                    approach_id="south",
                    allowed_movement_ids=("S_T",),
                ),
            ),
        ),
    )
    intersection = Intersection(
        id="test_junction",
        approaches=approaches,
        movements=movements,
    )
    phases = (
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=20.0,
            min_green=5.0,
            max_green=30.0,
        ),
        SignalPhase(
            id="P2",
            green_movement_ids=("S_T",),
            green_duration=15.0,
            min_green=5.0,
            max_green=25.0,
        ),
    )
    plan = SignalPlan(id="plan_sample", phases=phases)
    return intersection, plan


def test_generate_3d_html_visualizer_empty() -> None:
    intersection, plan = create_sample_intersection()
    html = generate_3d_html_visualizer(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        controller_name="fixed-time",
        scenario_name="test_scenario",
        seed=42,
    )
    assert "<!DOCTYPE html>" in html
    assert '<canvas id="webgl-canvas"></canvas>' in html
    assert "OrbitControls.js" in html
    assert "three.min.js" in html
    assert "SIM_DATA" in html
    assert "test_scenario" in html


def test_generate_3d_html_visualizer_with_trajectories() -> None:
    intersection, plan = create_sample_intersection()
    v1 = Vehicle(id="car_10", origin="north", destination="south", arrival_time=0.5)
    v1_dis = Vehicle(
        id="car_10",
        origin="north",
        destination="south",
        arrival_time=0.5,
        departure_time=2.0,
    )
    step0 = StepResult(
        step_index=0,
        time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(v1,),
        discharged_vehicles=(),
        queue_lengths={"ln_n0": 1},
    )
    step1 = StepResult(
        step_index=1,
        time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(),
        discharged_vehicles=(v1_dis,),
        queue_lengths={"ln_n0": 0},
    )

    html = generate_3d_html_visualizer(
        results=[step0, step1],
        intersection=intersection,
        signal_plan=plan,
        controller_name="actuated",
        scenario_name="webster_test",
        seed=101,
        step_size=1.0,
        substep_dt=0.5,
    )
    assert "car_10" in html
    assert "trajectories" in html
    assert "hud-active-veh" in html
    assert "hud-served-veh" in html
    assert "cam-modes" in html
    assert "lighting-modes" in html
    assert "inspector-card" in html


def test_export_3d_html_visualizer_to_file(tmp_path: Path) -> None:
    intersection, plan = create_sample_intersection()
    dest = tmp_path / "deep" / "nested" / "sim_3d.html"
    export_3d_html_visualizer(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=dest,
    )
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content


def test_export_3d_html_visualizer_to_stream() -> None:
    intersection, plan = create_sample_intersection()
    stream = io.StringIO()
    export_3d_html_visualizer(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=stream,
    )
    output = stream.getvalue()
    assert "<!DOCTYPE html>" in output
    assert "webgl-canvas" in output


def test_cli_visualize_3d_default(tmp_path: Path) -> None:
    out_file = tmp_path / "vis_3d.html"
    parser = create_parser()
    args = parser.parse_args(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "--controller",
            "fixed-time",
            "-d",
            "5.0",
            "-o",
            str(out_file),
        ]
    )
    stdout = io.StringIO()
    ret = handle_visualize(args, stdout=stdout)
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "webgl-canvas" in content
    assert "3D Photorealistic WebGL" in stdout.getvalue()


def test_cli_visualize_2d_mode(tmp_path: Path) -> None:
    out_file = tmp_path / "vis_2d.html"
    parser = create_parser()
    args = parser.parse_args(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "--controller",
            "fixed-time",
            "--mode",
            "2d",
            "-d",
            "5.0",
            "-o",
            str(out_file),
        ]
    )
    stdout = io.StringIO()
    ret = handle_visualize(args, stdout=stdout)
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "2D Interactive Canvas" in stdout.getvalue()
    assert "Junction-Sim Interactive Visualizer" in content


def test_cli_visualize_explicit_3d_flag(tmp_path: Path) -> None:
    out_file = tmp_path / "vis_flag.html"
    parser = create_parser()
    args = parser.parse_args(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "--controller",
            "fixed-time",
            "--3d",
            "--mode",
            "2d",
            "-d",
            "5.0",
            "-o",
            str(out_file),
        ]
    )
    stdout = io.StringIO()
    ret = handle_visualize(args, stdout=stdout)
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "webgl-canvas" in content
    assert "3D Photorealistic WebGL" in stdout.getvalue()


def test_cli_run_out_html_3d(tmp_path: Path) -> None:
    out_3d = tmp_path / "run_out_3d.html"
    parser = create_parser()
    args = parser.parse_args(
        [
            "run",
            "-p",
            "webster_four_way",
            "--controller",
            "fixed-time",
            "-d",
            "5.0",
            "--out-html-3d",
            str(out_3d),
        ]
    )
    stdout = io.StringIO()
    ret = handle_run(args, stdout=stdout)
    assert ret == 0
    assert out_3d.exists()
    content = out_3d.read_text(encoding="utf-8")
    assert "webgl-canvas" in content
    assert "Exported 3D HTML:" in stdout.getvalue()
