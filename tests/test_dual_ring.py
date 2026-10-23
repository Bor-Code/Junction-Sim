import pytest
from pydantic import ValidationError as PydanticValidationError

from junction_sim.cli.commands import instantiate_controller
from junction_sim.controllers.dual_ring import DualRingController
from junction_sim.controllers.protocol import ControllerContext
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.dual_ring import (
    DualRingStructure,
    NEMAPhase,
    build_nema_eight_phase_structure,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan, SignalState
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.engine.arrival import DemandProfile
from junction_sim.engine.engine import SimulationEngine
from junction_sim.exceptions import (
    ConfigurationError,
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


def create_nema_test_intersection() -> Intersection:
    movements = (
        Movement(
            id="N_L",
            origin="north",
            destination="east",
            turn_type=TurnType.LEFT,
            saturation_flow_rate=1600.0,
        ),
        Movement(
            id="N_T",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="S_L",
            origin="south",
            destination="west",
            turn_type=TurnType.LEFT,
            saturation_flow_rate=1600.0,
        ),
        Movement(
            id="S_T",
            origin="south",
            destination="north",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="E_L",
            origin="east",
            destination="south",
            turn_type=TurnType.LEFT,
            saturation_flow_rate=1600.0,
        ),
        Movement(
            id="E_T",
            origin="east",
            destination="west",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="W_L",
            origin="west",
            destination="north",
            turn_type=TurnType.LEFT,
            saturation_flow_rate=1600.0,
        ),
        Movement(
            id="W_T",
            origin="west",
            destination="east",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
    )

    lanes_n = (
        Lane(id="ln_nl", approach_id="north", allowed_movement_ids=("N_L",)),
        Lane(id="ln_nt", approach_id="north", allowed_movement_ids=("N_T",)),
    )
    lanes_s = (
        Lane(id="ln_sl", approach_id="south", allowed_movement_ids=("S_L",)),
        Lane(id="ln_st", approach_id="south", allowed_movement_ids=("S_T",)),
    )
    lanes_e = (
        Lane(id="ln_el", approach_id="east", allowed_movement_ids=("E_L",)),
        Lane(id="ln_et", approach_id="east", allowed_movement_ids=("E_T",)),
    )
    lanes_w = (
        Lane(id="ln_wl", approach_id="west", allowed_movement_ids=("W_L",)),
        Lane(id="ln_wt", approach_id="west", allowed_movement_ids=("W_T",)),
    )

    approaches = (
        Approach(id="north", direction=Direction.NORTH, lanes=lanes_n),
        Approach(id="south", direction=Direction.SOUTH, lanes=lanes_s),
        Approach(id="east", direction=Direction.EAST, lanes=lanes_e),
        Approach(id="west", direction=Direction.WEST, lanes=lanes_w),
    )

    conflicts = frozenset(
        {
            frozenset({"N_T", "E_T"}),
            frozenset({"N_T", "W_T"}),
            frozenset({"S_T", "E_T"}),
            frozenset({"S_T", "W_T"}),
            frozenset({"N_L", "S_T"}),
            frozenset({"S_L", "N_T"}),
            frozenset({"E_L", "W_T"}),
            frozenset({"W_L", "E_T"}),
        }
    )

    return Intersection(
        id="nema_int",
        approaches=approaches,
        movements=movements,
        conflicting_movement_pairs=conflicts,
    )


def test_nema_phase_creation_and_validation() -> None:
    p = NEMAPhase(
        phase_number=1,
        ring=1,
        barrier_group=1,
        green_movement_ids=("N_L",),
        green_duration=10.0,
    )
    assert p.phase_number == 1
    assert p.ring == 1
    assert p.barrier_group == 1
    assert p.total_duration == 14.0

    with pytest.raises(PydanticValidationError):
        NEMAPhase(
            phase_number=0,
            ring=1,
            barrier_group=1,
            green_movement_ids=("N_L",),
            green_duration=10.0,
        )

    with pytest.raises(PydanticValidationError):
        NEMAPhase(
            phase_number=1,
            ring=3,
            barrier_group=1,
            green_movement_ids=("N_L",),
            green_duration=10.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="max_green cannot be less"):
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=("N_L",),
            green_duration=10.0,
            min_green=20.0,
            max_green=10.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="green_duration cannot be less"):
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=("N_L",),
            green_duration=4.0,
            min_green=5.0,
            max_green=30.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="green_duration cannot exceed"):
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=("N_L",),
            green_duration=40.0,
            min_green=5.0,
            max_green=30.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="movement id cannot be empty"):
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=("  ",),
            green_duration=10.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="duplicate movement ids"):
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=("N_L", "N_L"),
            green_duration=10.0,
        )


def test_dual_ring_structure_validation() -> None:
    p1 = NEMAPhase(
        phase_number=1,
        ring=1,
        barrier_group=1,
        green_movement_ids=("N_L",),
        green_duration=10.0,
    )
    p2 = NEMAPhase(
        phase_number=5,
        ring=2,
        barrier_group=1,
        green_movement_ids=("S_L",),
        green_duration=10.0,
    )

    with pytest.raises(ValidationError, match="dual ring id cannot be empty"):
        DualRingStructure(id="  ", phases=(p1, p2))

    p_dup = NEMAPhase(
        phase_number=1,
        ring=2,
        barrier_group=1,
        green_movement_ids=("S_L",),
        green_duration=10.0,
    )
    with pytest.raises(InvalidSignalPlanError, match="duplicate phase numbers"):
        DualRingStructure(id="dr", phases=(p1, p_dup))

    p_ring1_only = NEMAPhase(
        phase_number=2,
        ring=1,
        barrier_group=1,
        green_movement_ids=("S_T",),
        green_duration=10.0,
    )
    with pytest.raises(
        InvalidSignalPlanError, match="must contain phases in both ring 1 and ring 2"
    ):
        DualRingStructure(id="dr", phases=(p1, p_ring1_only))

    p_mismatched_barrier = NEMAPhase(
        phase_number=5,
        ring=2,
        barrier_group=2,
        green_movement_ids=("S_L",),
        green_duration=10.0,
    )
    with pytest.raises(
        InvalidSignalPlanError, match="barrier groups must be identical"
    ):
        DualRingStructure(id="dr", phases=(p1, p_mismatched_barrier))


def test_dual_ring_methods_and_conversion() -> None:
    inter = create_nema_test_intersection()
    structure = build_nema_eight_phase_structure(inter)

    assert len(structure.phases) == 8
    assert len(structure.ring1_phases) == 4
    assert len(structure.ring2_phases) == 4
    assert structure.barrier_groups == (1, 2)

    p1 = structure.get_phase(1)
    assert p1.phase_number == 1
    assert p1.ring == 1

    with pytest.raises(InvalidSignalPlanError, match="NEMA phase 99 not found"):
        structure.get_phase(99)

    b1_phases = structure.get_phases_in_barrier(1)
    assert len(b1_phases) == 4
    b1_r1 = structure.get_phases_in_barrier(1, ring=1)
    assert len(b1_r1) == 2

    assert not structure.are_compatible(1, 1)
    assert not structure.are_compatible(1, 2)
    assert not structure.are_compatible(1, 7)
    assert structure.are_compatible(1, 5)
    assert structure.are_compatible(1, 6)

    plan = structure.to_signal_plan(plan_id="nema_plan_test")
    assert plan.id == "nema_plan_test"
    assert len(plan.phases) == 4

    default_plan = structure.to_signal_plan()
    assert default_plan.id == f"{structure.id}_plan"

    validate_signal_plan_against_intersection(plan, inter)


def test_build_nema_eight_phase_missing_movement() -> None:
    mov = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    lane_n = Lane(id="ln0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="ln1", approach_id="south", allowed_movement_ids=("N_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    inter = Intersection(
        id="bad_nema_int",
        approaches=(app_n, app_s),
        movements=(mov,),
    )
    with pytest.raises(ValidationError, match="intersection missing movement"):
        build_nema_eight_phase_structure(inter)


def test_dual_ring_controller_lifecycle() -> None:
    inter = create_nema_test_intersection()
    structure = build_nema_eight_phase_structure(inter)
    plan = structure.to_signal_plan()

    ctrl = DualRingController(dual_ring=structure, signal_plan=plan, intersection=inter)
    assert ctrl.dual_ring == structure
    assert ctrl.signal_plan == plan
    assert ctrl.intersection == inter
    assert ctrl.current_phase_index == 0
    assert ctrl.elapsed_green == 0.0

    p_initial = plan.phases[0].id

    ctx = ControllerContext(
        current_time=0.0,
        active_phase_id=p_initial,
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    d = ctrl.decide(ctx)
    assert not d.should_change_phase
    assert d.reason is not None and "not reached" in d.reason

    ctx_trans = ControllerContext(
        current_time=1.0,
        active_phase_id=p_initial,
        signal_state=SignalState.YELLOW,
        is_in_transition=True,
        queue_lengths={},
    )
    d_trans = ctrl.decide(ctx_trans)
    assert not d_trans.should_change_phase
    assert d_trans.reason == "signal in transition"

    ctx_back = ControllerContext(
        current_time=0.5,
        active_phase_id=p_initial,
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    with pytest.raises(InvalidStateError, match="cannot go backwards"):
        ctrl.decide(ctx_back)

    ctx_unknown = ControllerContext(
        current_time=2.0,
        active_phase_id="unknown_phase",
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={},
    )
    with pytest.raises(InvalidSignalPlanError, match="unknown active phase"):
        ctrl.decide(ctx_unknown)

    ctrl.reset()
    assert ctrl.current_phase_index == 0
    assert ctrl.elapsed_green == 0.0


def test_dual_ring_controller_gap_out_and_max_green() -> None:
    inter = create_nema_test_intersection()
    structure = build_nema_eight_phase_structure(inter)
    plan = structure.to_signal_plan()
    ctrl = DualRingController(dual_ring=structure, signal_plan=plan, intersection=inter)

    first_phase = plan.phases[0]
    next_phase = plan.phases[1].id

    ctrl.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id=first_phase.id,
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )

    ctx_min_passed = ControllerContext(
        current_time=first_phase.min_green + 1.0,
        active_phase_id=first_phase.id,
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"ln_nl": 0, "ln_sl": 0, "ln_nt": 5},
    )
    d_gap = ctrl.decide(ctx_min_passed)
    assert d_gap.should_change_phase
    assert d_gap.target_phase_id == next_phase
    assert d_gap.reason == "gap out on active phase"

    ctrl.reset()
    ctrl.decide(
        ControllerContext(
            current_time=0.0,
            active_phase_id=first_phase.id,
            signal_state=SignalState.GREEN,
            is_in_transition=False,
            queue_lengths={},
        )
    )

    ctx_holding = ControllerContext(
        current_time=first_phase.min_green + 1.0,
        active_phase_id=first_phase.id,
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"ln_nl": 3, "ln_sl": 2},
    )
    d_hold = ctrl.decide(ctx_holding)
    assert not d_hold.should_change_phase
    assert d_hold.reason == "holding dual-ring phase green"

    ctx_max = ControllerContext(
        current_time=first_phase.max_green + 1.0,
        active_phase_id=first_phase.id,
        signal_state=SignalState.GREEN,
        is_in_transition=False,
        queue_lengths={"ln_nl": 5},
    )
    d_max = ctrl.decide(ctx_max)
    assert d_max.should_change_phase
    assert d_max.target_phase_id == next_phase
    assert d_max.reason is not None and "max_green" in d_max.reason


def test_simulation_engine_dual_ring_execution() -> None:
    inter = create_nema_test_intersection()
    structure = build_nema_eight_phase_structure(inter)
    plan = structure.to_signal_plan()
    ctrl = DualRingController(dual_ring=structure, signal_plan=plan, intersection=inter)

    demands = (
        DemandProfile(movement_id="N_L", flow_rate_vph=150.0),
        DemandProfile(movement_id="N_T", flow_rate_vph=400.0),
        DemandProfile(movement_id="S_L", flow_rate_vph=150.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=400.0),
        DemandProfile(movement_id="E_L", flow_rate_vph=100.0),
        DemandProfile(movement_id="E_T", flow_rate_vph=300.0),
        DemandProfile(movement_id="W_L", flow_rate_vph=100.0),
        DemandProfile(movement_id="W_T", flow_rate_vph=300.0),
    )

    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        controller=ctrl,
        seed=42,
        step_size=1.0,
    )

    results = engine.run(duration=50.0)
    assert len(results) == 50
    total_arrivals = sum(len(r.arrived_vehicles) for r in results)
    total_served = sum(len(r.discharged_vehicles) for r in results)
    assert total_arrivals > 0
    assert total_served > 0


def test_instantiate_controller_dual_ring() -> None:
    inter = create_nema_test_intersection()
    structure = build_nema_eight_phase_structure(inter)
    plan = structure.to_signal_plan()

    c = instantiate_controller("dual-ring", plan, inter)
    assert isinstance(c, DualRingController)

    mov_1 = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_2 = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )
    lane_n = Lane(id="ln0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="ln1", approach_id="south", allowed_movement_ids=("S_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    p1 = SignalPhase(id="p1", green_movement_ids=("N_T",), green_duration=10.0)
    p2 = SignalPhase(id="p2", green_movement_ids=("S_T",), green_duration=10.0)
    simple_plan = SignalPlan(id="spl", phases=(p1, p2))
    incompat_inter = Intersection(
        id="simple_int",
        approaches=(app_n, app_s),
        movements=(mov_1, mov_2),
    )

    with pytest.raises(ConfigurationError, match="incompatible with dual-ring"):
        instantiate_controller("dual-ring", simple_plan, incompat_inter)
