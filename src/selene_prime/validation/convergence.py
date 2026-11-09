"""Successive-resolution convergence records; no resolution is treated as truth."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Callable, Mapping

from selene_prime.errors import ConfigurationError

MetricEvaluator = Callable[[int], Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class MetricDifference:
    metric: str
    coarse_value: float
    fine_value: float
    absolute_difference: float
    relative_difference: float
    absolute_tolerance: float
    relative_tolerance: float
    passed: bool


@dataclass(frozen=True, slots=True)
class RefinementStep:
    coarse_resolution: int
    fine_resolution: int
    differences: tuple[MetricDifference, ...]

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.differences)


@dataclass(frozen=True, slots=True)
class ConvergenceReport:
    resolutions: tuple[int, ...]
    values: tuple[Mapping[str, float], ...]
    steps: tuple[RefinementStep, ...]
    converged: bool

    def to_dict(self) -> dict[str, object]:
        """Return JSON-ready records with all successive differences preserved."""
        return asdict(self)


def run_refinements(
    resolutions: tuple[int, ...], evaluator: MetricEvaluator, *,
    absolute_tolerances: Mapping[str, float], relative_tolerances: Mapping[str, float],
) -> ConvergenceReport:
    """Evaluate increasing resolutions and compare every successive pair.

    A passing report means only that differences meet caller-supplied tolerances;
    it does not prove accuracy or identify a ground-truth resolution.
    """
    if len(resolutions) < 2 or any(isinstance(n, bool) or not isinstance(n, int) or n < 1
                                   for n in resolutions):
        raise ConfigurationError("at least two positive integer resolutions are required")
    if any(b <= a for a, b in zip(resolutions, resolutions[1:])):
        raise ConfigurationError("resolutions must be strictly increasing")
    if not absolute_tolerances or set(absolute_tolerances) != set(relative_tolerances):
        raise ConfigurationError("absolute and relative tolerance maps must name the same metrics")
    for name in absolute_tolerances:
        if not name or any(not math.isfinite(tol) or tol < 0
                           for tol in (absolute_tolerances[name], relative_tolerances[name])):
            raise ConfigurationError("metric tolerances must be finite and nonnegative")
    values = tuple(dict(evaluator(resolution)) for resolution in resolutions)
    metric_names = set(absolute_tolerances)
    for result in values:
        if set(result) != metric_names or any(not math.isfinite(v) for v in result.values()):
            raise ConfigurationError("evaluator must return finite values for exactly configured metrics")
    steps: list[RefinementStep] = []
    for index in range(1, len(resolutions)):
        differences: list[MetricDifference] = []
        for metric in sorted(metric_names):
            coarse, fine = values[index - 1][metric], values[index][metric]
            absolute = abs(fine - coarse)
            relative = absolute / max(abs(fine), abs(coarse), 1e-300)
            passed = absolute <= absolute_tolerances[metric] and relative <= relative_tolerances[metric]
            differences.append(MetricDifference(metric, coarse, fine, absolute, relative,
                                                absolute_tolerances[metric],
                                                relative_tolerances[metric], passed))
        steps.append(RefinementStep(resolutions[index - 1], resolutions[index], tuple(differences)))
    return ConvergenceReport(resolutions, values, tuple(steps), all(step.passed for step in steps))
