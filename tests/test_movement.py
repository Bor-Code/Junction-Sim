import pydantic
import pytest

from junction_sim.domain.movement import Movement, TurnType
from junction_sim.exceptions import InvalidGeometryError, ValidationError


def test_movement_creation_defaults() -> None:
    movement = Movement(
        id="N_T",
        origin="north",
        destination="south",
        turn_type=TurnType.THROUGH,
    )
    assert movement.id == "N_T"
    assert movement.origin == "north"
    assert movement.destination == "south"
    assert movement.turn_type == TurnType.THROUGH
    assert movement.saturation_flow_rate == 1800.0
    assert movement.discharge_rate_per_second == 0.5


def test_movement_custom_saturation_rate() -> None:
    movement = Movement(
        id="N_L",
        origin="north",
        destination="east",
        turn_type=TurnType.LEFT,
        saturation_flow_rate=1440.0,
    )
    assert movement.saturation_flow_rate == 1440.0
    assert movement.discharge_rate_per_second == 0.4


def test_turn_type_values() -> None:
    assert TurnType.LEFT.value == "left"
    assert TurnType.THROUGH.value == "through"
    assert TurnType.RIGHT.value == "right"
    assert TurnType.U_TURN.value == "u_turn"


def test_valid_u_turn_creation() -> None:
    movement = Movement(
        id="N_U",
        origin="north",
        destination="north",
        turn_type=TurnType.U_TURN,
    )
    assert movement.turn_type == TurnType.U_TURN
    assert movement.origin == movement.destination


def test_non_u_turn_same_origin_destination_raises() -> None:
    with pytest.raises(InvalidGeometryError):
        Movement(
            id="N_T",
            origin="north",
            destination="north",
            turn_type=TurnType.THROUGH,
        )


def test_u_turn_different_origin_destination_raises() -> None:
    with pytest.raises(InvalidGeometryError):
        Movement(
            id="N_U",
            origin="north",
            destination="south",
            turn_type=TurnType.U_TURN,
        )


def test_movement_blank_id_raises() -> None:
    with pytest.raises(ValidationError):
        Movement(
            id="   ",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
        )


def test_movement_blank_origin_raises() -> None:
    with pytest.raises(ValidationError):
        Movement(
            id="N_T",
            origin="   ",
            destination="south",
            turn_type=TurnType.THROUGH,
        )


def test_movement_blank_destination_raises() -> None:
    with pytest.raises(ValidationError):
        Movement(
            id="N_T",
            origin="north",
            destination="  ",
            turn_type=TurnType.THROUGH,
        )


def test_movement_empty_fields_pydantic_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        Movement(
            id="",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
        )

    with pytest.raises(pydantic.ValidationError):
        Movement(
            id="N_T",
            origin="",
            destination="south",
            turn_type=TurnType.THROUGH,
        )

    with pytest.raises(pydantic.ValidationError):
        Movement(
            id="N_T",
            origin="north",
            destination="",
            turn_type=TurnType.THROUGH,
        )


def test_movement_non_positive_saturation_rate_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        Movement(
            id="N_T",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=0.0,
        )

    with pytest.raises(pydantic.ValidationError):
        Movement(
            id="N_T",
            origin="north",
            destination="south",
            turn_type=TurnType.THROUGH,
            saturation_flow_rate=-500.0,
        )
