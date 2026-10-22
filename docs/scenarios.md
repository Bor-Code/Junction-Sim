# Scenario Configuration & Schema Reference

`junction-sim` uses declarative Pydantic schemas to validate and load intersection geometries, signal plans, and demand profiles.

Scenarios can be loaded directly from JSON files using `load_scenario_from_file`, parsed from Python dictionaries using `load_scenario_from_dict`, or retrieved from standard presets using `get_preset`.

---

## 1. Schema Hierarchy

```text
ScenarioConfig
├── intersection: IntersectionConfig
│   ├── approaches: list[ApproachConfig]
│   │   └── lanes: list[LaneConfig]
│   ├── movements: list[MovementConfig]
│   └── conflicting_movement_pairs: list[list[str]]
├── signal_plan: SignalPlanConfig
│   └── phases: list[SignalPhaseConfig]
├── demands: list[DemandProfileConfig]
└── simulation: SimulationConfig
```

---

## 2. Field Specifications

### `IntersectionConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Yes | Unique alphanumeric identifier for the intersection. |
| `approaches` | `list[ApproachConfig]` | Yes | List of incoming approaches (must contain at least 1). |
| `movements` | `list[MovementConfig]` | Yes | List of vehicular movements (must contain at least 1). |
| `conflicting_movement_pairs` | `list[list[str]]` | No | List of two-element lists defining mutually exclusive movement pairs. |

### `ApproachConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Yes | Approach identifier (e.g., `north`, `south`). |
| `direction` | `Direction` | Yes | Cardinal direction: `"north"`, `"south"`, `"east"`, or `"west"`. |
| `lanes` | `list[LaneConfig]` | Yes | List of inbound lanes belonging to this approach. |

### `LaneConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Yes | Unique lane identifier. |
| `approach_id` | `str` | Yes | Parent approach identifier. |
| `allowed_movement_ids` | `list[str]` | Yes | Movement IDs permitted from this lane. |
| `max_capacity` | `int` | No | Maximum number of vehicles the lane queue can hold (default: 50). |

### `MovementConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Yes | Movement identifier (e.g., `N_T`, `S_L`). |
| `origin` | `str` | Yes | Origin approach ID. |
| `destination` | `str` | Yes | Destination approach ID (cannot equal origin). |
| `turn_type` | `TurnType` | Yes | Turn maneuver: `"through"`, `"left"`, `"right"`, or `"u_turn"`. |
| `saturation_flow_rate` | `float` | No | Maximum discharge rate in vehicles per hour (default: 1800.0). |

### `SignalPhaseConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `id` | `str` | Yes | Phase identifier (e.g., `P1`, `P2`). |
| `green_movement_ids` | `list[str]` | Yes | Movements permitted to proceed during this phase. |
| `green_duration` | `float` | Yes | Nominal green time in seconds. |
| `yellow_duration` | `float` | No | Yellow clearance time in seconds (default: 3.0). |
| `all_red_duration` | `float` | No | All-red clearance time in seconds (default: 1.0). |
| `min_green` | `float` | No | Minimum green time enforced by actuated/adaptive controllers (default: 5.0). |
| `max_green` | `float` | No | Maximum green ceiling enforced by actuated/adaptive controllers (default: 60.0). |

### `DemandProfileConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `movement_id` | `str` | Yes | Movement identifier receiving vehicle arrivals. |
| `flow_rate_vph` | `float` | Yes | Arrival flow rate in vehicles per hour (must be >= 0.0). |

### `SimulationConfig`

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `duration` | `float` | No | Total simulation duration in seconds (default: 300.0). |
| `step_size` | `float` | No | Discrete time step in seconds (default: 1.0). |
| `seed` | `int` | No | Random number generator seed for deterministic reproducibility (default: 42). |

---

## 3. Example JSON Configuration

```json
{
  "intersection": {
    "id": "sample_intersection",
    "approaches": [
      {
        "id": "north",
        "direction": "north",
        "lanes": [
          {
            "id": "lane_n_0",
            "approach_id": "north",
            "allowed_movement_ids": ["N_T"],
            "max_capacity": 50
          }
        ]
      },
      {
        "id": "south",
        "direction": "south",
        "lanes": [
          {
            "id": "lane_s_0",
            "approach_id": "south",
            "allowed_movement_ids": ["S_T"],
            "max_capacity": 50
          }
        ]
      }
    ],
    "movements": [
      {
        "id": "N_T",
        "origin": "north",
        "destination": "south",
        "turn_type": "through",
        "saturation_flow_rate": 1800.0
      },
      {
        "id": "S_T",
        "origin": "south",
        "destination": "north",
        "turn_type": "through",
        "saturation_flow_rate": 1800.0
      }
    ],
    "conflicting_movement_pairs": []
  },
  "signal_plan": {
    "id": "sample_plan",
    "phases": [
      {
        "id": "P1",
        "green_movement_ids": ["N_T"],
        "green_duration": 20.0,
        "yellow_duration": 3.0,
        "all_red_duration": 1.0,
        "min_green": 5.0,
        "max_green": 40.0
      },
      {
        "id": "P2",
        "green_movement_ids": ["S_T"],
        "green_duration": 20.0,
        "yellow_duration": 3.0,
        "all_red_duration": 1.0,
        "min_green": 5.0,
        "max_green": 40.0
      }
    ]
  },
  "demands": [
    { "movement_id": "N_T", "flow_rate_vph": 400.0 },
    { "movement_id": "S_T", "flow_rate_vph": 300.0 }
  ],
  "simulation": {
    "duration": 120.0,
    "step_size": 1.0,
    "seed": 42
  }
}
```
