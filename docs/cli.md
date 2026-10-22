# CLI Reference Guide

`junction-sim` provides a unified command line interface for executing discrete-event traffic simulations, benchmarking signal control policies, and managing scenario presets.

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
| `--controller` | | choice | `fixed-time` | Signal controller policy to use: `fixed-time`, `actuated`, `max-pressure`. |
| `--duration` | `-d` | float | None | Simulation duration in seconds (overrides scenario setting). |
| `--seed` | `-s` | integer | None | Random number generator seed (overrides scenario setting). |
| `--dashboard` | | flag | False | Render terminal ASCII intersection layout and queue bar charts for the final simulation step. |
| `--out-csv` | | string | None | Destination path to export step-by-step CSV time series. |
| `--out-json` | | string | None | Destination path to export detailed simulation execution summary in JSON format. |

#### Examples

Running a preset with terminal dashboard:

```bash
junction-sim run --preset arterial_corridor --controller max-pressure --duration 120.0 --dashboard
```

Running a custom configuration and exporting CSV metrics:

```bash
junction-sim run --config scenarios/custom.json --controller actuated --out-csv results/metrics.csv
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
| `--controllers` | | string | `fixed-time,actuated,max-pressure` | Comma-separated list of controllers to benchmark. |
| `--duration` | `-d` | float | None | Simulation duration in seconds (overrides scenario setting). |
| `--seed` | `-s` | integer | None | Random number generator seed. |
| `--out-csv` | | string | None | Destination path to export benchmark summary CSV. |
| `--out-json` | | string | None | Destination path to export benchmark summary JSON. |

#### Example

```bash
junction-sim benchmark --preset webster_four_way --controllers fixed-time,actuated,max-pressure --duration 300.0 --out-json bench.json
```

---

### 3. `presets`

Inspects available built-in scenario presets and exports them to standalone JSON files.

```bash
junction-sim presets [list | export]
```

#### Presets List

```bash
junction-sim presets list
```

Outputs a table of all registered presets along with their descriptions.

#### Presets Export

```bash
junction-sim presets export --preset <PRESET_NAME> --out <FILE_PATH>
```

| Option | Short | Required | Description |
| :--- | :--- | :--- | :--- |
| `--preset` | `-p` | Yes | Name of the preset to export. |
| `--out` | `-o` | Yes | Destination path for the exported JSON scenario file. |

#### Example

```bash
junction-sim presets export --preset bottleneck_spillback --out scenarios/spillback_experiment.json
```

---

## Exit Codes

| Exit Code | Meaning |
| :--- | :--- |
| `0` | Successful execution or help display. |
| `1` | Configuration error, invalid geometry, or runtime simulation exception. |
| `2` | Command-line argument parsing error (handled by argparse). |
