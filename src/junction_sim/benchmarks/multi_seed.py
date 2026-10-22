import math
import statistics
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from junction_sim.benchmarks.metrics import BenchmarkMetrics
from junction_sim.exceptions import ValidationError


class MultiSeedMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    controller_name: str
    runs: int = Field(ge=1)
    mean_delay: float = Field(ge=0.0)
    std_delay: float = Field(ge=0.0)
    ci95_delay_lower: float = Field(ge=0.0)
    ci95_delay_upper: float = Field(ge=0.0)
    mean_discharges: float = Field(ge=0.0)
    std_discharges: float = Field(ge=0.0)
    mean_completion_rate: float = Field(ge=0.0, le=100.0)
    mean_max_queue: float = Field(ge=0.0)
    mean_wasted_green: float = Field(ge=0.0)


class MultiSeedBenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    controller_metrics: dict[str, MultiSeedMetrics]
    seeds: tuple[int, ...] = Field(min_length=1)
    duration: float = Field(gt=0.0)
    step_size: float = Field(gt=0.0)

    @property
    def best_by_delay(self) -> str:
        if not self.controller_metrics:
            raise ValidationError("no metrics available in multi-seed benchmark")
        return min(
            self.controller_metrics.values(), key=lambda m: m.mean_delay
        ).controller_name

    @property
    def best_by_throughput(self) -> str:
        if not self.controller_metrics:
            raise ValidationError("no metrics available in multi-seed benchmark")
        return max(
            self.controller_metrics.values(), key=lambda m: m.mean_discharges
        ).controller_name


def aggregate_seed_metrics(
    controller_name: str, runs_metrics: Sequence[BenchmarkMetrics]
) -> MultiSeedMetrics:
    if not runs_metrics:
        raise ValidationError("runs_metrics cannot be empty")

    n = len(runs_metrics)
    delays = [m.average_delay for m in runs_metrics]
    discharges = [float(m.total_discharges) for m in runs_metrics]
    completions = [m.completion_rate for m in runs_metrics]
    max_queues = [float(m.max_queue) for m in runs_metrics]
    wasted_greens = [m.wasted_green_time for m in runs_metrics]

    mean_d = round(statistics.mean(delays), 3)
    std_d = round(statistics.stdev(delays), 3) if n > 1 else 0.0

    se_d = std_d / math.sqrt(n) if n > 1 else 0.0
    margin = 1.96 * se_d
    ci_lower = max(0.0, round(mean_d - margin, 3))
    ci_upper = round(mean_d + margin, 3)

    mean_dis = round(statistics.mean(discharges), 2)
    std_dis = round(statistics.stdev(discharges), 2) if n > 1 else 0.0

    mean_comp = round(statistics.mean(completions), 2)
    mean_q = round(statistics.mean(max_queues), 2)
    mean_wasted = round(statistics.mean(wasted_greens), 3)

    return MultiSeedMetrics(
        controller_name=controller_name,
        runs=n,
        mean_delay=mean_d,
        std_delay=std_d,
        ci95_delay_lower=ci_lower,
        ci95_delay_upper=ci_upper,
        mean_discharges=mean_dis,
        std_discharges=std_dis,
        mean_completion_rate=mean_comp,
        mean_max_queue=mean_q,
        mean_wasted_green=mean_wasted,
    )
