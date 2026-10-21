import pydantic
import pytest

from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.exceptions import InvalidSignalPlanError


def test_signal_phase_creation_defaults() -> None:
    phase = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=30.0,
    )
    assert phase.id == "P1"
    assert phase.green_movement_ids == ("N_T", "S_T")
    assert phase.green_duration == 30.0
    assert phase.yellow_duration == 3.0
    assert phase.all_red_duration == 2.0
    assert phase.min_green == 5.0
    assert phase.max_green == 60.0
    assert phase.total_duration == 35.0


def test_signal_phase_custom_durations() -> None:
    phase = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=4.0,
        all_red_duration=1.5,
        min_green=10.0,
        max_green=40.0,
    )
    assert phase.green_duration == 20.0
    assert phase.yellow_duration == 4.0
    assert phase.all_red_duration == 1.5
    assert phase.total_duration == 25.5


def test_signal_phase_blank_id_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="   ",
            green_movement_ids=("N_T",),
            green_duration=20.0,
        )


def test_signal_phase_empty_movements_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=(),
            green_duration=20.0,
        )


def test_signal_phase_blank_movement_id_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T", "   "),
            green_duration=20.0,
        )


def test_signal_phase_duplicate_movement_ids_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T", "N_T"),
            green_duration=20.0,
        )


def test_signal_phase_max_green_less_than_min_green_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=15.0,
            min_green=20.0,
            max_green=10.0,
        )


def test_signal_phase_green_duration_less_than_min_green_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=3.0,
            min_green=5.0,
            max_green=30.0,
        )


def test_signal_phase_green_duration_exceeds_max_green_raises() -> None:
    with pytest.raises(InvalidSignalPlanError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=45.0,
            min_green=5.0,
            max_green=30.0,
        )


def test_signal_phase_negative_durations_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=0.0,
        )

    with pytest.raises(pydantic.ValidationError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=20.0,
            yellow_duration=-1.0,
        )

    with pytest.raises(pydantic.ValidationError):
        SignalPhase(
            id="P1",
            green_movement_ids=("N_T",),
            green_duration=20.0,
            all_red_duration=-1.0,
        )


def test_signal_plan_creation_valid() -> None:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T", "S_T"),
        green_duration=30.0,
        yellow_duration=3.0,
        all_red_duration=2.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T", "W_T"),
        green_duration=20.0,
        yellow_duration=3.0,
        all_red_duration=2.0,
    )

    plan = SignalPlan(
        id="plan_01",
        phases=(phase_1, phase_2),
    )

    assert plan.id == "plan_01"
    assert len(plan.phases) == 2
    assert plan.cycle_length == 60.0
    assert plan.get_phase("P1") == phase_1
    assert plan.get_phase("P2") == phase_2


def test_signal_plan_blank_id_raises() -> None:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        green_duration=20.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T",),
        green_duration=20.0,
    )

    with pytest.raises(InvalidSignalPlanError):
        SignalPlan(id="   ", phases=(phase_1, phase_2))


def test_signal_plan_fewer_than_two_phases_raises() -> None:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        green_duration=20.0,
    )

    with pytest.raises(InvalidSignalPlanError):
        SignalPlan(id="plan_01", phases=(phase_1,))


def test_signal_plan_duplicate_phase_ids_raises() -> None:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        green_duration=20.0,
    )
    phase_dup = SignalPhase(
        id="P1",
        green_movement_ids=("E_T",),
        green_duration=20.0,
    )

    with pytest.raises(InvalidSignalPlanError):
        SignalPlan(id="plan_01", phases=(phase_1, phase_dup))


def test_signal_plan_get_phase_not_found_raises() -> None:
    phase_1 = SignalPhase(
        id="P1",
        green_movement_ids=("N_T",),
        green_duration=20.0,
    )
    phase_2 = SignalPhase(
        id="P2",
        green_movement_ids=("E_T",),
        green_duration=20.0,
    )
    plan = SignalPlan(id="plan_01", phases=(phase_1, phase_2))

    with pytest.raises(InvalidSignalPlanError):
        plan.get_phase("UNKNOWN")
