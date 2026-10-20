import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.lane import Lane
from junction_sim.exceptions import InvalidGeometryError, ValidationError


def test_approach_creation_valid() -> None:
    lane_0 = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_L",),
    )
    lane_1 = Lane(
        id="lane_n_1",
        approach_id="north",
        allowed_movement_ids=("N_T", "N_R"),
    )
    approach = Approach(
        id="north",
        direction=Direction.NORTH,
        lanes=(lane_0, lane_1),
    )

    assert approach.id == "north"
    assert approach.direction == Direction.NORTH
    assert len(approach.lanes) == 2


def test_approach_get_lane() -> None:
    lane_0 = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_L",),
    )
    approach = Approach(
        id="north",
        direction=Direction.NORTH,
        lanes=(lane_0,),
    )

    assert approach.get_lane("lane_n_0") == lane_0

    with pytest.raises(InvalidGeometryError):
        approach.get_lane("lane_n_99")


def test_approach_get_lanes_for_movement() -> None:
    lane_0 = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_L",),
    )
    lane_1 = Lane(
        id="lane_n_1",
        approach_id="north",
        allowed_movement_ids=("N_T",),
    )
    lane_2 = Lane(
        id="lane_n_2",
        approach_id="north",
        allowed_movement_ids=("N_T", "N_R"),
    )
    approach = Approach(
        id="north",
        direction=Direction.NORTH,
        lanes=(lane_0, lane_1, lane_2),
    )

    through_lanes = approach.get_lanes_for_movement("N_T")
    assert through_lanes == (lane_1, lane_2)

    left_lanes = approach.get_lanes_for_movement("N_L")
    assert left_lanes == (lane_0,)

    u_turn_lanes = approach.get_lanes_for_movement("N_U")
    assert u_turn_lanes == ()


def test_approach_blank_id_raises() -> None:
    lane_0 = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_L",),
    )
    with pytest.raises(ValidationError):
        Approach(
            id="   ",
            direction=Direction.NORTH,
            lanes=(lane_0,),
        )


def test_approach_empty_lanes_raises() -> None:
    with pytest.raises(ValidationError):
        Approach(
            id="north",
            direction=Direction.NORTH,
            lanes=(),
        )


def test_approach_duplicate_lane_ids_raises() -> None:
    lane_0 = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_L",),
    )
    lane_dup = Lane(
        id="lane_n_0",
        approach_id="north",
        allowed_movement_ids=("N_T",),
    )
    with pytest.raises(InvalidGeometryError):
        Approach(
            id="north",
            direction=Direction.NORTH,
            lanes=(lane_0, lane_dup),
        )


def test_approach_lane_approach_id_mismatch_raises() -> None:
    lane_wrong = Lane(
        id="lane_s_0",
        approach_id="south",
        allowed_movement_ids=("S_T",),
    )
    with pytest.raises(InvalidGeometryError):
        Approach(
            id="north",
            direction=Direction.NORTH,
            lanes=(lane_wrong,),
        )
