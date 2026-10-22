import csv
import io
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from junction_sim.benchmarks.metrics import BenchmarkResult
from junction_sim.engine.step_result import StepResult


def export_step_results_to_csv(
    results: Sequence[StepResult],
    destination: Path | str | TextIO | None = None,
) -> str:
    lane_ids = sorted({lid for r in results for lid in r.queue_lengths})
    fieldnames = [
        "time",
        "step_index",
        "active_phase",
        "signal_state",
        "arrived_count",
        "discharged_count",
        "total_queue",
        "controller_reason",
        "controller_target_phase",
    ] + [f"queue_{lid}" for lid in lane_ids]

    rows: list[dict[str, object]] = []
    for r in results:
        row: dict[str, object] = {
            "time": f"{r.time:.3f}",
            "step_index": r.step_index,
            "active_phase": r.active_phase_id,
            "signal_state": r.signal_state.value,
            "arrived_count": len(r.arrived_vehicles),
            "discharged_count": len(r.discharged_vehicles),
            "total_queue": sum(r.queue_lengths.values()),
            "controller_reason": (
                r.controller_decision.reason if r.controller_decision else ""
            ),
            "controller_target_phase": (
                r.controller_decision.target_phase_id or ""
                if r.controller_decision
                else ""
            ),
        }
        for lid in lane_ids:
            row[f"queue_{lid}"] = r.queue_lengths.get(lid, 0)
        rows.append(row)

    if destination is None:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    if isinstance(destination, (str, Path)):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path.read_text(encoding="utf-8")

    writer = csv.DictWriter(destination, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return ""


def export_benchmark_to_csv(
    result: BenchmarkResult,
    destination: Path | str | TextIO | None = None,
) -> str:
    fieldnames = [
        "controller",
        "total_arrivals",
        "total_discharges",
        "completion_rate_pct",
        "average_delay_s",
        "max_delay_s",
        "average_queue_veh",
        "max_queue_veh",
        "phase_switch_count",
        "wasted_green_time_s",
    ]

    rows: list[dict[str, object]] = []
    for m in result.metrics.values():
        rows.append(
            {
                "controller": m.controller_name,
                "total_arrivals": m.total_arrivals,
                "total_discharges": m.total_discharges,
                "completion_rate_pct": f"{m.completion_rate:.2f}",
                "average_delay_s": f"{m.average_delay:.3f}",
                "max_delay_s": f"{m.max_delay:.3f}",
                "average_queue_veh": f"{m.average_queue:.3f}",
                "max_queue_veh": m.max_queue,
                "phase_switch_count": m.phase_switch_count,
                "wasted_green_time_s": f"{m.wasted_green_time:.3f}",
            }
        )

    if destination is None:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    if isinstance(destination, (str, Path)):
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        return path.read_text(encoding="utf-8")

    writer = csv.DictWriter(destination, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return ""
