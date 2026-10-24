# CLI Reference Guide

`junction-sim` provides a unified command line interface for discrete-event traffic simulations, signal controller benchmarking, model training, OpenStreetMap imports, and interactive 3D WebGL visualizations.

---

## Global Options

```bash
junction-sim [--version] [-v] [--help] [-h] <subcommand>
```

| Flag | Short | Description |
| :--- | :--- | :--- |
| `--version` | `-v` | Display the installed version of `junction-sim` and exit. |
| `--help` | `-h` | Display global help information and exit. |

---

## Subcommands

### 1. `run`

Executes a single simulation run using a specified controller and scenario configuration.

```bash
junction-sim run (-c CONFIG | -p PRESET) [options]
```

#### Arguments and Options

| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--config` | `-c` | string | None | Path to scenario JSON configuration file. Mutually exclusive with `--preset`. |
| `--preset` | `-p` | choice | None | Name of standard preset scenario (`webster_four_way`, `arterial_corridor`, `peak_hour_surge`, `bottleneck_spillback`). |
| `--controller` | | choice | `fixed-time` | Signal control policy to execute: `fixed-time`, `actuated`, `max-pressure`, `dual-ring`, `q-learning`, `dqn`, `reservation`, `coordinated`. |
| `--duration` | `-d` | float | None | Simulation duration in seconds (overrides scenario setting). |
| `--seed` | `-s` | integer | None | Random number generator seed (overrides scenario setting). |
| `--dashboard` | | flag | False | Render terminal ASCII intersection layout and queue bar charts for the final simulation step. |
| `--out-csv` | | string | None | Destination path to export step-by-step CSV time series. |
| `--out-json` | | string | None | Destination path to export detailed simulation execution summary in JSON format. |
| `--out-html` | | string | None | Destination path to export interactive 2D HTML visualizer. |
| `--out-html-3d` | | string | None | Destination path to export photorealistic 3D WebGL visualizer. |

#### Examples

Running a preset with terminal ASCII dashboard:

```bash
junction-sim run --preset arterial_corridor --controller max-pressure --duration 120.0 --dashboard
```

Running an autonomous CAV reservation grid simulation:

```bash
junction-sim run --preset webster_four_way --controller reservation --duration 100.0 --out-json run_cav.json
```

---

### 2. `benchmark`

Runs an automated comparative benchmark across multiple signal controllers under identical demand seeds and duration.

```bash
junction-sim benchmark (-c CONFIG | -p PRESET) [options]
```

#### Arguments and Options

| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--config` | `-c` | string | None | Path to scenario JSON configuration file. Mutually exclusive with `--preset`. |
| `--preset` | `-p` | choice | None | Name of standard preset scenario to benchmark. |
| `--controllers` | | string | `fixed-time,actuated,max-pressure` | Comma-separated list of controllers to benchmark. Supports `fixed-time`, `actuated`, `max-pressure`, `coordinated`, `q-learning`, `dqn`, `reservation`. |
| `--duration` | `-d` | float | None | Simulation duration in seconds (overrides scenario setting). |
| `--seed` | `-s` | integer | None | Base random number generator seed. |
| `--num-seeds` | | integer | None | Execute multi-seed evaluation across N consecutive seeds. |
| `--seeds` | | string | None | Comma-separated list of RNG seeds for multi-seed statistical evaluation. |
| `--out-csv` | | string | None | Destination path to export benchmark summary CSV. |
| `--out-json` | | string | None | Destination path to export benchmark summary JSON. |

#### Example

```bash
junction-sim benchmark --preset webster_four_way --controllers fixed-time,actuated,max-pressure,q-learning,dqn,reservation --seeds 42 --duration 100.0 --out-json bench.json
```

---

### 3. `train`

Trains a reinforcement learning agent (`q-learning` tabular or `dqn` Deep Q-Network) within the `JunctionEnv` simulation environment.

```bash
junction-sim train (-c CONFIG | -p PRESET) [options]
```

#### Arguments and Options

| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--config` | `-c` | string | None | Path to scenario JSON configuration file. Mutually exclusive with `--preset`. |
| `--preset` | `-p` | choice | None | Name of scenario preset to train on (`webster_four_way`, etc.). |
| `--algorithm` | `-a` | choice | `q-learning` | RL algorithm to train: `q-learning` or `dqn`. |
| `--episodes` | `-e` | integer | 10 | Number of training episodes. |
| `--reward-type` | | choice | `queue_penalty` | Reward function formulation: `queue_penalty`, `delay_penalty`, `throughput`. |
| `--out-model` | `-o` | string | None | Destination path to save trained model JSON policy weights. |

#### Examples

Training a Deep Q-Network controller:

```bash
junction-sim train --preset webster_four_way --algorithm dqn --episodes 20 --reward-type queue_penalty --out-model dqn_policy.json
```

Training a tabular Q-learning controller:

```bash
junction-sim train --preset arterial_corridor --algorithm q-learning --episodes 50 --out-model q_policy.json
```

---

### 4. `import`

Imports real-world intersection geometry directly from an OpenStreetMap Overpass JSON export file and generates a ready-to-run scenario.

```bash
junction-sim import --osm OSM_FILE --node-id NODE_ID [options]
```

#### Arguments and Options

| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--osm` | | string | Required | Path to OpenStreetMap Overpass API JSON export file. |
| `--node-id` | | integer | Required | Center OSM node ID representing the junction crossroads. |
| `--junction-id` | | string | `osm_junction` | Identifier for the generated intersection. |
| `--out` | `-o` | string | None | Destination path to save the generated scenario JSON. |

#### Example

```bash
junction-sim import --osm tests/data/osm_junction.json --node-id 1001 --out imported_scenario.json
```

---

### 5. `visualize`

Executes a simulation and exports an interactive HTML5 visualizer, with optional browser launch.

```bash
junction-sim visualize (-c CONFIG | -p PRESET) [options]
```

#### Arguments and Options

| Option | Short | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `--config` | `-c` | string | None | Path to scenario JSON configuration file. Mutually exclusive with `--preset`. |
| `--preset` | `-p` | choice | None | Name of standard preset scenario to visualize. |
| `--controller` | | choice | `fixed-time` | Signal control policy to execute. |
| `--duration` | `-d` | float | None | Simulation duration in seconds (overrides scenario setting). |
| `--seed` | `-s` | integer | None | Random number generator seed. |
| `--out-html` | `-o` | string | `visualizer.html` | Target HTML output path. |
| `--3d` | | flag | False | Explicitly select photorealistic 3D WebGL mode. |
| `--mode` | | choice | `3d` | Rendering engine mode: `2d` (canvas) or `3d` (photorealistic WebGL Three.js). |
| `--open` | | flag | False | Automatically launch the generated visualizer in the default web browser. |

#### Example

```bash
junction-sim visualize --preset webster_four_way --controller actuated --duration 120.0 --mode 3d --open
```

---

### 6. `presets`

Inspects available built-in scenario presets and exports them to standalone JSON files.

```bash
junction-sim presets [list | export]
```

#### Presets List

```bash
junction-sim presets list
```

#### Presets Export

```bash
junction-sim presets export --preset <PRESET_NAME> --out <FILE_PATH>
```

| Option | Short | Required | Description |
| :--- | :--- | :--- | :--- |
| `--preset` | `-p` | Yes | Name of the preset to export (`webster_four_way`, `arterial_corridor`, `peak_hour_surge`, `bottleneck_spillback`). |
| `--out` | `-o` | Yes | Destination path for the exported JSON scenario file. |

#### Example

```bash
junction-sim presets export --preset bottleneck_spillback --out scenarios/spillback_experiment.json
```
