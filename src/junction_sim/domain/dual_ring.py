from pydantic import BaseModel, ConfigDict, Field, model_validator

from junction_sim.domain.intersection import Intersection
from junction_sim.domain.movement import TurnType
from junction_sim.domain.signal import SignalPhase, SignalPlan
from junction_sim.exceptions import InvalidSignalPlanError, ValidationError


class NEMAPhase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    phase_number: int = Field(ge=1, le=16)
    ring: int = Field(ge=1, le=2)
    barrier_group: int = Field(ge=1)
    green_movement_ids: tuple[str, ...] = Field(min_length=1)
    green_duration: float = Field(gt=0.0)
    yellow_duration: float = Field(default=3.0, ge=0.0)
    all_red_duration: float = Field(default=1.0, ge=0.0)
    min_green: float = Field(default=5.0, gt=0.0)
    max_green: float = Field(default=60.0, gt=0.0)

    @model_validator(mode="after")
    def validate_phase(self) -> "NEMAPhase":
        if self.max_green < self.min_green:
            raise InvalidSignalPlanError("max_green cannot be less than min_green")
        if self.green_duration < self.min_green:
            raise InvalidSignalPlanError("green_duration cannot be less than min_green")
        if self.green_duration > self.max_green:
            raise InvalidSignalPlanError("green_duration cannot exceed max_green")
        for m_id in self.green_movement_ids:
            if not m_id.strip():
                raise InvalidSignalPlanError("movement id cannot be empty or blank")
        if len(self.green_movement_ids) != len(set(self.green_movement_ids)):
            raise InvalidSignalPlanError("duplicate movement ids found in NEMA phase")
        return self

    @property
    def total_duration(self) -> float:
        return self.green_duration + self.yellow_duration + self.all_red_duration


class DualRingStructure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    phases: tuple[NEMAPhase, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_structure(self) -> "DualRingStructure":
        if not self.id.strip():
            raise ValidationError("dual ring id cannot be empty or blank")

        phase_numbers = [p.phase_number for p in self.phases]
        if len(phase_numbers) != len(set(phase_numbers)):
            raise InvalidSignalPlanError(
                "duplicate phase numbers found in dual ring structure"
            )

        rings = {p.ring for p in self.phases}
        if rings != {1, 2}:
            raise InvalidSignalPlanError(
                "dual ring structure must contain phases in both ring 1 and ring 2"
            )

        barriers_r1 = {p.barrier_group for p in self.phases if p.ring == 1}
        barriers_r2 = {p.barrier_group for p in self.phases if p.ring == 2}
        if barriers_r1 != barriers_r2:
            raise InvalidSignalPlanError(
                "barrier groups must be identical across ring 1 and ring 2"
            )

        return self

    @property
    def ring1_phases(self) -> tuple[NEMAPhase, ...]:
        return tuple(p for p in self.phases if p.ring == 1)

    @property
    def ring2_phases(self) -> tuple[NEMAPhase, ...]:
        return tuple(p for p in self.phases if p.ring == 2)

    @property
    def barrier_groups(self) -> tuple[int, ...]:
        return tuple(sorted({p.barrier_group for p in self.phases}))

    def get_phase(self, phase_number: int) -> NEMAPhase:
        for p in self.phases:
            if p.phase_number == phase_number:
                return p
        raise InvalidSignalPlanError(
            f"NEMA phase {phase_number} not found in dual ring '{self.id}'"
        )

    def get_phases_in_barrier(
        self, barrier_group: int, ring: int | None = None
    ) -> tuple[NEMAPhase, ...]:
        result = [p for p in self.phases if p.barrier_group == barrier_group]
        if ring is not None:
            result = [p for p in result if p.ring == ring]
        return tuple(result)

    def are_compatible(self, phase_a: int, phase_b: int) -> bool:
        if phase_a == phase_b:
            return False
        pa = self.get_phase(phase_a)
        pb = self.get_phase(phase_b)
        return pa.ring != pb.ring and pa.barrier_group == pb.barrier_group

    def to_signal_plan(self, plan_id: str | None = None) -> SignalPlan:
        target_id = plan_id if plan_id is not None else f"{self.id}_plan"
        composite_phases: list[SignalPhase] = []

        for bg in self.barrier_groups:
            r1 = self.get_phases_in_barrier(bg, ring=1)
            r2 = self.get_phases_in_barrier(bg, ring=2)
            max_len = max(len(r1), len(r2))

            for i in range(max_len):
                p1 = r1[i % len(r1)]
                p2 = r2[i % len(r2)]
                phase_name = f"B{bg}_P{p1.phase_number}_P{p2.phase_number}"
                green_movs = tuple(
                    sorted(set(p1.green_movement_ids + p2.green_movement_ids))
                )
                green_dur = max(p1.green_duration, p2.green_duration)
                yellow_dur = max(p1.yellow_duration, p2.yellow_duration)
                all_red_dur = max(p1.all_red_duration, p2.all_red_duration)
                min_g = max(p1.min_green, p2.min_green)
                max_g = max(p1.max_green, p2.max_green)

                composite_phases.append(
                    SignalPhase(
                        id=phase_name,
                        green_movement_ids=green_movs,
                        green_duration=green_dur,
                        yellow_duration=yellow_dur,
                        all_red_duration=all_red_dur,
                        min_green=min_g,
                        max_green=max_g,
                    )
                )

        return SignalPlan(id=target_id, phases=tuple(composite_phases))


def build_nema_eight_phase_structure(
    intersection: Intersection,
    id: str = "nema_8phase",
) -> DualRingStructure:
    mov_lookup: dict[tuple[str, TurnType], str] = {}
    for m in intersection.movements:
        mov_lookup[(m.origin, m.turn_type)] = m.id

    required = [
        ("north", TurnType.LEFT),
        ("south", TurnType.THROUGH),
        ("west", TurnType.LEFT),
        ("east", TurnType.THROUGH),
        ("south", TurnType.LEFT),
        ("north", TurnType.THROUGH),
        ("east", TurnType.LEFT),
        ("west", TurnType.THROUGH),
    ]

    for orig, t_type in required:
        if (orig, t_type) not in mov_lookup:
            raise ValidationError(
                f"intersection missing movement for NEMA 8-phase: {orig} {t_type.value}"
            )

    phases = (
        NEMAPhase(
            phase_number=1,
            ring=1,
            barrier_group=1,
            green_movement_ids=(mov_lookup[("north", TurnType.LEFT)],),
            green_duration=10.0,
            yellow_duration=3.0,
            all_red_duration=1.0,
            min_green=5.0,
            max_green=30.0,
        ),
        NEMAPhase(
            phase_number=2,
            ring=1,
            barrier_group=1,
            green_movement_ids=(mov_lookup[("south", TurnType.THROUGH)],),
            green_duration=25.0,
            yellow_duration=4.0,
            all_red_duration=1.0,
            min_green=7.0,
            max_green=60.0,
        ),
        NEMAPhase(
            phase_number=3,
            ring=1,
            barrier_group=2,
            green_movement_ids=(mov_lookup[("west", TurnType.LEFT)],),
            green_duration=10.0,
            yellow_duration=3.0,
            all_red_duration=1.0,
            min_green=5.0,
            max_green=30.0,
        ),
        NEMAPhase(
            phase_number=4,
            ring=1,
            barrier_group=2,
            green_movement_ids=(mov_lookup[("east", TurnType.THROUGH)],),
            green_duration=20.0,
            yellow_duration=4.0,
            all_red_duration=1.0,
            min_green=7.0,
            max_green=50.0,
        ),
        NEMAPhase(
            phase_number=5,
            ring=2,
            barrier_group=1,
            green_movement_ids=(mov_lookup[("south", TurnType.LEFT)],),
            green_duration=10.0,
            yellow_duration=3.0,
            all_red_duration=1.0,
            min_green=5.0,
            max_green=30.0,
        ),
        NEMAPhase(
            phase_number=6,
            ring=2,
            barrier_group=1,
            green_movement_ids=(mov_lookup[("north", TurnType.THROUGH)],),
            green_duration=25.0,
            yellow_duration=4.0,
            all_red_duration=1.0,
            min_green=7.0,
            max_green=60.0,
        ),
        NEMAPhase(
            phase_number=7,
            ring=2,
            barrier_group=2,
            green_movement_ids=(mov_lookup[("east", TurnType.LEFT)],),
            green_duration=10.0,
            yellow_duration=3.0,
            all_red_duration=1.0,
            min_green=5.0,
            max_green=30.0,
        ),
        NEMAPhase(
            phase_number=8,
            ring=2,
            barrier_group=2,
            green_movement_ids=(mov_lookup[("west", TurnType.THROUGH)],),
            green_duration=20.0,
            yellow_duration=4.0,
            all_red_duration=1.0,
            min_green=7.0,
            max_green=50.0,
        ),
    )

    return DualRingStructure(id=id, phases=phases)
