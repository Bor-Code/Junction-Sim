# junction-sim

A discrete-event traffic simulation and signal benchmarking library and CLI for signalized intersections.

---

## Overview

`junction-sim` provides a lightweight, deterministic discrete-event traffic simulation framework designed to evaluate and benchmark traffic signal control policies on isolated signalized intersections. Built with Python 3.12+ and Pydantic v2, it requires zero heavy dependencies, guarantees deterministic repeatability via hierarchical random number generation, and achieves 100% test and branch coverage.

---

## Key Features

- **Microscopic Traffic Mechanics**: Vehicle arrival Poisson processes, lane queue accumulation, queue capacity bounds, saturation flow discharge, and yellow-interval clearing.
- **Strict Geometric & Signal Validation**: Enforces directional consistency, lane-to-movement compatibility, conflicting movement separation, and multi-phase signal plan completeness before simulation execution.
- **Pluggable Signal Controllers**:
  - `FixedTimeController`: Cyclic phase sequencing with configurable green, yellow, and all-red durations based on Webster's cycle formulations.
  - `ActuatedController`: Dynamic green extension triggered by vehicle presence on detector zones, minimum green enforcement, and headway gap-out logic.
  - `MaxPressureController`: Pressure differential optimization across incoming and outgoing lane queues to maximize network throughput and prevent spillback.
- **Comparative Benchmarking Harness**: Simultaneous evaluation of multiple signal policies under identical demand profiles, computing throughput, completion rates, average delay, maximum queue, and wasted green time.
- **Visual Analytics**: Terminal ASCII intersection layout visualization, queue length bar charts, and step summary dashboards.
- **Standard Scenario Presets**: Built-in benchmark scenarios including Webster symmetric 4-way, asymmetric arterial corridors, peak-hour surges, and bottleneck spillback configurations.
- **CLI & Declarative Configs**: Command-line interface with `run`, `benchmark`, and `presets` subcommands alongside JSON and CSV time series exporters.

---

## Installation

### From Source

```bash
git clone https://github.com/Bor-Code/Junction-Sim.git
cd Junction-Sim
pip install .
```

### Development Installation

Using `uv`:

```bash
uv sync --all-extras
```

Or using standard `pip`:

```bash
pip install -e ".[dev]"
```

---

## Command Line Interface (CLI)

The package installs a console executable named `junction-sim`.

### 1. Run a Simulation

Execute a single-controller simulation using a built-in preset or a custom JSON configuration:

```bash
junction-sim run --preset webster_four_way --controller fixed-time --duration 300.0 --dashboard
```

Export detailed step-by-step metrics:

```bash
junction-sim run --preset arterial_corridor --controller max-pressure --out-csv run.csv --out-json run.json
```

### 2. Benchmark Controllers

Run an automated comparative benchmark across multiple signal controllers under identical demand:

```bash
junction-sim benchmark --preset peak_hour_surge --controllers fixed-time,actuated,max-pressure --duration 300.0
```

Export comparative benchmark summaries:

```bash
junction-sim benchmark --preset bottleneck_spillback --out-csv bench.csv --out-json bench.json
```

### 3. Inspect and Export Presets

List all available scenario presets:

```bash
junction-sim presets list
```

Export a preset to a standalone JSON configuration file for custom editing:

```bash
junction-sim presets export --preset webster_four_way --out my_scenario.json
```

---

## Python API Quickstart

### Running a Preset Simulation

```python
from junction_sim import (
    FixedTimeController,
    SimulationEngine,
    build_webster_four_way_preset,
    render_step_dashboard,
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

print(f"Executed {len(results)} steps.")
print(render_step_dashboard(results[-1], plan=signal_plan))
```

### Running a Benchmark

```python
from junction_sim import (
    ActuatedController,
    BenchmarkHarness,
    FixedTimeController,
    MaxPressureController,
    get_preset,
)

scenario = get_preset("arterial_corridor")
intersection, signal_plan, demands, sim_cfg = scenario.build_scenario()

controllers = {
    "fixed-time": FixedTimeController(signal_plan=signal_plan),
    "actuated": ActuatedController(signal_plan=signal_plan, intersection=intersection),
    "max-pressure": MaxPressureController(
        signal_plan=signal_plan, intersection=intersection
    ),
}

harness = BenchmarkHarness(
    intersection=intersection,
    signal_plan=signal_plan,
    demands=demands,
    step_size=sim_cfg.step_size,
    seed=sim_cfg.seed,
)

benchmark_result = harness.run_benchmark(controllers=controllers, duration=300.0)

print(f"Best by delay: {benchmark_result.best_by_delay}")
print(f"Best by throughput: {benchmark_result.best_by_throughput}")
for name, metrics in benchmark_result.metrics.items():
    print(
        f"{name}: avg delay = {metrics.average_delay:.2f}s, served = {metrics.total_discharges}"
    )
```

---

## Built-in Scenario Presets

| Preset Name | Description | Key Characteristic |
| :--- | :--- | :--- |
| `webster_four_way` | Classic symmetric 4-way intersection (Webster 1958) | Balanced 400 vph Poisson demand, 2-phase equal green |
| `arterial_corridor` | Arterial corridor with major street and cross-street | North-South 800 vph multi-lane, East-West 150 vph single-lane |
| `peak_hour_surge` | Saturated 4-way intersection under heavy surge demand | 850-900 vph per approach approaching saturation capacity |
| `bottleneck_spillback` | Geometry with restricted storage capacities | 15 vehicles/lane capacity testing spillback & queue blockage |

---

## Signal Control Policies

Detailed documentation on controller theory and algorithms is available in `docs/controllers.md`:

- **Fixed-Time (`fixed_time`)**: Time-of-day cyclic stage transitions. Predictable, baseline strategy suitable for steady demand.
- **Actuated (`actuated`)**: Extends green time as long as arriving vehicle headways are below vehicle extension threshold; gaps out when queues clear.
- **Max-Pressure (`max_pressure`)**: Calculates the queue pressure across phases ($P = Q_{in} - Q_{out}$) and selects the phase relieving maximal congestion.

---

## Documentation

- [CLI Reference Guide](docs/cli.md)
- [Signal Controller Policies](docs/controllers.md)
- [Scenario Configuration & Schema](docs/scenarios.md)

---

## Quality and Testing

The codebase adheres to strict engineering constraints:
- Static typing verified with `mypy --strict`.
- Formatted and linted with `ruff`.
- 100.00% statement and branch test coverage enforced via `pytest-cov`.

Run tests and verification locally:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src tests
uv run pytest --cov=junction_sim --cov-report=term-missing
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
