import pydantic
import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.validation import validate_vehicle_against_intersection
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.arrival import ArrivalGenerator, DemandProfile
from junction_sim.engine.rng import TrafficRNG
from junction_sim.exceptions import InvalidGeometryError, ValidationError


def create_sample_intersection() -> Intersection:
    mov_n_t = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_s_t = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )

    lane_n_0 = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_n_1 = Lane(id="lane_n_1", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s_0 = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n_0, lane_n_1))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s_0,))

    return Intersection(
        id="int_01",
        approaches=(app_n, app_s),
        movements=(mov_n_t, mov_s_t),
    )


def test_demand_profile_creation() -> None:
    dp = DemandProfile(movement_id="N_T", flow_rate_vph=600.0)
    assert dp.movement_id == "N_T"
    assert dp.flow_rate_vph == 600.0


def test_demand_profile_blank_movement_raises() -> None:
    with pytest.raises(ValidationError):
        DemandProfile(movement_id="   ", flow_rate_vph=500.0)


def test_demand_profile_negative_flow_rate_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        DemandProfile(movement_id="N_T", flow_rate_vph=-10.0)


def test_arrival_generator_duplicate_demand_raises() -> None:
    inter = create_sample_intersection()
    rng = TrafficRNG(seed=42)
    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=300.0),
        DemandProfile(movement_id="N_T", flow_rate_vph=400.0),
    )
    with pytest.raises(ValidationError):
        ArrivalGenerator(intersection=inter, demands=demands, rng=rng)


def test_arrival_generator_unknown_movement_raises() -> None:
    inter = create_sample_intersection()
    rng = TrafficRNG(seed=42)
    demands = (DemandProfile(movement_id="UNKNOWN", flow_rate_vph=300.0),)
    with pytest.raises(InvalidGeometryError):
        ArrivalGenerator(intersection=inter, demands=demands, rng=rng)


def test_arrival_generator_no_lane_for_movement_raises() -> None:
    mov_n_t = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_n_l = Movement(
        id="N_L", origin="north", destination="east", turn_type=TurnType.LEFT
    )
    mov_s_t = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )

    lane_n_0 = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s_0 = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n_0,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s_0,))

    inter = Intersection(
        id="int_no_lane",
        approaches=(app_n, app_s),
        movements=(mov_n_t, mov_n_l, mov_s_t),
    )
    rng = TrafficRNG(seed=42)
    demands = (DemandProfile(movement_id="N_L", flow_rate_vph=200.0),)

    with pytest.raises(InvalidGeometryError):
        ArrivalGenerator(intersection=inter, demands=demands, rng=rng)


def test_arrival_generator_zero_demand() -> None:
    inter = create_sample_intersection()
    rng = TrafficRNG(seed=42)
    demands = (DemandProfile(movement_id="N_T", flow_rate_vph=0.0),)
    gen = ArrivalGenerator(intersection=inter, demands=demands, rng=rng)

    assert gen.demands == demands
    assert gen.vehicle_counter == 0

    for _ in range(10):
        vehicles = gen.generate_arrivals(current_time=0.0, step_size=1.0)
        assert vehicles == ()
    assert gen.vehicle_counter == 0


def test_arrival_generator_reproducibility() -> None:
    inter = create_sample_intersection()
    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=1800.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=900.0),
    )

    gen1 = ArrivalGenerator(
        intersection=inter, demands=demands, rng=TrafficRNG(seed=42)
    )
    gen2 = ArrivalGenerator(
        intersection=inter, demands=demands, rng=TrafficRNG(seed=42)
    )

    batch1 = gen1.generate_arrivals(current_time=1.0, step_size=1.0)
    batch2 = gen2.generate_arrivals(current_time=1.0, step_size=1.0)

    assert batch1 == batch2
    assert gen1.vehicle_counter == gen2.vehicle_counter


def test_arrival_generator_vehicles_valid_against_intersection() -> None:
    inter = create_sample_intersection()
    demands = (
        DemandProfile(movement_id="N_T", flow_rate_vph=3600.0),
        DemandProfile(movement_id="S_T", flow_rate_vph=1800.0),
    )
    gen = ArrivalGenerator(
        intersection=inter, demands=demands, rng=TrafficRNG(seed=100)
    )

    all_vehicles: list[Vehicle] = []
    for t in range(10):
        vehicles = gen.generate_arrivals(current_time=float(t), step_size=1.0)
        for veh in vehicles:
            validate_vehicle_against_intersection(veh, inter)
            assert veh.arrival_time == float(t)
            assert veh.target_lane_id in ("lane_n_0", "lane_n_1", "lane_s_0")
        all_vehicles.extend(vehicles)

    assert len(all_vehicles) > 0
    assert gen.vehicle_counter == len(all_vehicles)


def test_arrival_generator_invalid_step_size_raises() -> None:
    inter = create_sample_intersection()
    gen = ArrivalGenerator(
        intersection=inter,
        demands=(DemandProfile(movement_id="N_T", flow_rate_vph=300.0),),
        rng=TrafficRNG(seed=42),
    )
    with pytest.raises(ValidationError):
        gen.generate_arrivals(current_time=0.0, step_size=0.0)

    with pytest.raises(ValidationError):
        gen.generate_arrivals(current_time=0.0, step_size=-1.0)


def test_arrival_generator_negative_current_time_raises() -> None:
    inter = create_sample_intersection()
    gen = ArrivalGenerator(
        intersection=inter,
        demands=(DemandProfile(movement_id="N_T", flow_rate_vph=300.0),),
        rng=TrafficRNG(seed=42),
    )
    with pytest.raises(ValidationError):
        gen.generate_arrivals(current_time=-1.0, step_size=1.0)
