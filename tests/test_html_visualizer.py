import io
from pathlib import Path

from junction_sim.controllers.protocol import ControllerDecision
from junction_sim.domain.approach import Approach
from junction_sim.domain.crosswalk import Crosswalk, PedestrianSignalState
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.transition import SignalState
from junction_sim.visualization.html_visualizer import (
    export_interactive_html,
    generate_interactive_html,
    serialize_simulation_data,
)


def create_sample_intersection_and_plan() -> tuple[Intersection, SignalPlan]:
    lanes_n = (
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T",),
            max_capacity=20,
        ),
    )
    lanes_s = (
        Lane(
            id="lane_s_0",
            approach_id="south",
            allowed_movement_ids=("S_T",),
            max_capacity=20,
        ),
    )
    approaches = (
        Approach(
            id="north",
            direction=Direction.NORTH,
            lanes=lanes_n,
        ),
        Approach(
            id="south",
            direction=Direction.SOUTH,
            lanes=lanes_s,
        ),
    )
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
    crosswalks = (
        Crosswalk(
            id="cw_north",
            approach_id="north",
            length_meters=16.0,
            walk_duration=7.0,
            clearance_duration=5.0,
        ),
    )
    intersection = Intersection(
        id="test_int",
        approaches=approaches,
        movements=movements,
        crosswalks=crosswalks,
    )

    phases = (
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=20.0,
            min_green=5.0,
            max_green=30.0,
            yellow_duration=3.0,
            all_red_duration=2.0,
            pedestrian_crosswalk_ids=("cw_north",),
        ),
        SignalPhase(
            id="P2",
            green_movement_ids=("S_T",),
            green_duration=20.0,
            min_green=5.0,
            max_green=30.0,
            yellow_duration=3.0,
            all_red_duration=2.0,
        ),
    )
    plan = SignalPlan(id="test_plan", phases=phases)
    return intersection, plan


def test_serialize_simulation_data_empty() -> None:
    intersection, plan = create_sample_intersection_and_plan()
    data = serialize_simulation_data(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        controller_name="fixed-time",
        scenario_name="empty_test",
        seed=42,
        step_size=1.0,
    )
    assert data["metadata"]["controller"] == "fixed-time"
    assert data["metadata"]["scenario"] == "empty_test"
    assert data["metadata"]["seed"] == 42
    assert data["metadata"]["duration"] == 0.0
    assert data["metadata"]["total_steps"] == 0
    assert data["metadata"]["total_arrivals"] == 0
    assert data["metadata"]["total_discharges"] == 0
    assert data["metadata"]["average_delay"] == 0.0
    assert data["metadata"]["max_delay"] == 0.0
    assert len(data["steps"]) == 0
    assert len(data["intersection"]["approaches"]) == 2
    assert len(data["intersection"]["crosswalks"]) == 1
    assert len(data["signal_plan"]["phases"]) == 2


def test_serialize_simulation_data_populated() -> None:
    intersection, plan = create_sample_intersection_and_plan()
    v1 = Vehicle(id="v1", origin="north", destination="south", arrival_time=1.0)
    v2 = Vehicle(
        id="v2",
        origin="north",
        destination="south",
        arrival_time=0.5,
        departure_time=2.0,
    )
    p1 = Pedestrian(id="p1", crosswalk_id="cw_north", arrival_time=1.0)
    p2 = Pedestrian(
        id="p2",
        crosswalk_id="cw_north",
        arrival_time=0.5,
        crossing_start_time=1.5,
        crossing_completion_time=2.0,
    )

    step = StepResult(
        step_index=1,
        time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(v1,),
        discharged_vehicles=(v2,),
        queue_lengths={"lane_n_0": 1, "lane_s_0": 0},
        controller_decision=ControllerDecision(target_phase_id="P1", reason="maintain"),
        arrived_pedestrians=(p1,),
        discharged_pedestrians=(p2,),
        pedestrian_queue_lengths={"cw_north": 1},
        pedestrian_signals={"cw_north": PedestrianSignalState.WALK},
    )

    data = serialize_simulation_data(
        results=[step],
        intersection=intersection,
        signal_plan=plan,
        controller_name="actuated",
        scenario_name="populated_test",
        seed=101,
        step_size=1.0,
    )

    assert data["metadata"]["total_steps"] == 1
    assert data["metadata"]["total_arrivals"] == 1
    assert data["metadata"]["total_discharges"] == 1
    assert data["metadata"]["average_delay"] == 1.5
    assert data["metadata"]["max_delay"] == 1.5

    s0 = data["steps"][0]
    assert s0["time"] == 2.0
    assert s0["step_index"] == 1
    assert s0["active_phase_id"] == "P1"
    assert s0["signal_state"] == "green"
    assert s0["arrived_vehicle_ids"] == ["v1"]
    assert len(s0["discharged_vehicles"]) == 1
    assert s0["discharged_vehicles"][0]["id"] == "v2"
    assert s0["discharged_vehicles"][0]["waiting_time"] == 1.5
    assert s0["controller_decision"] == {
        "target_phase_id": "P1",
        "reason": "maintain",
    }
    assert s0["arrived_pedestrians"] == ["p1"]
    assert len(s0["discharged_pedestrians"]) == 1
    assert s0["discharged_pedestrians"][0]["id"] == "p2"
    assert s0["discharged_pedestrians"][0]["crossing_start_time"] == 1.5
    assert s0["discharged_pedestrians"][0]["crossing_completion_time"] == 2.0
    assert s0["discharged_pedestrians"][0]["waiting_time"] == 1.0
    assert s0["pedestrian_queue_lengths"] == {"cw_north": 1}
    assert s0["pedestrian_signals"] == {"cw_north": "walk"}


def test_generate_interactive_html() -> None:
    intersection, plan = create_sample_intersection_and_plan()
    html = generate_interactive_html(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        controller_name="max-pressure",
        scenario_name="webster",
    )
    assert "<!DOCTYPE html>" in html
    assert '<canvas id="sim-canvas"' in html
    assert "JUNCTION-SIM" in html
    assert "IntersectionVisualizer" in html
    assert '"controller": "max-pressure"' in html


def test_export_interactive_html_to_string() -> None:
    intersection, plan = create_sample_intersection_and_plan()
    res = export_interactive_html(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=None,
    )
    assert isinstance(res, str)
    assert "<!DOCTYPE html>" in res


def test_export_interactive_html_to_file(tmp_path: Path) -> None:
    intersection, plan = create_sample_intersection_and_plan()
    target = tmp_path / "subdir" / "sim.html"
    ret = export_interactive_html(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=target,
    )
    assert target.exists()
    assert target.read_text(encoding="utf-8") == ret


def test_export_interactive_html_to_textio() -> None:
    intersection, plan = create_sample_intersection_and_plan()
    buf = io.StringIO()
    ret = export_interactive_html(
        results=[],
        intersection=intersection,
        signal_plan=plan,
        destination=buf,
    )
    assert ret == ""
    buf.seek(0)
    assert "<!DOCTYPE html>" in buf.read()
