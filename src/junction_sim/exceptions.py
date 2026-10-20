class JunctionSimError(Exception):
    pass


class ValidationError(JunctionSimError):
    pass


class ConfigurationError(ValidationError):
    pass


class InvalidGeometryError(ValidationError):
    pass


class InvalidSignalPlanError(ValidationError):
    pass


class SimulationError(JunctionSimError):
    pass


class ControllerError(SimulationError):
    pass


class InvalidStateError(SimulationError):
    pass
