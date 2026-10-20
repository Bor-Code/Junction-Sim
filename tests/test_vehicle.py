import pydantic
import pytest

from junction_sim.domain.vehicle import Vehicle
from junction_sim.exceptions import (
    InvalidGeometryError,
    InvalidStateError,
    ValidationError,
)


def test_vehicle_creation_defaults() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.5,
    )
    assert veh.id == "veh_001"
    assert veh.origin == "north"
    assert veh.destination == "south"
    assert veh.arrival_time == 10.5
    assert veh.departure_time is None
    assert veh.target_lane_id is None
    assert not veh.is_completed


def test_vehicle_creation_with_optional_fields() -> None:
    veh = Vehicle(
        id="veh_002",
        origin="east",
        destination="west",
        arrival_time=5.0,
        departure_time=15.0,
        target_lane_id="lane_east_0",
    )
    assert veh.departure_time == 15.0
    assert veh.target_lane_id == "lane_east_0"
    assert veh.is_completed


def test_vehicle_blank_id_raises() -> None:
    with pytest.raises(ValidationError):
        Vehicle(id="   ", origin="north", destination="south", arrival_time=0.0)


def test_vehicle_blank_origin_raises() -> None:
    with pytest.raises(ValidationError):
        Vehicle(id="veh_001", origin=" ", destination="south", arrival_time=0.0)


def test_vehicle_blank_destination_raises() -> None:
    with pytest.raises(ValidationError):
        Vehicle(id="veh_001", origin="north", destination="   ", arrival_time=0.0)


def test_vehicle_same_origin_destination_raises() -> None:
    with pytest.raises(InvalidGeometryError):
        Vehicle(
            id="veh_001",
            origin="north",
            destination="north",
            arrival_time=0.0,
        )


def test_vehicle_negative_arrival_time_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        Vehicle(
            id="veh_001",
            origin="north",
            destination="south",
            arrival_time=-1.0,
        )


def test_vehicle_departure_before_arrival_raises() -> None:
    with pytest.raises(ValidationError):
        Vehicle(
            id="veh_001",
            origin="north",
            destination="south",
            arrival_time=10.0,
            departure_time=5.0,
        )


def test_waiting_time_pending_vehicle() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
    )
    assert veh.waiting_time(10.0) == 0.0
    assert veh.waiting_time(25.5) == 15.5


def test_waiting_time_completed_vehicle() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
        departure_time=18.0,
    )
    assert veh.waiting_time(30.0) == 8.0


def test_waiting_time_earlier_than_arrival_raises() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
    )
    with pytest.raises(InvalidStateError):
        veh.waiting_time(5.0)


def test_with_departure_creates_new_instance() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
    )
    departed = veh.with_departure(20.0)

    assert veh.departure_time is None
    assert not veh.is_completed

    assert departed.id == "veh_001"
    assert departed.arrival_time == 10.0
    assert departed.departure_time == 20.0
    assert departed.is_completed


def test_with_departure_already_departed_raises() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
        departure_time=20.0,
    )
    with pytest.raises(InvalidStateError):
        veh.with_departure(25.0)


def test_with_departure_before_arrival_raises() -> None:
    veh = Vehicle(
        id="veh_001",
        origin="north",
        destination="south",
        arrival_time=10.0,
    )
    with pytest.raises(InvalidStateError):
        veh.with_departure(5.0)
