import io
from pathlib import Path
from typing import Any

import pytest

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
    compile_blender_scene,
    export_blender_script,
    find_blender_executable,
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
        blend_destination="test.blend",
    )
    compiled = compile(script, "<blender_test_full>", "exec")
    assert compiled is not None
    assert "car_blender" in script
    assert "keyframe_insert" in script
    assert "FPS = 30" in script
    assert 'DEFAULT_BLEND_PATH = "test.blend"' in script


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


def test_find_blender_executable_shutil(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: "/usr/bin/blender")
    assert find_blender_executable() == "/usr/bin/blender"


def test_find_blender_executable_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "darwin"
    )
    mac_path = "/Applications/Blender.app/Contents/MacOS/Blender"
    monkeypatch.setattr(Path, "is_file", lambda self: self.as_posix() == mac_path)
    assert find_blender_executable() == str(Path(mac_path))


def test_find_blender_executable_darwin_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "darwin"
    )
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    assert find_blender_executable() is None


def test_find_blender_executable_win32_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "win32"
    )
    cand = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == cand)
    assert find_blender_executable() == cand


def test_find_blender_executable_win32_second_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "win32"
    )
    cand2 = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
    monkeypatch.setattr(Path, "is_file", lambda self: str(self) == cand2)
    assert find_blender_executable() == cand2


def test_find_blender_executable_win32_glob(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "win32"
    )
    fake_dir = tmp_path / "dummy_dir"
    fake_exe = tmp_path / "blender.exe"
    fake_exe.touch()
    monkeypatch.setattr(Path, "is_file", lambda self: self == fake_exe)
    monkeypatch.setattr(Path, "is_dir", lambda self: True)
    monkeypatch.setattr(Path, "glob", lambda self, _pat: [fake_dir, fake_exe])
    assert find_blender_executable() == str(fake_exe)


def test_find_blender_executable_win32_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "win32"
    )
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setattr(Path, "is_dir", lambda self: False)
    assert find_blender_executable() is None


def test_find_blender_executable_win32_glob_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "win32"
    )
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setattr(Path, "is_dir", lambda self: True)
    monkeypatch.setattr(Path, "glob", lambda self, _pat: [])
    assert find_blender_executable() is None


def test_find_blender_executable_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.sys.platform", "linux"
    )
    assert find_blender_executable() is None


def test_compile_blender_scene_missing_binary(tmp_path: Path) -> None:
    script = tmp_path / "s.py"
    script.touch()
    assert (
        compile_blender_scene(script, tmp_path / "out.blend", blender_bin="/no/bin")
        is False
    )


def test_compile_blender_scene_subprocess(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "s.py"
    script.touch()
    blend = tmp_path / "out.blend"
    fake_bin = tmp_path / "blender.exe"
    fake_bin.touch()

    class DummyRes:
        returncode = 0

    def fake_run(*args: Any, **kwargs: Any) -> DummyRes:
        blend.touch()
        return DummyRes()

    monkeypatch.setattr("subprocess.run", fake_run)
    assert compile_blender_scene(script, blend, blender_bin=str(fake_bin)) is True


def test_compile_blender_scene_subprocess_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    script = tmp_path / "s.py"
    script.touch()
    blend = tmp_path / "out.blend"
    fake_bin = tmp_path / "blender.exe"
    fake_bin.touch()

    class DummyFail:
        returncode = 1

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: DummyFail())
    assert compile_blender_scene(script, blend, blender_bin=str(fake_bin)) is False


def test_export_blender_script_with_compilation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    intersection, plan = create_blender_test_intersection()
    dest = tmp_path / "scene.py"
    blend = tmp_path / "scene.blend"
    compiled = False

    def fake_compile(s: Any, b: Any) -> bool:
        nonlocal compiled
        compiled = True
        return True

    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.compile_blender_scene",
        fake_compile,
    )
    export_blender_script(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=dest,
        blend_destination=blend,
    )
    assert dest.exists()
    assert compiled is True


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


def test_cli_export_blender_with_blend_and_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out_script = tmp_path / "blender_cli_export.py"
    out_blend = tmp_path / "blender_cli_export.blend"
    out_blend.touch()
    opened = False

    def fake_popen(*args: Any, **kwargs: Any) -> None:
        nonlocal opened
        opened = True

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr(
        "junction_sim.cli.commands.find_blender_executable",
        lambda: "fake_blender",
    )
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.compile_blender_scene",
        lambda s, b: True,
    )

    stdout = io.StringIO()
    ret = main(
        [
            "export-blender",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "-o",
            str(out_script),
            "--blend",
            str(out_blend),
            "--open",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Compiled Blend:" in stdout.getvalue()
    assert "Opened scene in Blender:" in stdout.getvalue()
    assert opened is True


def test_cli_export_blender_with_blend_no_open(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out_script = tmp_path / "blender_cli_export.py"
    out_blend = tmp_path / "blender_cli_export.blend"
    out_blend.touch()
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.compile_blender_scene",
        lambda s, b: True,
    )

    stdout = io.StringIO()
    ret = main(
        [
            "export-blender",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "-o",
            str(out_script),
            "--blend",
            str(out_blend),
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Compiled Blend:" in stdout.getvalue()


def test_cli_export_blender_open_default_blend_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out_script = tmp_path / "b_fail.py"
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.compile_blender_scene",
        lambda s, b: False,
    )
    stdout = io.StringIO()
    ret = main(
        [
            "export-blender",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "-o",
            str(out_script),
            "--open",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Warning: Failed to compile blend file" in stdout.getvalue()


def test_cli_export_blender_open_no_binary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    out_script = tmp_path / "b_nobin.py"
    out_blend = tmp_path / "b_nobin.blend"
    out_blend.touch()
    monkeypatch.setattr(
        "junction_sim.visualization.blender_exporter.compile_blender_scene",
        lambda s, b: True,
    )
    monkeypatch.setattr(
        "junction_sim.cli.commands.find_blender_executable",
        lambda: None,
    )
    stdout = io.StringIO()
    ret = main(
        [
            "export-blender",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "-o",
            str(out_script),
            "--blend",
            str(out_blend),
            "--open",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Blender executable not found to open GUI" in stdout.getvalue()


def test_cli_visualize_blender_option(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    opened = False

    def fake_popen(*args: Any, **kwargs: Any) -> None:
        nonlocal opened
        opened = True

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr(
        "junction_sim.cli.commands.find_blender_executable",
        lambda: "fake_blender",
    )

    def fake_export(*args: Any, **kwargs: Any) -> None:
        Path("junction_simulation.blend").touch()

    monkeypatch.setattr("junction_sim.cli.commands.export_blender_script", fake_export)
    stdout = io.StringIO()
    ret = main(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "--blender",
            "--open",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Blender 3D Simulation Generated Successfully" in stdout.getvalue()
    assert opened is True
    Path("junction_simulation.blend").unlink(missing_ok=True)
    Path("junction_scene.py").unlink(missing_ok=True)


def test_cli_visualize_blender_no_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "junction_sim.cli.commands.find_blender_executable", lambda: None
    )

    def fake_export(*args: Any, **kwargs: Any) -> None:
        Path("junction_simulation.blend").touch()

    monkeypatch.setattr("junction_sim.cli.commands.export_blender_script", fake_export)
    stdout = io.StringIO()
    ret = main(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "--blender",
            "--open",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Blender executable not found to open GUI" in stdout.getvalue()
    Path("junction_simulation.blend").unlink(missing_ok=True)
    Path("junction_scene.py").unlink(missing_ok=True)


def test_cli_visualize_blender_no_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "junction_sim.cli.commands.export_blender_script",
        lambda *args, **kwargs: None,
    )
    stdout = io.StringIO()
    ret = main(
        [
            "visualize",
            "-p",
            "webster_four_way",
            "-d",
            "5.0",
            "--blender",
        ],
        stdout=stdout,
    )
    assert ret == 0
    assert "Blender 3D Simulation Generated Successfully" in stdout.getvalue()
    Path("junction_scene.py").unlink(missing_ok=True)


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
