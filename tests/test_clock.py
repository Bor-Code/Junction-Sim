import pydantic
import pytest

from junction_sim.engine.clock import SimulationClock
from junction_sim.exceptions import InvalidStateError, ValidationError


def test_clock_defaults() -> None:
    clock = SimulationClock()
    assert clock.start_time == 0.0
    assert clock.step_size == 1.0
    assert clock.step_count == 0
    assert clock.current_time == 0.0


def test_clock_custom_start_and_step() -> None:
    clock = SimulationClock(start_time=10.0, step_size=0.5)
    assert clock.start_time == 10.0
    assert clock.step_size == 0.5
    assert clock.step_count == 0
    assert clock.current_time == 10.0


def test_clock_tick() -> None:
    clock = SimulationClock(step_size=1.0)
    ticked = clock.tick()

    assert clock.step_count == 0
    assert clock.current_time == 0.0

    assert ticked.step_count == 1
    assert ticked.current_time == 1.0


def test_clock_advance_multiple_steps() -> None:
    clock = SimulationClock(start_time=5.0, step_size=0.5)
    advanced = clock.advance(4)

    assert clock.step_count == 0
    assert advanced.step_count == 4
    assert advanced.current_time == 7.0


def test_clock_floating_point_precision() -> None:
    clock = SimulationClock(step_size=0.1)
    for _ in range(10):
        clock = clock.tick()
    assert clock.step_count == 10
    assert clock.current_time == 1.0


def test_clock_is_finished() -> None:
    clock = SimulationClock(start_time=0.0, step_size=1.0)
    assert not clock.is_finished(10.0)

    clock = clock.advance(9)
    assert not clock.is_finished(10.0)

    clock = clock.tick()
    assert clock.is_finished(10.0)

    clock = clock.tick()
    assert clock.is_finished(10.0)


def test_clock_is_finished_negative_duration_raises() -> None:
    clock = SimulationClock()
    with pytest.raises(ValidationError):
        clock.is_finished(-5.0)


def test_clock_advance_non_positive_steps_raises() -> None:
    clock = SimulationClock()
    with pytest.raises(InvalidStateError):
        clock.advance(0)

    with pytest.raises(InvalidStateError):
        clock.advance(-3)


def test_clock_invalid_parameters_raises() -> None:
    with pytest.raises(pydantic.ValidationError):
        SimulationClock(start_time=-1.0)

    with pytest.raises(pydantic.ValidationError):
        SimulationClock(step_size=0.0)

    with pytest.raises(pydantic.ValidationError):
        SimulationClock(step_size=-0.5)

    with pytest.raises(pydantic.ValidationError):
        SimulationClock(step_count=-1)
