import math
import random
from collections.abc import Sequence
from typing import TypeVar

from junction_sim.exceptions import ValidationError

T = TypeVar("T")


class TrafficRNG:
    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed
        self._generator = random.Random(seed)

    @property
    def seed(self) -> int | None:
        return self._seed

    def random(self) -> float:
        return self._generator.random()

    def uniform(self, a: float, b: float) -> float:
        if a > b:
            raise ValidationError("a cannot be greater than b in uniform distribution")
        return self._generator.uniform(a, b)

    def exponential(self, rate: float) -> float:
        if rate <= 0.0:
            raise ValidationError(
                "rate must be greater than zero for exponential distribution"
            )
        return self._generator.expovariate(rate)

    def poisson(self, lam: float) -> int:
        if lam < 0.0:
            raise ValidationError("lam cannot be negative for Poisson distribution")
        if lam == 0.0:
            return 0

        limit = math.exp(-lam)
        k = 0
        p = 1.0
        while p > limit:
            k += 1
            p *= self._generator.random()
        return k - 1

    def choice(self, sequence: Sequence[T]) -> T:
        if not sequence:
            raise ValidationError("cannot choose from empty sequence")
        return self._generator.choice(sequence)

    def spawn_child(self) -> "TrafficRNG":
        child_seed = self._generator.getrandbits(64)
        return TrafficRNG(seed=child_seed)
