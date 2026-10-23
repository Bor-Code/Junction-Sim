import io
from pathlib import Path

from junction_sim.cli import main
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import SignalState
from junction_sim.visualization.blender_exporter import (
    export_blender_script,
    generate_blender_script,
)


def create_blender_test_intersection() -> tuple[Intersection, SignalPlan]:
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
        id="test_junction_blender",
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
    plan = SignalPlan(id="plan_sample_blender", phases=phases)
    return intersection, plan


def test_generate_blender_script_empty() -> None:
    intersection, plan = create_blender_test_intersection()
    script = generate_blender_script(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        controller_name="fixed-time",
        scenario_name="empty_test",
        seed=42,
    )
    compiled = compile(script, "<blender_test_empty>", "exec")
    assert compiled is not None
    assert "import bpy" in script
    assert "SIM_DATA" in script
    assert "Mat_Asphalt" in script
    assert "CinematicCam" in script

    scope: dict[str, object] = {}
    exec(compiled, scope)
    assert "run_blender_setup" in scope
    fn = scope["run_blender_setup"]
    assert callable(fn)
    fn()


def test_generate_blender_script_with_vehicles() -> None:
    intersection, plan = create_blender_test_intersection()
    v1 = Vehicle(
        id="car_blender",
        origin="north",
        destination="south",
        arrival_time=0.5,
    )
    v1_dis = Vehicle(
        id="car_blender",
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

    script = generate_blender_script(
        results=[step0, step1],
        intersection=intersection,
        signal_plan=plan,
        controller_name="actuated",
        scenario_name="blender_full",
        seed=99,
        fps=30,
        substep_dt=0.5,
    )
    compiled = compile(script, "<blender_test_full>", "exec")
    assert compiled is not None
    assert "car_blender" in script
    assert "keyframe_insert" in script
    assert "FPS = 30" in script


def test_export_blender_script_to_file(tmp_path: Path) -> None:
    intersection, plan = create_blender_test_intersection()
    dest = tmp_path / "blender_out" / "scene_setup.py"
    export_blender_script(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=dest,
    )
    assert dest.exists()
    content = dest.read_text(encoding="utf-8")
    compiled = compile(content, "<file_test>", "exec")
    assert compiled is not None


def test_export_blender_script_to_stream() -> None:
    intersection, plan = create_blender_test_intersection()
    stream = io.StringIO()
    export_blender_script(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=stream,
    )
    output = stream.getvalue()
    assert "run_blender_setup" in output


def test_cli_export_blender_command(tmp_path: Path) -> None:
    out_script = tmp_path / "blender_cli_export.py"
    stdout = io.StringIO()
    ret = main(
        [
            "export-blender",
            "-p",
            "webster_four_way",
            "--controller",
            "actuated",
            "-d",
            "10.0",
            "--fps",
            "30",
            "-o",
            str(out_script),
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert out_script.exists()
    content = out_script.read_text(encoding="utf-8")
    assert "FPS = 30" in content
    assert compile(content, "<cli_blender>", "exec") is not None
    assert "Blender Scene Script Generated Successfully" in stdout.getvalue()


def test_cli_run_export_blender_option(tmp_path: Path) -> None:
    out_script = tmp_path / "run_blender.py"
    stdout = io.StringIO()
    ret = main(
        [
            "run",
            "-p",
            "webster_four_way",
            "--controller",
            "fixed-time",
            "-d",
            "5.0",
            "--export-blender",
            str(out_script),
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert out_script.exists()
    assert "Exported Blender:" in stdout.getvalue()
