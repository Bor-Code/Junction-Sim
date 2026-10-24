from pydantic import BaseModel, ConfigDict, Field

from junction_sim.exceptions import ValidationError


class BenchmarkMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    controller_name: str
    total_arrivals: int = Field(ge=0)
    total_discharges: int = Field(ge=0)
    completion_rate: float = Field(ge=0.0, le=100.0)
    average_delay: float = Field(ge=0.0)
    max_delay: float = Field(ge=0.0)
    average_queue: float = Field(ge=0.0)
    max_queue: int = Field(ge=0)
    phase_switch_count: int = Field(ge=0)
    wasted_green_time: float = Field(ge=0.0)
    fuel_consumed_liters: float = Field(default=0.0, ge=0.0)
    co2_emitted_kg: float = Field(default=0.0, ge=0.0)


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: dict[str, BenchmarkMetrics]
    duration: float = Field(gt=0.0)
    step_size: float = Field(gt=0.0)
    seed: int | None = Field(default=None)

    @property
    def best_by_delay(self) -> str:
        if not self.metrics:
            raise ValidationError("no metrics available in benchmark result")
        return min(self.metrics.values(), key=lambda m: m.average_delay).controller_name

    @property
    def best_by_throughput(self) -> str:
        if not self.metrics:
            raise ValidationError("no metrics available in benchmark result")
        return max(
            self.metrics.values(), key=lambda m: m.total_discharges
        ).controller_name

    def delay_reduction_pct(self, baseline: str, candidate: str) -> float:
        if baseline not in self.metrics:
            raise ValidationError(f"baseline controller '{baseline}' not found")
        if candidate not in self.metrics:
            raise ValidationError(f"candidate controller '{candidate}' not found")
        base_delay = self.metrics[baseline].average_delay
        cand_delay = self.metrics[candidate].average_delay
        if base_delay == 0.0:
            return 0.0
        return round(((base_delay - cand_delay) / base_delay) * 100.0, 2)
