import io

import pytest

from junction_sim.cli import main
from junction_sim.cli.commands import instantiate_controller
from junction_sim.controllers.coordinated import (
    CoordinatedSignalController,
    CorridorNode,
    compute_green_wave_offsets,
    compute_progression_bandwidth,
)
from junction_sim.controllers.protocol import ControllerContext
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.engine.transition import SignalState
from junction_sim.exceptions import ValidationError


def create_sample_plan_and_inter() -> tuple[SignalPlan, Intersection]:
    m1 = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    m2 = Movement(
        id="E_T",
        origin="east",
        destination="west",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    l1 = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    l2 = Lane(id="lane_e_0", approach_id="east", allowed_movement_ids=("E_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(l1,))
    app_e = Approach(id="east", direction=Direction.EAST, lanes=(l2,))
    inter = Intersection(
        id="inter_1",
        approaches=(app_n, app_e),
        movements=(m1, m2),
        conflicting_movement_pairs=frozenset(),
    )
    p1 = SignalPhase(id="P1", green_movement_ids=("N_T",), green_duration=30.0)
    p2 = SignalPhase(id="P2", green_movement_ids=("E_T",), green_duration=20.0)
    plan = SignalPlan(id="plan_1", phases=(p1, p2))
    return plan, inter


def test_corridor_node_model() -> None:
    node = CorridorNode(
        intersection_id="int_0",
        distance_from_origin_m=250.0,
        cycle_length=60.0,
        offset_seconds=18.0,
        coordinated_phase_id="P1",
    )
    assert node.intersection_id == "int_0"
    assert node.distance_from_origin_m == 250.0


def test_compute_green_wave_offsets_valid() -> None:
    distances = [0.0, 300.0, 600.0]
    offsets = compute_green_wave_offsets(
        distances_m=distances, progression_speed_mps=15.0, cycle_length=60.0
    )
    assert len(offsets) == 3
    assert offsets[0] == 0.0
    assert offsets[1] == 20.0
    assert offsets[2] == 40.0


def test_compute_green_wave_offsets_validation() -> None:
    with pytest.raises(ValidationError):
        compute_green_wave_offsets([100.0], progression_speed_mps=0.0)
    with pytest.raises(ValidationError):
        compute_green_wave_offsets([100.0], cycle_length=-10.0)
    with pytest.raises(ValidationError):
        compute_green_wave_offsets([-50.0], cycle_length=60.0)


def test_compute_progression_bandwidth() -> None:
    assert compute_progression_bandwidth([], [], []) == 0.0

    with pytest.raises(ValidationError):
        compute_progression_bandwidth([30.0], [0.0], [0.0, 10.0])

    with pytest.raises(ValidationError):
        compute_progression_bandwidth([30.0], [0.0], [0.0], cycle_length=0.0)

    assert compute_progression_bandwidth([0.0], [0.0], [0.0]) == 0.0

    bw = compute_progression_bandwidth(
        green_durations=[30.0, 30.0],
        offsets=[0.0, 20.0],
        travel_times=[0.0, 20.0],
        cycle_length=60.0,
    )
    assert bw == 30.0

    bw_clash = compute_progression_bandwidth(
        green_durations=[10.0, 10.0],
        offsets=[0.0, 30.0],
        travel_times=[0.0, 0.0],
        cycle_length=60.0,
    )
    assert bw_clash == 0.0


def test_coordinated_controller_validation() -> None:
    plan, _ = create_sample_plan_and_inter()
    with pytest.raises(ValidationError):
        CoordinatedSignalController(signal_plan=plan, cycle_length=0.0)
    with pytest.raises(ValidationError):
        CoordinatedSignalController(signal_plan=plan, offset=-5.0)
    with pytest.raises(ValidationError):
        CoordinatedSignalController(signal_plan=plan, coordinated_phase_id="UNKNOWN")


def test_coordinated_controller_decide_and_properties() -> None:
    plan, _ = create_sample_plan_and_inter()
    ctrl = CoordinatedSignalController(
        signal_plan=plan,
        cycle_length=60.0,
        offset=10.0,
        coordinated_phase_id="P1",
    )
    assert ctrl.cycle_length == 60.0
    assert ctrl.offset == 10.0
    assert ctrl.coordinated_phase_id == "P1"

    ctx_trans = ControllerContext(
        current_time=10.0,
        active_phase_id="P1",
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={},
    )
    d_trans = ctrl.decide(ctx_trans)
    assert d_trans.reason == "in_transition"

    ctx_prog = ControllerContext(
        current_time=15.0,
        active_phase_id="P2",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    d_prog = ctrl.decide(ctx_prog)
    assert d_prog.reason == "green_wave_coordinated_progression"
    assert d_prog.target_phase_id == "P1"

    ctx_hold = ControllerContext(
        current_time=16.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    d_hold = ctrl.decide(ctx_hold)
    assert d_hold.reason == "holding_phase"
    assert d_hold.target_phase_id is None

    ctx_cross = ControllerContext(
        current_time=45.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    d_cross = ctrl.decide(ctx_cross)
    assert d_cross.reason == "cross_street_allocation"
    assert d_cross.target_phase_id == "P2"

    ctrl.reset()


def test_instantiate_controller_coordinated() -> None:
    plan, inter = create_sample_plan_and_inter()
    c1 = instantiate_controller("coordinated", plan, inter)
    assert isinstance(c1, CoordinatedSignalController)
    c2 = instantiate_controller("green-wave", plan, inter)
    assert isinstance(c2, CoordinatedSignalController)


def test_cli_run_coordinated() -> None:
    buf = io.StringIO()
    code = main(
        [
            "run",
            "--preset",
            "arterial_corridor",
            "--controller",
            "coordinated",
            "--duration",
            "30.0",
        ],
        stdout=buf,
    )
    assert code == 0
    assert "Simulation Execution Summary" in buf.getvalue()
