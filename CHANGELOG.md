# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-24

### Added
- **Domain Models & Scenario Validation**:
  - Microscopic vehicle kinematics, queuing, and saturation flow rate models.
  - Intersection topology with configurable approaches, lanes, directional movements, and crosswalks.
  - Multi-phase signal plan representations with Webster cycle time formulas, yellow clearance, and all-red intervals.
  - Cross-model collision-free scenario validation preventing conflicting simultaneous green indications and unserved movements.
- **Simulation Engine & Dynamics**:
  - Deterministic discrete-event simulation engine with micro-step precision.
  - Hierarchical seeded random number generation (`TrafficRNG`) ensuring 100% reproducible traffic experiments.
  - Stochastic vehicle arrivals via time-varying Poisson processes and step demand schedules.
  - Pedestrian arrivals, crosswalk queuing, pedestrian clearance intervals, and conflicting turn filtering.
  - Yellow-interval clearance and phase transition loss penalties.
- **Signal Controllers**:
  - `FixedTimeController`: Cyclic fixed-time scheduling with configurable phase splits.
  - `ActuatedController`: Gap-out headway detection and minimum green enforcement.
  - `MaxPressureController`: Network queue differential optimization balancing inflow and outflow spillbacks.
  - `DualRingController`: Standard NEMA TS-2 8-phase dual-ring barrier controller with concurrent ring synchronization.
- **Benchmarking & Analysis**:
  - Multi-controller comparative benchmark harness executing identical arrival streams.
  - Multi-seed statistical evaluator computing mean, standard deviation, and confidence intervals across seeds.
  - Real-time ASCII intersection terminal dashboard with queue bar charts.
  - Interactive standalone HTML5 Canvas simulation playback visualizer.
  - CSV and JSON step-by-step time series and summary metrics reporters.
- **Reinforcement Learning Interface**:
  - Gymnasium-compatible `JunctionEnv` with observation normalization, action mapping, and reward functions.
- **CLI & Preset Workflows**:
  - Console CLI `junction-sim` supporting `run`, `benchmark`, `presets`, and `visualize` subcommands.
  - Built-in scenarios: `webster_four_way`, `arterial_corridor`, `peak_hour_surge`, `bottleneck_spillback`.
