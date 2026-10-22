import io
from pathlib import Path

import pytest
from pydantic import ValidationError as PydanticValidationError

from junction_sim.cli import main
from junction_sim.config.schema import (
    ApproachConfig,
    CrosswalkConfig,
    DemandProfileConfig,
    IntersectionConfig,
    LaneConfig,
    MovementConfig,
    PedestrianDemandConfig,
    ScenarioConfig,
    SignalPhaseConfig,
    SignalPlanConfig,
    SimulationConfig,
)
from junction_sim.domain.approach import Approach
from junction_sim.domain.crosswalk import Crosswalk, PedestrianSignalState
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.validation import validate_signal_plan_against_intersection
from junction_sim.engine.arrival import (
    DemandInterval,
    DemandProfile,
    PedestrianArrivalGenerator,
    PedestrianDemandProfile,
)
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.pedestrian_queue import PedestrianQueue
from junction_sim.engine.rng import TrafficRNG
from junction_sim.exceptions import (
    ConfigurationError,
    InvalidGeometryError,
    InvalidSignalPlanError,
    InvalidStateError,
    ValidationError,
)


def create_test_intersection() -> tuple[Intersection, SignalPlan]:
    mov_n = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    mov_s = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
        saturation_flow_rate=1800.0,
    )
    lane_n = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))

    cw_n = Crosswalk(
        id="cw_north",
        approach_id="north",
        length_meters=12.0,
        pedestrian_speed_mps=1.2,
        walk_duration=7.0,
    )

    inter = Intersection(
        id="ped_int",
        approaches=(app_n, app_s),
        movements=(mov_n, mov_s),
        crosswalks=(cw_n,),
        conflicting_movement_pairs=frozenset(),
    )

    p1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        pedestrian_crosswalk_ids=("cw_north",),
        green_duration=20.0,
    )
    p2 = SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=15.0)
    plan = SignalPlan(id="ped_plan", phases=(p1, p2))
    return inter, plan


def test_crosswalk_defaults_and_properties() -> None:
    cw = Crosswalk(id="cw1", approach_id="north")
    assert cw.id == "cw1"
    assert cw.approach_id == "north"
    assert cw.length_meters == 12.0
    assert cw.pedestrian_speed_mps == 1.2
    assert cw.walk_duration == 7.0
    assert cw.clearance_duration is None
    assert cw.effective_clearance_duration == 10.0
    assert cw.total_pedestrian_time == 17.0


def test_crosswalk_custom_clearance() -> None:
    cw = Crosswalk(
        id="cw1",
        approach_id="north",
        length_meters=15.0,
        pedestrian_speed_mps=1.5,
        walk_duration=8.0,
        clearance_duration=12.0,
    )
    assert cw.effective_clearance_duration == 12.0
    assert cw.total_pedestrian_time == 20.0


def test_crosswalk_validation_errors() -> None:
    with pytest.raises(ValidationError, match="crosswalk id cannot be empty"):
        Crosswalk(id="  ", approach_id="north")

    with pytest.raises(ValidationError, match="approach_id cannot be empty"):
        Crosswalk(id="cw1", approach_id="  ")

    with pytest.raises(PydanticValidationError):
        Crosswalk(id="cw1", approach_id="north", length_meters=0.0)

    with pytest.raises(PydanticValidationError):
        Crosswalk(id="cw1", approach_id="north", walk_duration=2.0)


def test_crosswalk_signal_state_transitions() -> None:
    cw = Crosswalk(
        id="cw1",
        approach_id="north",
        walk_duration=7.0,
        clearance_duration=10.0,
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=3.0, is_phase_green=False)
        == PedestrianSignalState.DONT_WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=0.0, is_phase_green=True)
        == PedestrianSignalState.WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=6.9, is_phase_green=True)
        == PedestrianSignalState.WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=7.0, is_phase_green=True)
        == PedestrianSignalState.FLASHING_DONT_WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=16.9, is_phase_green=True)
        == PedestrianSignalState.FLASHING_DONT_WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=17.0, is_phase_green=True)
        == PedestrianSignalState.DONT_WALK
    )
    assert (
        cw.get_signal_state(elapsed_in_phase=25.0, is_phase_green=True)
        == PedestrianSignalState.DONT_WALK
    )


def test_pedestrian_domain_model() -> None:
    p = Pedestrian(id="p1", crosswalk_id="cw1", arrival_time=5.0)
    assert p.id == "p1"
    assert p.crosswalk_id == "cw1"
    assert p.arrival_time == 5.0
    assert p.waiting_time(current_time=10.0) == 5.0

    p_started = p.model_copy(
        update={"crossing_start_time": 8.0, "crossing_completion_time": 18.0}
    )
    assert p_started.waiting_time(current_time=20.0) == 3.0

    with pytest.raises(ValidationError, match="current_time cannot be earlier"):
        p.waiting_time(current_time=3.0)


def test_pedestrian_validation_errors() -> None:
    with pytest.raises(ValidationError, match="pedestrian id cannot be empty"):
        Pedestrian(id="  ", crosswalk_id="cw1", arrival_time=0.0)

    with pytest.raises(ValidationError, match="crosswalk_id cannot be empty"):
        Pedestrian(id="p1", crosswalk_id="  ", arrival_time=0.0)

    with pytest.raises(ValidationError, match="crossing_start_time cannot be earlier"):
        Pedestrian(
            id="p1",
            crosswalk_id="cw1",
            arrival_time=10.0,
            crossing_start_time=5.0,
        )

    with pytest.raises(ValidationError, match="crossing_start_time must be set"):
        Pedestrian(
            id="p1",
            crosswalk_id="cw1",
            arrival_time=10.0,
            crossing_completion_time=20.0,
        )

    with pytest.raises(
        ValidationError, match="crossing_completion_time cannot be earlier"
    ):
        Pedestrian(
            id="p1",
            crosswalk_id="cw1",
            arrival_time=10.0,
            crossing_start_time=15.0,
            crossing_completion_time=12.0,
        )


def test_pedestrian_queue_operations() -> None:
    cw = Crosswalk(id="cw_test", approach_id="north", clearance_duration=10.0)
    q = PedestrianQueue(crosswalk=cw, max_capacity=2)
    assert q.crosswalk == cw
    assert q.max_capacity == 2
    assert q.length == 0
    assert q.is_empty
    assert not q.is_full
    assert q.peek() is None

    with pytest.raises(ValidationError, match="max_capacity must be greater than zero"):
        PedestrianQueue(crosswalk=cw, max_capacity=0)

    p1 = Pedestrian(id="p1", crosswalk_id="cw_test", arrival_time=2.0)
    q.enqueue(p1)
    assert q.length == 1
    assert q.peek() == p1
    assert not q.is_empty
    assert not q.is_full

    p_wrong = Pedestrian(id="p_wrong", crosswalk_id="cw_other", arrival_time=2.0)
    with pytest.raises(ValidationError, match="does not match queue crosswalk"):
        q.enqueue(p_wrong)

    p2 = Pedestrian(id="p2", crosswalk_id="cw_test", arrival_time=3.0)
    q.enqueue(p2)
    assert q.is_full

    p3 = Pedestrian(id="p3", crosswalk_id="cw_test", arrival_time=4.0)
    with pytest.raises(InvalidStateError, match="is full"):
        q.enqueue(p3)

    with pytest.raises(ValidationError, match="current_time cannot be negative"):
        q.discharge(current_time=-1.0)

    discharged = q.discharge(current_time=5.0, max_count=1)
    assert len(discharged) == 1
    assert discharged[0].id == "p1"
    assert discharged[0].crossing_start_time == 5.0
    assert discharged[0].crossing_completion_time == 15.0
    assert q.length == 1

    remaining = q.discharge(current_time=6.0)
    assert len(remaining) == 1
    assert remaining[0].id == "p2"
    assert remaining[0].crossing_start_time == 6.0
    assert remaining[0].crossing_completion_time == 16.0
    assert q.is_empty


def test_pedestrian_demand_profile_and_generator() -> None:
    dp = PedestrianDemandProfile(crosswalk_id="cw1", flow_rate_pph=120.0)
    assert dp.crosswalk_id == "cw1"
    assert dp.flow_rate_pph == 120.0
    assert dp.get_flow_rate(10.0) == 120.0

    interval = DemandInterval(start_time=0.0, end_time=100.0, flow_rate_vph=300.0)
    interval_b = DemandInterval(start_time=100.0, end_time=200.0, flow_rate_vph=150.0)
    dp_var = PedestrianDemandProfile(
        crosswalk_id="cw1",
        flow_rate_pph=60.0,
        intervals=(interval, interval_b),
    )
    assert dp_var.get_flow_rate(50.0) == 300.0
    assert dp_var.get_flow_rate(150.0) == 150.0
    assert dp_var.get_flow_rate(250.0) == 60.0

    with pytest.raises(ValidationError, match="crosswalk id cannot be empty"):
        PedestrianDemandProfile(crosswalk_id="  ")

    i1 = DemandInterval(start_time=0.0, end_time=60.0, flow_rate_vph=100.0)
    i2 = DemandInterval(start_time=30.0, end_time=90.0, flow_rate_vph=200.0)
    with pytest.raises(ValidationError, match="demand intervals cannot overlap"):
        PedestrianDemandProfile(crosswalk_id="cw1", intervals=(i1, i2))

    inter, _ = create_test_intersection()
    rng = TrafficRNG(seed=42)

    with pytest.raises(ValidationError, match="duplicate demand profiles"):
        PedestrianArrivalGenerator(
            intersection=inter,
            demands=(
                PedestrianDemandProfile(crosswalk_id="cw_north", flow_rate_pph=100.0),
                PedestrianDemandProfile(crosswalk_id="cw_north", flow_rate_pph=200.0),
            ),
            rng=rng,
        )

    with pytest.raises(InvalidGeometryError, match="unknown crosswalk id"):
        PedestrianArrivalGenerator(
            intersection=inter,
            demands=(
                PedestrianDemandProfile(crosswalk_id="cw_unknown", flow_rate_pph=100.0),
            ),
            rng=rng,
        )

    gen = PedestrianArrivalGenerator(
        intersection=inter,
        demands=(
            PedestrianDemandProfile(crosswalk_id="cw_north", flow_rate_pph=3600.0),
        ),
        rng=rng,
    )
    assert gen.demands[0].crosswalk_id == "cw_north"
    assert gen.pedestrian_counter == 0

    with pytest.raises(ValidationError, match="step_size must be greater than zero"):
        gen.generate_arrivals(current_time=0.0, step_size=0.0)

    with pytest.raises(ValidationError, match="current_time cannot be negative"):
        gen.generate_arrivals(current_time=-1.0, step_size=1.0)

    arrivals = gen.generate_arrivals(current_time=0.0, step_size=10.0)
    assert len(arrivals) > 0
    assert arrivals[0].crosswalk_id == "cw_north"
    assert arrivals[0].arrival_time == 0.0

    gen_zero = PedestrianArrivalGenerator(
        intersection=inter,
        demands=(PedestrianDemandProfile(crosswalk_id="cw_north", flow_rate_pph=0.0),),
        rng=rng,
    )
    assert gen_zero.generate_arrivals(current_time=0.0, step_size=1.0) == ()


def test_intersection_crosswalk_validation() -> None:
    cw1 = Crosswalk(id="cw_1", approach_id="north")
    cw2 = Crosswalk(id="cw_1", approach_id="south")

    lane_n = Lane(id="ln0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="ln1", approach_id="south", allowed_movement_ids=("S_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    mov_n = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
    )
    mov_s = Movement(
        id="S_T",
        origin="south",
        destination="north",
        turn_type=TurnType.THROUGH,
    )

    with pytest.raises(
        InvalidGeometryError, match="duplicate crosswalk ids found in intersection"
    ):
        Intersection(
            id="bad_int",
            approaches=(app_n, app_s),
            movements=(mov_n, mov_s),
            crosswalks=(cw1, cw2),
        )

    cw_invalid_app = Crosswalk(id="cw_x", approach_id="unknown_app")
    with pytest.raises(InvalidGeometryError, match="does not match any approach"):
        Intersection(
            id="bad_int2",
            approaches=(app_n, app_s),
            movements=(mov_n, mov_s),
            crosswalks=(cw_invalid_app,),
        )

    inter, _ = create_test_intersection()
    assert inter.get_crosswalk("cw_north").id == "cw_north"
    with pytest.raises(InvalidGeometryError, match="not found in intersection"):
        inter.get_crosswalk("cw_unknown")


def test_signal_phase_crosswalk_validation() -> None:
    with pytest.raises(InvalidSignalPlanError, match="crosswalk id cannot be empty"):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            pedestrian_crosswalk_ids=("  ",),
            green_duration=10.0,
        )

    with pytest.raises(InvalidSignalPlanError, match="duplicate crosswalk ids"):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            pedestrian_crosswalk_ids=("cw1", "cw1"),
            green_duration=10.0,
        )

    inter, _ = create_test_intersection()
    bad_phase = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        pedestrian_crosswalk_ids=("cw_nonexistent",),
        green_duration=10.0,
    )
    p2 = SignalPhase(id="P2", green_movement_ids=("S_T",), green_duration=10.0)
    plan = SignalPlan(id="bad_plan", phases=(bad_phase, p2))
    with pytest.raises(InvalidSignalPlanError, match="references unknown crosswalk"):
        validate_signal_plan_against_intersection(plan, inter)


def test_simulation_engine_pedestrian_execution() -> None:
    inter, plan = create_test_intersection()
    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=300.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=300.0),
    )
    ped_demands = (
        PedestrianDemandProfile(crosswalk_id="cw_north", flow_rate_pph=1200.0),
    )

    engine = SimulationEngine(
        intersection=inter,
        signal_plan=plan,
        demands=demands,
        pedestrian_demands=ped_demands,
        seed=42,
        step_size=1.0,
    )

    assert len(engine.pedestrian_demands) == 1
    assert "cw_north" in engine.pedestrian_queues
    assert engine.get_pedestrian_queue_length("cw_north") == 0
    assert engine.get_pedestrian_queue("cw_north").crosswalk.id == "cw_north"

    with pytest.raises(InvalidGeometryError, match="unknown crosswalk id"):
        engine.get_pedestrian_queue("cw_invalid")

    results = engine.run(duration=40.0)
    assert len(results) == 40

    total_ped_arrivals = sum(len(r.arrived_pedestrians) for r in results)
    total_ped_discharges = sum(len(r.discharged_pedestrians) for r in results)
    assert total_ped_arrivals > 0
    assert total_ped_discharges > 0

    first_step = results[0]
    assert "cw_north" in first_step.pedestrian_signals
    assert first_step.pedestrian_signals["cw_north"] == PedestrianSignalState.WALK


def test_config_and_cli_pedestrian_support() -> None:
    app_n = ApproachConfig(
        id="north",
        direction=Direction.NORTH,
        lanes=[
            LaneConfig(
                id="ln0",
                approach_id="north",
                allowed_movement_ids=["N_T"],
                max_capacity=50,
            )
        ],
    )
    app_s = ApproachConfig(
        id="south",
        direction=Direction.SOUTH,
        lanes=[
            LaneConfig(
                id="ln1",
                approach_id="south",
                allowed_movement_ids=["S_T"],
                max_capacity=50,
            )
        ],
    )
    mov_n = MovementConfig(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_s = MovementConfig(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )
    cw_cfg = CrosswalkConfig(
        id="cw_n",
        approach_id="north",
        length_meters=10.0,
        pedestrian_speed_mps=1.0,
        walk_duration=5.0,
    )
    inter_cfg = IntersectionConfig(
        id="cfg_int",
        approaches=[app_n, app_s],
        movements=[mov_n, mov_s],
        crosswalks=[cw_cfg],
    )
    p1 = SignalPhaseConfig(
        id="P1",
        green_movement_ids=["N_T"],
        pedestrian_crosswalk_ids=["cw_n"],
        green_duration=10.0,
    )
    p2 = SignalPhaseConfig(id="P2", green_movement_ids=["S_T"], green_duration=10.0)
    plan_cfg = SignalPlanConfig(id="cfg_plan", phases=[p1, p2])
    dem_cfg = [DemandProfileConfig(movement_id="N_T", flow_rate_vph=200.0)]
    ped_dem_cfg = [PedestrianDemandConfig(crosswalk_id="cw_n", flow_rate_pph=600.0)]

    sc_cfg = ScenarioConfig(
        intersection=inter_cfg,
        signal_plan=plan_cfg,
        demands=dem_cfg,
        pedestrian_demands=ped_dem_cfg,
        simulation=SimulationConfig(duration=20.0, step_size=1.0, seed=42),
    )

    inter, plan, demands, sim_cfg = sc_cfg.build_scenario()
    assert len(inter.crosswalks) == 1
    assert len(sc_cfg.build_pedestrian_demands()) == 1

    bad_sc = sc_cfg.model_copy(
        update={
            "pedestrian_demands": [
                PedestrianDemandConfig(crosswalk_id="cw_missing", flow_rate_pph=100.0)
            ]
        }
    )
    with pytest.raises(ConfigurationError, match="unknown crosswalk"):
        bad_sc.build_scenario()

    json_path = Path("scratch_ped_scenario.json")
    json_path.write_text(sc_cfg.model_dump_json(indent=2), encoding="utf-8")

    buf = io.StringIO()
    try:
        code = main(
            ["run", "-c", str(json_path), "--duration", "20"],
            stdout=buf,
        )
        assert code == 0
        out = buf.getvalue()
        assert "Ped Arrivals:" in out
        assert "Ped Served:" in out
    finally:
        if json_path.exists():
            json_path.unlink()
