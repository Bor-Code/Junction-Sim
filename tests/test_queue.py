import pytest

from junction_sim.domain.lane import Lane
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.queue import LaneQueue
from junction_sim.exceptions import InvalidStateError, ValidationError


def create_test_lane(max_capacity: int = 5) -> Lane:
    return Lane(
        id="lane_01",
        approach_id="north",
        allowed_movement_ids=("N_T",),
        max_capacity=max_capacity,
    )


def test_lane_queue_initial_state() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    assert queue.lane == lane
    assert queue.length == 0
    assert queue.is_empty
    assert not queue.is_full
    assert queue.peek() is None
    assert queue.discharge_credit == 0.0


def test_lane_queue_enqueue_fifo() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    veh1 = Vehicle(
        id="veh_01",
        origin="north",
        destination="south",
        arrival_time=1.0,
        target_lane_id="lane_01",
    )
    veh2 = Vehicle(
        id="veh_02",
        origin="north",
        destination="south",
        arrival_time=2.0,
        target_lane_id="lane_01",
    )

    queue.enqueue(veh1)
    assert queue.length == 1
    assert not queue.is_empty
    assert queue.peek() == veh1

    queue.enqueue(veh2)
    assert queue.length == 2
    assert queue.peek() == veh1


def test_lane_queue_target_lane_mismatch_raises() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    veh_wrong_lane = Vehicle(
        id="veh_01",
        origin="north",
        destination="south",
        arrival_time=1.0,
        target_lane_id="other_lane",
    )

    with pytest.raises(ValidationError):
        queue.enqueue(veh_wrong_lane)


def test_lane_queue_capacity_limit_raises() -> None:
    lane = create_test_lane(max_capacity=2)
    queue = LaneQueue(lane=lane)

    veh1 = Vehicle(id="veh_01", origin="north", destination="south", arrival_time=1.0)
    veh2 = Vehicle(id="veh_02", origin="north", destination="south", arrival_time=2.0)
    veh3 = Vehicle(id="veh_03", origin="north", destination="south", arrival_time=3.0)

    queue.enqueue(veh1)
    queue.enqueue(veh2)
    assert queue.is_full

    with pytest.raises(InvalidStateError):
        queue.enqueue(veh3)


def test_lane_queue_discharge_empty() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    discharged = queue.discharge(
        current_time=10.0, step_size=1.0, saturation_flow_rate=1800.0
    )
    assert discharged == ()
    assert queue.discharge_credit == 0.0


def test_lane_queue_discharge_headway_accumulation() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    veh1 = Vehicle(id="veh_01", origin="north", destination="south", arrival_time=0.0)
    veh2 = Vehicle(id="veh_02", origin="north", destination="south", arrival_time=0.0)
    queue.enqueue(veh1)
    queue.enqueue(veh2)

    discharged_step1 = queue.discharge(
        current_time=1.0, step_size=1.0, saturation_flow_rate=1800.0
    )
    assert discharged_step1 == ()
    assert queue.discharge_credit == 0.5
    assert queue.length == 2

    discharged_step2 = queue.discharge(
        current_time=2.0, step_size=1.0, saturation_flow_rate=1800.0
    )
    assert len(discharged_step2) == 1
    assert discharged_step2[0].id == "veh_01"
    assert discharged_step2[0].departure_time == 2.0
    assert discharged_step2[0].is_completed
    assert queue.length == 1
    assert queue.discharge_credit == 0.0

    discharged_step3 = queue.discharge(
        current_time=3.0, step_size=1.0, saturation_flow_rate=1800.0
    )
    assert discharged_step3 == ()
    assert queue.discharge_credit == 0.5

    discharged_step4 = queue.discharge(
        current_time=4.0, step_size=1.0, saturation_flow_rate=1800.0
    )
    assert len(discharged_step4) == 1
    assert discharged_step4[0].id == "veh_02"
    assert discharged_step4[0].departure_time == 4.0
    assert queue.is_empty
    assert queue.discharge_credit == 0.0


def test_lane_queue_discharge_multiple_in_single_step() -> None:
    lane = create_test_lane(max_capacity=5)
    queue = LaneQueue(lane=lane)

    for i in range(4):
        queue.enqueue(
            Vehicle(
                id=f"veh_{i}",
                origin="north",
                destination="south",
                arrival_time=0.0,
            )
        )

    discharged = queue.discharge(
        current_time=2.0, step_size=2.0, saturation_flow_rate=3600.0
    )
    assert len(discharged) == 2
    assert discharged[0].id == "veh_0"
    assert discharged[1].id == "veh_1"
    assert queue.length == 2
    assert queue.discharge_credit == 0.0


def test_lane_queue_reset_credit() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    veh1 = Vehicle(id="veh_01", origin="north", destination="south", arrival_time=0.0)
    queue.enqueue(veh1)

    queue.discharge(current_time=1.0, step_size=1.0, saturation_flow_rate=1800.0)
    assert queue.discharge_credit == 0.5

    queue.reset_credit()
    assert queue.discharge_credit == 0.0


def test_lane_queue_discharge_invalid_arguments_raises() -> None:
    lane = create_test_lane()
    queue = LaneQueue(lane=lane)

    with pytest.raises(ValidationError):
        queue.discharge(current_time=1.0, step_size=0.0, saturation_flow_rate=1800.0)

    with pytest.raises(ValidationError):
        queue.discharge(current_time=1.0, step_size=-1.0, saturation_flow_rate=1800.0)

    with pytest.raises(ValidationError):
        queue.discharge(current_time=1.0, step_size=1.0, saturation_flow_rate=0.0)

    with pytest.raises(ValidationError):
        queue.discharge(current_time=1.0, step_size=1.0, saturation_flow_rate=-500.0)

    with pytest.raises(ValidationError):
        queue.discharge(current_time=-1.0, step_size=1.0, saturation_flow_rate=1800.0)
