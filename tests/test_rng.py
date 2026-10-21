import pytest

from junction_sim.engine.rng import TrafficRNG
from junction_sim.exceptions import ValidationError


def test_rng_reproducibility() -> None:
    rng1 = TrafficRNG(seed=42)
    rng2 = TrafficRNG(seed=42)

    samples1 = [rng1.random() for _ in range(100)]
    samples2 = [rng2.random() for _ in range(100)]
    assert samples1 == samples2

    poisson1 = [rng1.poisson(lam=1.5) for _ in range(50)]
    poisson2 = [rng2.poisson(lam=1.5) for _ in range(50)]
    assert poisson1 == poisson2


def test_rng_different_seeds_diverge() -> None:
    rng1 = TrafficRNG(seed=42)
    rng2 = TrafficRNG(seed=99)

    samples1 = [rng1.random() for _ in range(20)]
    samples2 = [rng2.random() for _ in range(20)]
    assert samples1 != samples2


def test_rng_seed_property() -> None:
    rng_seeded = TrafficRNG(seed=12345)
    assert rng_seeded.seed == 12345

    rng_unseeded = TrafficRNG()
    assert rng_unseeded.seed is None


def test_rng_uniform() -> None:
    rng = TrafficRNG(seed=42)
    val = rng.uniform(5.0, 15.0)
    assert 5.0 <= val <= 15.0

    with pytest.raises(ValidationError):
        rng.uniform(15.0, 5.0)


def test_rng_exponential() -> None:
    rng = TrafficRNG(seed=42)
    val = rng.exponential(rate=2.0)
    assert val >= 0.0

    with pytest.raises(ValidationError):
        rng.exponential(rate=0.0)

    with pytest.raises(ValidationError):
        rng.exponential(rate=-1.0)


def test_rng_poisson() -> None:
    rng = TrafficRNG(seed=42)
    assert rng.poisson(lam=0.0) == 0

    with pytest.raises(ValidationError):
        rng.poisson(lam=-0.5)

    samples = [rng.poisson(lam=2.5) for _ in range(5000)]
    mean = sum(samples) / len(samples)
    assert 2.4 <= mean <= 2.6


def test_rng_choice() -> None:
    rng = TrafficRNG(seed=42)
    options = ["north", "south", "east", "west"]
    chosen = rng.choice(options)
    assert chosen in options

    with pytest.raises(ValidationError):
        rng.choice([])


def test_rng_spawn_child() -> None:
    parent1 = TrafficRNG(seed=42)
    parent2 = TrafficRNG(seed=42)

    child1 = parent1.spawn_child()
    child2 = parent2.spawn_child()

    assert isinstance(child1, TrafficRNG)
    assert child1.seed == child2.seed

    samples1 = [child1.random() for _ in range(50)]
    samples2 = [child2.random() for _ in range(50)]
    assert samples1 == samples2
