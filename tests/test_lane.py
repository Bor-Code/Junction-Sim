import pydantic
import pytest

from junction_sim.domain.lane import Lane
from junction_sim.exceptions import ValidationError


def test_lane_creation_defaults() -> None:
    lane = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_T", "N_R"),
    )
    assert lane.id == "lane_n_0"
    assert lane.approach_id == "north"
    assert lane.allowed_movement_ids == ("N_T", "N_R")
    assert lane.length_meters == 150.0
    assert lane.max_capacity == 20
    assert lane.speed_limit_mps == 13.89


def test_lane_allows_movement() -> None:
    lane = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_T", "N_R"),
    )
    assert lane.allows_movement("N_T")
    assert lane.allows_movement("N_R")
    assert not lane.allows_movement("N_L")


def test_lane_blank_id_raises() -> None:
    with pytest.raises(ValidationError):
        Lane(
            id="   ",
            approach_id="north",
            allowed_movement_ids=("N_T",),
        )


def test_lane_blank_approach_id_raises() -> None:
    with pytest.raises(ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="  ",
            allowed_movement_ids=("N_T",),
        )


def test_lane_empty_movements_raises() -> None:
    with pytest.raises(ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=(),
        )


def test_lane_blank_movement_id_raises() -> None:
    with pytest.raises(ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T", "  "),
        )


def test_lane_duplicate_movements_raises() -> None:
    with pytest.raises(ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T", "N_T"),
        )


def test_lane_invalid_numbers_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T",),
            length_meters=0.0,
        )

    with pytest.raises(pydantic.ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T",),
            max_capacity=0,
        )

    with pytest.raises(pydantic.ValidationError):
        Lane(
            id="lane_n_0",
            approach_id="north",
            allowed_movement_ids=("N_T",),
            speed_limit_mps=-5.0,
        )
