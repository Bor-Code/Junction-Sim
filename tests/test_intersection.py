import pytest

from junction_sim.domain.approach import Approach
from junction_sim.domain.direction import Direction
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.exceptions import InvalidGeometryError, ValidationError


def create_sample_intersection() -> Intersection:
    mov_n_t = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov_s_t = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )
    mov_e_t = Movement(
        id="E_T", origin="east", destination="west", turn_type=TurnType.THROUGH
    )

    lane_n = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_s = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))
    lane_e = Lane(id="lane_e_0", approach_id="east", allowed_movement_ids=("E_T",))

    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    app_e = Approach(id="east", direction=Direction.EAST, lanes=(lane_e,))

    conflicts = frozenset({frozenset({"N_T", "E_T"}), frozenset({"S_T", "E_T"})})

    return Intersection(
        id="int_01",
        approaches=(app_n, app_s, app_e),
        movements=(mov_n_t, mov_s_t, mov_e_t),
        conflicting_movement_pairs=conflicts,
    )


def test_intersection_creation_valid() -> None:
    inter = create_sample_intersection()
    assert inter.id == "int_01"
    assert len(inter.approaches) == 3
    assert len(inter.movements) == 3


def test_intersection_queries() -> None:
    inter = create_sample_intersection()

    app = inter.get_approach("north")
    assert app.id == "north"

    mov = inter.get_movement("N_T")
    assert mov.id == "N_T"

    lane = inter.get_lane("lane_e_0")
    assert lane.id == "lane_e_0"

    assert inter.are_conflicting("N_T", "E_T")
    assert inter.are_conflicting("E_T", "N_T")
    assert not inter.are_conflicting("N_T", "S_T")
    assert not inter.are_conflicting("N_T", "N_T")


def test_intersection_query_not_found_raises() -> None:
    inter = create_sample_intersection()

    with pytest.raises(InvalidGeometryError):
        inter.get_approach("unknown_app")

    with pytest.raises(InvalidGeometryError):
        inter.get_movement("unknown_mov")

    with pytest.raises(InvalidGeometryError):
        inter.get_lane("unknown_lane")


def test_intersection_blank_id_raises() -> None:
    inter = create_sample_intersection()
    with pytest.raises(ValidationError):
        Intersection(
            id="   ",
            approaches=inter.approaches,
            movements=inter.movements,
        )


def test_intersection_fewer_than_two_approaches_raises() -> None:
    inter = create_sample_intersection()
    with pytest.raises(ValidationError):
        Intersection(
            id="int_01",
            approaches=(inter.approaches[0],),
            movements=inter.movements,
        )


def test_intersection_duplicate_approach_ids_raises() -> None:
    lane_n1 = Lane(id="lane_n_0", approach_id="north", allowed_movement_ids=("N_T",))
    lane_n2 = Lane(id="lane_n_1", approach_id="north", allowed_movement_ids=("N_T",))
    app1 = Approach(id="north", direction=Direction.NORTH, lanes=(lane_n1,))
    app2 = Approach(id="north", direction=Direction.SOUTH, lanes=(lane_n2,))
    mov = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )

    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=(app1, app2),
            movements=(mov,),
        )


def test_intersection_duplicate_approach_directions_raises() -> None:
    lane_n1 = Lane(id="lane_n_0", approach_id="north_1", allowed_movement_ids=("N_T",))
    lane_n2 = Lane(id="lane_n_1", approach_id="north_2", allowed_movement_ids=("N_T",))
    app1 = Approach(id="north_1", direction=Direction.NORTH, lanes=(lane_n1,))
    app2 = Approach(id="north_2", direction=Direction.NORTH, lanes=(lane_n2,))
    mov = Movement(
        id="N_T", origin="north_1", destination="south", turn_type=TurnType.THROUGH
    )

    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=(app1, app2),
            movements=(mov,),
        )


def test_intersection_empty_movements_raises() -> None:
    inter = create_sample_intersection()
    with pytest.raises(ValidationError):
        Intersection(
            id="int_01",
            approaches=inter.approaches,
            movements=(),
        )


def test_intersection_duplicate_movement_ids_raises() -> None:
    inter = create_sample_intersection()
    mov_dup = Movement(
        id="N_T", origin="north", destination="east", turn_type=TurnType.LEFT
    )
    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=inter.approaches,
            movements=(inter.movements[0], mov_dup),
        )


def test_intersection_movement_origin_mismatch_raises() -> None:
    inter = create_sample_intersection()
    mov_bad = Movement(
        id="W_T", origin="west", destination="east", turn_type=TurnType.THROUGH
    )
    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=inter.approaches,
            movements=(inter.movements[0], mov_bad),
        )


def test_intersection_lane_unknown_movement_raises() -> None:
    lane_bad = Lane(
        id="lane_n_0", approach_id="north", allowed_movement_ids=("UNKNOWN",)
    )
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane_bad,))
    lane_s = Lane(id="lane_s_0", approach_id="south", allowed_movement_ids=("S_T",))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane_s,))
    mov = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )

    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=(app_n, app_s),
            movements=(mov,),
        )


def test_intersection_duplicate_lane_id_across_approaches_raises() -> None:
    lane1 = Lane(id="lane_shared", approach_id="north", allowed_movement_ids=("N_T",))
    lane2 = Lane(id="lane_shared", approach_id="south", allowed_movement_ids=("S_T",))
    app_n = Approach(id="north", direction=Direction.NORTH, lanes=(lane1,))
    app_s = Approach(id="south", direction=Direction.SOUTH, lanes=(lane2,))
    mov1 = Movement(
        id="N_T", origin="north", destination="south", turn_type=TurnType.THROUGH
    )
    mov2 = Movement(
        id="S_T", origin="south", destination="north", turn_type=TurnType.THROUGH
    )

    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=(app_n, app_s),
            movements=(mov1, mov2),
        )


def test_intersection_conflicting_pair_invalid_size_raises() -> None:
    inter = create_sample_intersection()
    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=inter.approaches,
            movements=inter.movements,
            conflicting_movement_pairs=frozenset({frozenset({"N_T"})}),
        )


def test_intersection_conflicting_pair_unknown_movement_raises() -> None:
    inter = create_sample_intersection()
    with pytest.raises(InvalidGeometryError):
        Intersection(
            id="int_01",
            approaches=inter.approaches,
            movements=inter.movements,
            conflicting_movement_pairs=frozenset({frozenset({"N_T", "UNKNOWN"})}),
        )
