import pytest

from junction_sim.exceptions import (
    ConfigurationError,
    ControllerError,
    InvalidGeometryError,
    InvalidSignalPlanError,
    InvalidStateError,
    JunctionSimError,
    SimulationError,
    ValidationError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(ValidationError, JunctionSimError)
    assert issubclass(ConfigurationError, ValidationError)
    assert issubclass(InvalidGeometryError, ValidationError)
    assert issubclass(InvalidSignalPlanError, ValidationError)

    assert issubclass(SimulationError, JunctionSimError)
    assert issubclass(ControllerError, SimulationError)
    assert issubclass(InvalidStateError, SimulationError)


def test_validation_error_catch() -> None:
    message = "invalid configuration provided"
    with pytest.raises(ValidationError) as exc_info:
        raise ConfigurationError(message)
    assert str(exc_info.value) == message
    assert isinstance(exc_info.value, JunctionSimError)


def test_geometry_error_catch() -> None:
    message = "overlapping movements detected"
    with pytest.raises(ValidationError) as exc_info:
        raise InvalidGeometryError(message)
    assert str(exc_info.value) == message
    assert isinstance(exc_info.value, JunctionSimError)


def test_signal_plan_error_catch() -> None:
    message = "green duration must be positive"
    with pytest.raises(ValidationError) as exc_info:
        raise InvalidSignalPlanError(message)
    assert str(exc_info.value) == message
    assert isinstance(exc_info.value, JunctionSimError)


def test_simulation_error_catch() -> None:
    message = "unknown controller: custom"
    with pytest.raises(SimulationError) as exc_info:
        raise ControllerError(message)
    assert str(exc_info.value) == message
    assert isinstance(exc_info.value, JunctionSimError)


def test_invalid_state_error_catch() -> None:
    message = "simulation time cannot decrease"
    with pytest.raises(SimulationError) as exc_info:
        raise InvalidStateError(message)
    assert str(exc_info.value) == message
    assert isinstance(exc_info.value, JunctionSimError)
