import math

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.trajectories import (
    TrajectoryEngine,
    VehicleState3D,
    VehicleType,
    build_turn_control_points,
    compute_bezier_point,
    export_trajectories_to_dict,
    get_approach_vectors,
    get_deterministic_vehicle_attributes,
    get_lane_stop_position,
    get_outbound_exit_position,
    sample_scene_vehicles,
)
from junction_sim.engine.transition import SignalState


def create_four_way_test_intersection() -> tuple[Intersection, SignalPlan]:
    movements = (
        Movement(
            id="N_T",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="N_L",
            origin="north",
            destination="east",
            turn_type=TurnType.LEFT,
            saturation_flow_rate=1600.0,
        ),
        Movement(
            id="N_R",
            origin="north",
            destination="west",
            turn_type=TurnType.RIGHT,
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
            id="E_T",
            origin="east",
            destination="west",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=1800.0,
        ),
        Movement(
            id="W_T",
            origin="west",
            destination="east",
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
                    allowed_movement_ids=("N_T", "N_L", "N_R"),
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
        Approach(
            id="east",
            direction=Direction.EAST,
            lanes=(
                Lane(
                    id="ln_e0",
                    approach_id="east",
                    allowed_movement_ids=("E_T",),
                ),
            ),
        ),
        Approach(
            id="west",
            direction=Direction.WEST,
            lanes=(
                Lane(
                    id="ln_w0",
                    approach_id="west",
                    allowed_movement_ids=("W_T",),
                ),
            ),
        ),
    )
    intersection = Intersection(
        id="four_way_test",
        approaches=approaches,
        movements=movements,
    )

    phases = (
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T", "S_T"),
            green_duration=20.0,
            min_green=5.0,
            max_green=30.0,
        ),
        SignalPhase(
            id="P2",
            green_movement_ids=("E_T", "W_T"),
            green_duration=20.0,
            min_green=5.0,
            max_green=30.0,
        ),
        SignalPhase(
            id="P3",
            green_movement_ids=("N_L", "N_R"),
            green_duration=15.0,
            min_green=5.0,
            max_green=25.0,
        ),
    )
    plan = SignalPlan(id="test_plan_3p", phases=phases)
    return intersection, plan


def test_deterministic_vehicle_attributes() -> None:
    t1, c1 = get_deterministic_vehicle_attributes("veh_100")
    t2, c2 = get_deterministic_vehicle_attributes("veh_100")
    assert t1 == t2
    assert c1 == c2
    assert isinstance(t1, VehicleType)
    assert c1.startswith("#")


def test_compute_bezier_point() -> None:
    p0 = (0.0, 0.0)
    p1 = (0.0, 5.0)
    p2 = (5.0, 10.0)
    p3 = (10.0, 10.0)

    x0, y0, h0 = compute_bezier_point(p0, p1, p2, p3, 0.0)
    assert abs(x0 - 0.0) < 1e-4
    assert abs(y0 - 0.0) < 1e-4

    x1, y1, h1 = compute_bezier_point(p0, p1, p2, p3, 1.0)
    assert abs(x1 - 10.0) < 1e-4
    assert abs(y1 - 10.0) < 1e-4

    x_mid, y_mid, h_mid = compute_bezier_point(p0, p1, p2, p3, 0.5)
    assert 0.0 < x_mid < 10.0
    assert 0.0 < y_mid < 10.0
    assert -math.pi <= h_mid <= math.pi

    x_neg, _, _ = compute_bezier_point(p0, p1, p2, p3, -1.0)
    assert abs(x_neg - 0.0) < 1e-4


def test_get_approach_vectors() -> None:
    fn, rn = get_approach_vectors(Direction.NORTH)
    assert fn == (0.0, -1.0)
    assert rn == (1.0, 0.0)

    fs, rs = get_approach_vectors(Direction.SOUTH)
    assert fs == (0.0, 1.0)
    assert rs == (-1.0, 0.0)

    fe, re = get_approach_vectors(Direction.EAST)
    assert fe == (-1.0, 0.0)
    assert re == (0.0, -1.0)

    fw, rw = get_approach_vectors(Direction.WEST)
    assert fw == (1.0, 0.0)
    assert rw == (0.0, 1.0)


def test_lane_stop_and_exit_positions() -> None:
    for d in (Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST):
        sx, sy, sh = get_lane_stop_position(d, 0, 1)
        assert isinstance(sx, float)
        assert isinstance(sy, float)
        assert -math.pi <= sh <= math.pi

        ex, ey, eh = get_outbound_exit_position(d)
        assert isinstance(ex, float)
        assert isinstance(ey, float)
        assert -math.pi <= eh <= math.pi


def test_build_turn_control_points() -> None:
    p0 = (0.0, 18.0)
    p3 = (0.0, -18.0)

    cp_t = build_turn_control_points(
        Direction.NORTH, Direction.SOUTH, TurnType.THROUGH, p0, p3
    )
    assert len(cp_t) == 4
    assert cp_t[0] == p0
    assert cp_t[3] == p3

    cp_l = build_turn_control_points(
        Direction.NORTH, Direction.EAST, TurnType.LEFT, p0, (18.0, 0.0)
    )
    assert len(cp_l) == 4

    cp_r = build_turn_control_points(
        Direction.NORTH, Direction.WEST, TurnType.RIGHT, p0, (-18.0, 0.0)
    )
    assert len(cp_r) == 4


def test_trajectory_engine_empty() -> None:
    intersection, plan = create_four_way_test_intersection()
    engine = TrajectoryEngine(intersection, plan)
    reg = engine.generate_vehicle_states([])
    assert reg == {}


def test_trajectory_engine_simulation_run() -> None:
    intersection, plan = create_four_way_test_intersection()
    v1 = Vehicle(id="car_1", origin="north", destination="south", arrival_time=1.0)
    v2 = Vehicle(id="car_2", origin="north", destination="east", arrival_time=1.5)
    v3 = Vehicle(id="car_3", origin="north", destination="west", arrival_time=2.0)

    step0 = StepResult(
        step_index=0,
        time=1.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(v1, v2, v3),
        discharged_vehicles=(),
        queue_lengths={"ln_n0": 3},
    )

    v1_dis = Vehicle(
        id="car_1",
        origin="north",
        destination="south",
        arrival_time=1.0,
        departure_time=2.0,
    )
    v2_dis = Vehicle(
        id="car_2",
        origin="north",
        destination="east",
        arrival_time=1.5,
        departure_time=2.0,
    )
    v3_dis = Vehicle(
        id="car_3",
        origin="north",
        destination="west",
        arrival_time=2.0,
        departure_time=2.0,
    )

    step1 = StepResult(
        step_index=1,
        time=2.0,
        active_phase_id="P1",
        signal_state=SignalState.GREEN,
        arrived_vehicles=(),
        discharged_vehicles=(v1_dis, v2_dis, v3_dis),
        queue_lengths={"ln_n0": 0},
    )

    results = [step0, step1]
    engine = TrajectoryEngine(intersection, plan, transit_duration=2.0)
    reg = engine.generate_vehicle_states(results, substep_dt=0.5)

    assert "car_1" in reg
    assert "car_2" in reg
    assert "car_3" in reg

    s1 = reg["car_1"]
    assert len(s1) > 0
    first_state = s1[0]
    assert first_state.vehicle_id == "car_1"
    assert first_state.brake_light is True
    assert first_state.turn_signal == "none"

    s2 = reg["car_2"]
    left_state = next(s for s in s2 if s.turn_signal == "left")
    assert left_state is not None
    assert left_state.steering_angle >= 0.0

    s3 = reg["car_3"]
    right_state = next(s for s in s3 if s.turn_signal == "right")
    assert right_state is not None
    assert right_state.steering_angle <= 0.0

    sampled = sample_scene_vehicles(reg, query_time=2.5, tolerance=0.5)
    assert len(sampled) >= 1

    d = export_trajectories_to_dict(reg)
    assert "car_1" in d
    assert isinstance(d["car_1"], list)
    assert "x" in d["car_1"][0]
    assert "y" in d["car_1"][0]
    assert "heading" in d["car_1"][0]


def test_sample_scene_vehicles_edge_cases() -> None:
    empty_reg: dict[str, list[VehicleState3D]] = {"empty": []}
    assert sample_scene_vehicles(empty_reg, 5.0) == []

    st = VehicleState3D(
        time=10.0,
        vehicle_id="v_test",
        x=0.0,
        y=0.0,
        heading=0.0,
    )
    reg = {"v_test": [st]}
    assert len(sample_scene_vehicles(reg, 10.1, tolerance=0.2)) == 1
    assert len(sample_scene_vehicles(reg, 20.0, tolerance=0.2)) == 0
