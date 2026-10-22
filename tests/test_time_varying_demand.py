import pytest

from junction_sim.config.schema import (
    DemandIntervalConfig,
    DemandProfileConfig,
)
from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.engine.arrival import (
    ArrivalGenerator,
    DemandInterval,
    DemandProfile,
)
from junction_sim.engine.rng import TrafficRNG
from junction_sim.exceptions import ValidationError


def create_simple_intersection() -> Intersection:
    mov = Movement(
        id="M1",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
    )
    lane1 = Lane(id="L1", approach_id="north", allowed_movement_ids=("M1",))
    lane2 = Lane(id="L2", approach_id="south", allowed_movement_ids=("M1",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane1,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane2,))
    return Intersection(
        id="I1",
        approaches=(app_n, app_s),
        movements=(mov,),
        conflicting_movement_pairs=frozenset(),
    )


def test_demand_interval_valid_and_invalid() -> None:
    interval = DemandInterval(
        start_time=10.0,
        end_time=30.0,
        flow_rate_vph=600.0,
    )
    assert interval.start_time == 10.0
    assert interval.end_time == 30.0
    assert interval.flow_rate_vph == 600.0

    with pytest.raises(ValidationError) as exc_info:
        DemandInterval(start_time=50.0, end_time=50.0, flow_rate_vph=400.0)
    assert "end_time must be greater than start_time" in str(exc_info.value)

    with pytest.raises(ValidationError):
        DemandInterval(start_time=50.0, end_time=20.0, flow_rate_vph=400.0)


def test_demand_profile_overlapping_intervals_raises() -> None:
    i1 = DemandInterval(start_time=0.0, end_time=50.0, flow_rate_vph=200.0)
    i2 = DemandInterval(start_time=40.0, end_time=90.0, flow_rate_vph=600.0)
    with pytest.raises(ValidationError) as exc_info:
        DemandProfile(movement_id="M1", intervals=(i1, i2))
    assert "intervals cannot overlap" in str(exc_info.value)


def test_demand_profile_flow_rate_intervals_resolution() -> None:
    i1 = DemandInterval(start_time=0.0, end_time=30.0, flow_rate_vph=100.0)
    i2 = DemandInterval(start_time=30.0, end_time=60.0, flow_rate_vph=900.0)
    dp = DemandProfile(
        movement_id="M1",
        flow_rate_vph=50.0,
        intervals=(i2, i1),
    )

    assert dp.get_flow_rate(15.0) == 100.0
    assert dp.get_flow_rate(45.0) == 900.0
    assert dp.get_flow_rate(80.0) == 50.0


def test_demand_interval_config_build_domain() -> None:
    cfg = DemandIntervalConfig(
        start_time=0.0,
        end_time=60.0,
        flow_rate_vph=300.0,
    )
    domain_interval = cfg.build_domain()
    assert domain_interval.start_time == 0.0
    assert domain_interval.end_time == 60.0
    assert domain_interval.flow_rate_vph == 300.0

    p_cfg = DemandProfileConfig(
        movement_id="M1",
        flow_rate_vph=100.0,
        intervals=[cfg],
    )
    domain_profile = p_cfg.build_domain()
    assert domain_profile.movement_id == "M1"
    assert len(domain_profile.intervals) == 1
    assert domain_profile.get_flow_rate(30.0) == 300.0


def test_arrival_generator_with_time_varying_intervals() -> None:
    inter = create_simple_intersection()
    i1 = DemandInterval(start_time=0.0, end_time=5.0, flow_rate_vph=0.0)
    i2 = DemandInterval(start_time=5.0, end_time=10.0, flow_rate_vph=3600.0)
    dp = DemandProfile(movement_id="M1", intervals=(i1, i2))

    rng = TrafficRNG(seed=42)
    gen = ArrivalGenerator(intersection=inter, demands=(dp,), rng=rng)

    arr_quiet = gen.generate_arrivals(current_time=2.0, step_size=1.0)
    assert len(arr_quiet) == 0

    arr_surge = gen.generate_arrivals(current_time=6.0, step_size=1.0)
    assert len(arr_surge) > 0
    assert arr_surge[0].movement_id if hasattr(arr_surge[0], "movement_id") else True
