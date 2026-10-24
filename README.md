# junction-sim

A discrete-event traffic simulation, microscopic kinematics engine, and signal benchmarking platform for signalized intersections.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Coverage](https://img.shields.io/badge/coverage-100.00%25-brightgreen.svg)]()
[![Version](https://img.shields.io/badge/release-v0.3.0-blue.svg)]()
[![PyPI](https://img.shields.io/pypi/v/junction-sim.svg)](https://pypi.org/project/junction-sim/)
[![Live Demo](https://img.shields.io/badge/demo-online_3D_simulation-brightgreen.svg)](https://bor-code.github.io/Junction-Sim/)

---

![Junction-Sim 3D WebGL Photorealistic Simulation](docs/assets/visualizer_showcase.jpg)

## Overview

`junction-sim` is a high-performance discrete-event traffic simulation and signal benchmarking framework built with Python 3.12+ and Pydantic v2. Designed for transportation researchers, traffic engineers, and machine learning practitioners, it combines rigorous queuing theory, microscopic vehicle kinematics (IDM), power-based fuel consumption & CO2 emissions modeling, and photorealistic 3D WebGL visualization with 100% test and branch coverage.

---

## Quick Start

### 1. Installation

```bash
uv sync --all-extras
# or using pip:
pip install -e ".[dev]"
```

### 2. Launch 3D Visualizer

Run a Webster 4-way intersection simulation and view it live in your browser:

```bash
junction-sim visualize --preset webster_four_way --controller actuated --duration 60.0 --mode 3d --open
```

### 3. Run a Benchmark

Compare signal controllers under identical Poisson arrivals:

```bash
junction-sim benchmark --preset webster_four_way --controllers fixed-time,actuated,max-pressure,reservation,dqn --seeds 42 --duration 100.0
```

---

## Core Capabilities

| Capability | Highlights |
| :--- | :--- |
| **Microscopic Kinematics** | Continuous trajectory generation via the Intelligent Driver Model (IDM) with Cautious, Normal, and Aggressive driver personalities, turn indicators, and collision-free braking. |
| **Signal Controllers** | Six production controllers: Fixed-Time, Actuated (gap/extension), Max-Pressure, Coordinated Arterial Green-Wave, Autonomous CAV Space-Time Reservation, and Deep Q-Networks (DQN). |
| **Environmental Impact** | VT-Micro instantaneous power-based fuel consumption (mL/s) and stoichiometric combustion CO2 emission rates (g/s) with heavy-vehicle differentiation. |
| **3D WebGL Visualizer** | Three.js visualizer with bloom post-processing, wet asphalt reflections, dynamic congestion heatmaps, emergency vehicle preemption, and first-person cockpit telemetry HUD. |
| **Real-World OSM Import** | Seamless conversion of raw OpenStreetMap Overpass API JSON exports into structured junction geometries and lane connectivity. |
| **Multi-Intersection Networks** | Interconnected arterial corridors and grid networks with inter-node road links, transit buffers, and link travel time delay modeling. |

---

## 3D Visualizer & Cockpit HUD

The browser-based 3D visualizer (`visualizer.html`) provides real-time interactive controls, camera views, and live telemetry:

![Cockpit HUD Telemetry with Speedometer and Dynamic Gauges](docs/assets/cockpit_hud_showcase.jpg)

### Keyboard Shortcuts

| Key | Mode | Function |
| :---: | :--- | :--- |
| `C` | **Cinematic Camera** | Sweeping, orbiting aerial view of the junction |
| `O` | **Orbit Camera** | Free orbital camera (left-click rotate, right-click pan, scroll zoom) |
| `F` | **Follow Camera** | Third-person dynamic pursuit camera tracking lead vehicles |
| `D` | **Cockpit HUD** | First-person driver cockpit with digital speedometer and telemetry gauges |
| `H` | **Heatmap Overlay** | Toggles asphalt queue congestion heatmap (Green to Red) |
| `M` | **Manual Control** | Interactive signal override panel to force phase switches |
| `E` | **Emergency Preempt** | Dispatches an emergency ambulance with strobe beacons and green priority |
| `G` | **CAV Grid** | Toggles the autonomous vehicle conflict-zone space-time reservation grid |
| `Space` | **Play / Pause** | Toggles simulation playback |
| `1` - `4` | **Playback Speed** | Sets playback speed to 0.5x, 1x, 2x, or 4x |

---

## Benchmark Performance

Performance comparison across 6 controllers on the standard Webster Four-Way scenario (100-second horizon):

| Controller | Served (veh) | Completion Rate | Avg Delay (s) | Fuel Consumed (L) | CO2 Emitted (kg) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Actuated** | 51 | 87.93% | 8.22 | 1.61 L | 3.85 kg |
| **Max-Pressure** | 46 | 79.31% | 10.98 | 1.57 L | 3.75 kg |
| **Fixed-Time** | 50 | 86.21% | 14.76 | 1.61 L | 3.86 kg |
| **DQN** | 35 | 60.34% | 7.94 | 1.22 L | 2.91 kg |
| **Q-Learning** | 35 | 60.34% | 16.43 | 1.25 L | 2.98 kg |
| **Reservation (CAV)** | 35 | 60.34% | 19.17 | 1.24 L | 2.95 kg |

For arterial corridor green-wave benchmarks and multi-seed statistical evaluation, see [docs/cli.md](docs/cli.md).

---

## CLI Reference

`junction-sim` provides a unified command line interface. For full option details, see [docs/cli.md](docs/cli.md).

| Subcommand | Description | Example Command |
| :--- | :--- | :--- |
| `visualize` | Generate and view 3D/2D simulations | `junction-sim visualize --preset webster_four_way --mode 3d --open` |
| `benchmark` | Compare multiple controllers across seeds | `junction-sim benchmark --preset webster_four_way --controllers fixed-time,actuated` |
| `train` | Train reinforcement learning agents (Q-Learning / DQN) | `junction-sim train --preset webster_four_way --algorithm dqn --episodes 20` |
| `run` | Headless simulation execution with metrics export | `junction-sim run --preset webster_four_way --controller actuated --out-json run.json` |
| `import` | Import real-world intersections from OpenStreetMap | `junction-sim import --osm junction.json --node-id 1001 --out scenario.json` |
| `presets` | List and export built-in scenario configurations | `junction-sim presets list` |

---

## Python API Quickstart

```python
from junction_sim import (
    FixedTimeController,
    SimulationEngine,
    TrajectoryEngine,
    build_webster_four_way_preset,
)

scenario = build_webster_four_way_preset()
intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()
controller = FixedTimeController(signal_plan=signal_plan)

engine = SimulationEngine(
    intersection=intersection,
    signal_plan=signal_plan,
    demands=demands,
    controller=controller,
    step_size=sim_cfg.step_size,
    seed=sim_cfg.seed,
)
results = engine.run(duration=60.0)

traj_engine = TrajectoryEngine(intersection=intersection, signal_plan=signal_plan)
trajectories = traj_engine.generate_vehicle_states(results=results, step_size=0.1)
print(f"Generated {len(trajectories)} trajectory states across {len(results)} steps.")
```

---

## Scenario Presets

| Preset Name | Description | Traffic Demand |
| :--- | :--- | :--- |
| `webster_four_way` | Symmetric 4-way intersection (Webster 1958) | Balanced 400 vph Poisson demand |
| `arterial_corridor` | Arterial corridor with major/minor cross-streets | North-South 800 vph, East-West 150 vph |
| `peak_hour_surge` | Saturated 4-way intersection under heavy surge demand | 850-900 vph per approach |
| `bottleneck_spillback` | Geometry with restricted storage capacities | 15 vehicles/lane storage limit |

---

## Quality and Verification

- **Type Safety**: Strictly enforced via `mypy --strict`.
- **Style & Linting**: Verified with `ruff`.
- **Test Coverage**: 100.00% statement and branch coverage enforced via `pytest-cov` (399 tests).

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest --cov=junction_sim --cov-branch --cov-fail-under=100
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
