from junction_sim.benchmarks import (
    BenchmarkHarness,
    BenchmarkMetrics,
    BenchmarkResult,
    MultiSeedBenchmarkResult,
    MultiSeedMetrics,
)
from junction_sim.config import (
    CrosswalkConfig,
    PedestrianDemandConfig,
    ScenarioConfig,
    SimulationConfig,
    load_scenario_from_dict,
    load_scenario_from_file,
    load_scenario_from_json,
)
from junction_sim.controllers.actuated import ActuatedController
from junction_sim.controllers.dual_ring import DualRingController
from junction_sim.controllers.fixed_time import FixedTimeController
from junction_sim.controllers.max_pressure import MaxPressureController
from junction_sim.controllers.protocol import (
    ControllerContext,
    ControllerDecision,
    SignalController,
)
from junction_sim.controllers.reservation import (
    ReservationController,
    ReservationGrid,
)
from junction_sim.domain.approach import Approach
from junction_sim.domain.crosswalk import Crosswalk, PedestrianSignalState
from junction_sim.domain.direction import Direction
from junction_sim.domain.dual_ring import (
    DualRingStructure,
    NEMAPhase,
    build_nema_eight_phase_structure,
)
from junction_sim.domain.intersection import Intersection
from junction_sim.domain.lane import Lane
from junction_sim.domain.movement import Movement, TurnType
from junction_sim.domain.pedestrian import Pedestrian
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.domain.validation import (
    validate_signal_plan_against_intersection,
    validate_vehicle_against_intersection,
)
from junction_sim.domain.vehicle import Vehicle
from junction_sim.engine.arrival import (
    ArrivalGenerator,
    DemandInterval,
    DemandProfile,
    PedestrianArrivalGenerator,
    PedestrianDemandProfile,
)
from junction_sim.engine.clock import SimulationClock
from junction_sim.engine.engine import SimulationEngine
from junction_sim.engine.pedestrian_queue import PedestrianQueue
from junction_sim.engine.queue import LaneQueue
from junction_sim.engine.rng import TrafficRNG
from junction_sim.engine.step_result import StepResult
from junction_sim.engine.trajectories import (
    TrajectoryEngine,
    VehicleState3D,
    VehicleType,
)
from junction_sim.engine.transition import PhaseTracker, SignalState
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
from junction_sim.presets import (
    PresetInfo,
    build_arterial_corridor_preset,
    build_bottleneck_spillback_preset,
    build_peak_hour_surge_preset,
    build_webster_four_way_preset,
    get_preset,
    get_preset_info,
    list_presets,
    list_presets_info,
)
from junction_sim.reporting import (
    export_benchmark_to_csv,
    export_benchmark_to_json,
    export_multi_seed_benchmark_to_csv,
    export_multi_seed_benchmark_to_json,
    export_step_results_to_csv,
    export_step_results_to_json,
)
from junction_sim.rl import JunctionEnv, RLController
from junction_sim.visualization import (
    export_3d_html_visualizer,
    export_interactive_html,
    generate_3d_html_visualizer,
    generate_interactive_html,
    render_ascii_intersection,
    render_queue_bars,
    render_step_dashboard,
    serialize_simulation_data,
)

__version__ = "0.2.0"

__all__ = [
    "ActuatedController",
    "Approach",
    "ArrivalGenerator",
    "BenchmarkHarness",
    "BenchmarkMetrics",
    "BenchmarkResult",
    "ConfigurationError",
    "ControllerContext",
    "ControllerDecision",
    "ControllerError",
    "Crosswalk",
    "CrosswalkConfig",
    "DemandInterval",
    "DemandProfile",
    "Direction",
    "DualRingController",
    "DualRingStructure",
    "export_3d_html_visualizer",
    "export_benchmark_to_csv",
    "export_benchmark_to_json",
    "export_interactive_html",
    "export_multi_seed_benchmark_to_csv",
    "export_multi_seed_benchmark_to_json",
    "export_step_results_to_csv",
    "export_step_results_to_json",
    "FixedTimeController",
    "generate_3d_html_visualizer",
    "generate_interactive_html",
    "Intersection",
    "InvalidGeometryError",
    "InvalidSignalPlanError",
    "InvalidStateError",
    "JunctionEnv",
    "JunctionSimError",
    "Lane",
    "LaneQueue",
    "load_scenario_from_dict",
    "load_scenario_from_file",
    "load_scenario_from_json",
    "MaxPressureController",
    "Movement",
    "MultiSeedBenchmarkResult",
    "MultiSeedMetrics",
    "NEMAPhase",
    "Pedestrian",
    "PedestrianArrivalGenerator",
    "PedestrianDemandConfig",
    "PedestrianDemandProfile",
    "PedestrianQueue",
    "PedestrianSignalState",
    "PhaseTracker",
    "PresetInfo",
    "build_arterial_corridor_preset",
    "build_bottleneck_spillback_preset",
    "build_nema_eight_phase_structure",
    "build_peak_hour_surge_preset",
    "build_webster_four_way_preset",
    "get_preset",
    "get_preset_info",
    "list_presets",
    "list_presets_info",
    "ReservationController",
    "ReservationGrid",
    "RLController",
    "render_ascii_intersection",
    "render_queue_bars",
    "render_step_dashboard",
    "ScenarioConfig",
    "serialize_simulation_data",
    "SignalController",
    "SignalPhase",
    "SignalPlan",
    "SignalState",
    "SimulationClock",
    "SimulationConfig",
    "SimulationEngine",
    "SimulationError",
    "StepResult",
    "TrafficRNG",
    "TrajectoryEngine",
    "TurnType",
    "ValidationError",
    "Vehicle",
    "VehicleState3D",
    "VehicleType",
    "__version__",
    "validate_signal_plan_against_intersection",
    "validate_vehicle_against_intersection",
]
