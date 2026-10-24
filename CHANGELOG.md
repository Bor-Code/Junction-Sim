# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-10-24

### Added
- **Deep Q-Network (DQN) Signal Controller**:
  - Neural `DQNAgent` and `DQNController` with experience replay buffer, target network updates, and Huber loss.
  - CLI training support: `junction-sim train --algorithm dqn --episodes N`.
- **Autonomous CAV Space-Time Reservation Grid**:
  - `ReservationGrid` and `ReservationController` implementing Autonomous Intersection Management (AIM).
  - Fine-grained spatial cell and temporal interval conflict checking for Connected and Autonomous Vehicles (CAVs).
  - Zero-delay intersection crossing with eliminate inter-phase clearance waste.
- **OpenStreetMap (OSM) Importer**:
  - `build_scenario_from_osm` and `parse_osm_json` to import real-world geometry from Overpass API JSON exports.
  - CLI subcommand: `junction-sim import --osm <file> --node-id <id>`.
- **Automated CI/CD & Publishing**:
  - GitHub Pages deployment workflow (`.github/workflows/pages.yml`) hosting online interactive 3D simulation.
  - PyPI Trusted Publishing OIDC workflow (`.github/workflows/release.yml`) for automated package distribution.
- **Documentation & Benchmarking**:
  - Comprehensive CLI reference guide covering all 6 subcommands (`run`, `benchmark`, `presets`, `visualize`, `train`, `import`).
  - 6-controller multi-seed comparative benchmark on Webster Four-Way scenario.

## [0.2.0] - 2026-10-24

### Added
- **Photorealistic 3D WebGL Visualizer**:
  - Three.js visualizer with UnrealBloomPass post-processing, wet asphalt reflections, and dynamic headlights.
  - First-person cockpit telemetry HUD with digital speedometer, dynamic throttle/brake gauges, and G-meter.
  - Dynamic asphalt congestion heatmap overlay and emergency vehicle preemption mode.
- **Microscopic Traffic & IDM Car-Following**:
  - Continuous trajectory generation using the Intelligent Driver Model (IDM).
  - Driver personality profiles (`Cautious`, `Normal`, `Aggressive`).
- **VT-Micro Fuel & Emissions Model**:
  - Power-based fuel consumption rates (mL/s) and stoichiometric combustion CO2 emission rates (g/s).
- **Corridor Coordination & RL**:
  - Arterial green-wave progression controller (`CoordinatedSignalController`).
  - Tabular Q-learning controller (`QLearningController`) with serialization.

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
