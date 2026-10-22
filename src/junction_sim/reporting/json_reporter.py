import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TextIO

from junction_sim.benchmarks.metrics import BenchmarkResult
from junction_sim.engine.step_result import StepResult


def export_step_results_to_json(
    results: Sequence[StepResult],
    destination: Path | str | TextIO | None = None,
    indent: int = 2,
) -> str:
    payload: list[dict[str, Any]] = []
    for r in results:
        step_dict: dict[str, Any] = {
            "time": r.time,
            "step_index": r.step_index,
            "active_phase_id": r.active_phase_id,
            "signal_state": r.signal_state.value,
            "arrived_vehicle_ids": [v.id for v in r.arrived_vehicles],
            "discharged_vehicles": [
                {
                    "id": v.id,
                    "origin": v.origin,
                    "destination": v.destination,
                    "arrival_time": v.arrival_time,
                    "departure_time": v.departure_time,
                    "waiting_time": v.waiting_time(r.time),
                }
                for v in r.discharged_vehicles
            ],
            "queue_lengths": r.queue_lengths,
            "controller_decision": (
                {
                    "target_phase_id": r.controller_decision.target_phase_id,
                    "reason": r.controller_decision.reason,
                }
                if r.controller_decision
                else None
            ),
        }
        payload.append(step_dict)

    json_str = json.dumps(payload, indent=indent)

    if destination is None:
        return json_str

    if isinstance(destination, (str, Path)):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_str, encoding="utf-8")
        return json_str

    destination.write(json_str)
    return ""


def export_benchmark_to_json(
    result: BenchmarkResult,
    destination: Path | str | TextIO | None = None,
    indent: int = 2,
) -> str:
    payload: dict[str, Any] = {
        "duration": result.duration,
        "step_size": result.step_size,
        "seed": result.seed,
        "best_by_delay": result.best_by_delay if result.metrics else None,
        "best_by_throughput": result.best_by_throughput if result.metrics else None,
        "metrics": {name: m.model_dump() for name, m in result.metrics.items()},
    }

    json_str = json.dumps(payload, indent=indent)

    if destination is None:
        return json_str

    if isinstance(destination, (str, Path)):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_str, encoding="utf-8")
        return json_str

    destination.write(json_str)
    return ""
