import pytest

from junction_sim.domain.signal import SignalPhase
from junction_sim.engine.transition import PhaseTracker, SignalState
from junction_sim.exceptions import InvalidStateError, ValidationError


def create_sample_phase(
    phase_id: str = "P1",
    yellow_duration: float = 3.0,
    all_red_duration: float = 2.0,
) -> SignalPhase:
    return SignalPhase(
        id=phase_id,
        green_movement_ids=("N_T",),
        green_duration=20.0,
        yellow_duration=yellow_duration,
        all_red_duration=all_red_duration,
    )


def test_phase_tracker_initial_state() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    assert tracker.current_phase_id == "P1"
    assert tracker.state == SignalState.GREEN
    assert tracker.elapsed_in_state == 0.0
    assert tracker.target_phase_id is None
    assert tracker.is_green
    assert not tracker.is_yellow
    assert not tracker.is_all_red
    assert not tracker.is_in_transition
    assert tracker.can_discharge


def test_phase_tracker_step_in_green() -> None:
    phase = create_sample_phase("P1")
    tracker = PhaseTracker(current_phase_id="P1")

    tracker = tracker.step(1.0, phase)
    assert tracker.elapsed_in_state == 1.0
    assert tracker.is_green

    tracker = tracker.step(2.5, phase)
    assert tracker.elapsed_in_state == 3.5
    assert tracker.is_green


def test_phase_tracker_request_same_phase_ignored() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    same = tracker.request_phase_change("P1")
    assert same.is_green
    assert same.target_phase_id is None
    assert not same.is_in_transition


def test_phase_tracker_full_transition_cycle() -> None:
    phase1 = create_sample_phase("P1", yellow_duration=3.0, all_red_duration=2.0)
    tracker = PhaseTracker(current_phase_id="P1")

    tracker = tracker.request_phase_change("P2")
    assert tracker.is_yellow
    assert tracker.is_in_transition
    assert not tracker.can_discharge
    assert tracker.target_phase_id == "P2"
    assert tracker.elapsed_in_state == 0.0

    tracker = tracker.step(1.0, phase1)
    assert tracker.is_yellow
    assert tracker.elapsed_in_state == 1.0

    tracker = tracker.step(2.0, phase1)
    assert tracker.is_all_red
    assert tracker.elapsed_in_state == 0.0
    assert tracker.target_phase_id == "P2"

    tracker = tracker.step(1.0, phase1)
    assert tracker.is_all_red
    assert tracker.elapsed_in_state == 1.0

    tracker = tracker.step(1.0, phase1)
    assert tracker.is_green
    assert tracker.current_phase_id == "P2"
    assert tracker.target_phase_id is None
    assert tracker.elapsed_in_state == 0.0
    assert tracker.can_discharge
    assert not tracker.is_in_transition


def test_phase_tracker_transition_with_zero_all_red() -> None:
    phase1 = create_sample_phase("P1", yellow_duration=2.0, all_red_duration=0.0)
    tracker = PhaseTracker(current_phase_id="P1")

    tracker = tracker.request_phase_change("P2")
    assert tracker.is_yellow

    tracker = tracker.step(2.0, phase1)
    assert tracker.is_green
    assert tracker.current_phase_id == "P2"
    assert tracker.target_phase_id is None
    assert tracker.elapsed_in_state == 0.0


def test_phase_tracker_request_change_while_in_transition_raises() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    tracker = tracker.request_phase_change("P2")
    with pytest.raises(InvalidStateError):
        tracker.request_phase_change("P3")


def test_phase_tracker_blank_target_raises() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    with pytest.raises(ValidationError):
        tracker.request_phase_change("   ")


def test_phase_tracker_step_wrong_phase_raises() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    phase2 = create_sample_phase("P2")
    with pytest.raises(ValidationError):
        tracker.step(1.0, phase2)


def test_phase_tracker_step_invalid_step_size_raises() -> None:
    tracker = PhaseTracker(current_phase_id="P1")
    phase1 = create_sample_phase("P1")
    with pytest.raises(ValidationError):
        tracker.step(0.0, phase1)
    with pytest.raises(ValidationError):
        tracker.step(-1.0, phase1)


def test_phase_tracker_invalid_model_states_raises() -> None:
    with pytest.raises(ValidationError):
        PhaseTracker(current_phase_id="   ")

    with pytest.raises(ValidationError):
        PhaseTracker(current_phase_id="P1", target_phase_id="  ")

    with pytest.raises(InvalidStateError):
        PhaseTracker(
            current_phase_id="P1",
            state=SignalState.YELLOW,
            target_phase_id=None,
        )

    with pytest.raises(InvalidStateError):
        PhaseTracker(
            current_phase_id="P1",
            state=SignalState.ALL_RED,
            target_phase_id=None,
        )

    with pytest.raises(InvalidStateError):
        PhaseTracker(
            current_phase_id="P1",
            state=SignalState.GREEN,
            target_phase_id="P2",
        )
