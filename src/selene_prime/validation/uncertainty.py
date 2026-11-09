"""Input uncertainty propagation kept separate from numerical convergence."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import random
from typing import Callable, Mapping

from selene_prime.errors import ConfigurationError

ModelEvaluator = Callable[[Mapping[str, float]], Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class Sensitivity:
    parameter: str
    output: str
    derivative_per_unit: float
    input_standard_uncertainty: float
    propagated_standard_uncertainty: float


@dataclass(frozen=True, slots=True)
class MonteCarloSummary:
    samples: int
    seed: int
    output_means: Mapping[str, float]
    output_standard_deviations: Mapping[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def finite_difference_sensitivities(
    evaluator: ModelEvaluator, nominal_inputs: Mapping[str, float],
    input_standard_uncertainties: Mapping[str, float], *, relative_step: float = 1e-5,
) -> tuple[Sensitivity, ...]:
    """Estimate independent-input local sensitivities with symmetric differences."""
    _validate_inputs(nominal_inputs, input_standard_uncertainties)
    if not math.isfinite(relative_step) or relative_step <= 0:
        raise ConfigurationError("relative_step must be finite and positive")
    nominal = dict(evaluator(nominal_inputs))
    if not nominal or any(not math.isfinite(v) for v in nominal.values()):
        raise ConfigurationError("evaluator must return finite named outputs")
    results: list[Sensitivity] = []
    for parameter, sigma in input_standard_uncertainties.items():
        center = nominal_inputs[parameter]
        step = relative_step * max(abs(center), sigma, 1.0)
        low, high = dict(nominal_inputs), dict(nominal_inputs)
        low[parameter], high[parameter] = center - step, center + step
        low_output, high_output = evaluator(low), evaluator(high)
        if set(low_output) != set(nominal) or set(high_output) != set(nominal):
            raise ConfigurationError("evaluator output keys changed during sensitivity perturbation")
        for output in sorted(nominal):
            derivative = (high_output[output] - low_output[output]) / (2 * step)
            if not math.isfinite(derivative):
                raise ConfigurationError("finite-difference derivative is nonfinite")
            results.append(Sensitivity(parameter, output, derivative, sigma, abs(derivative) * sigma))
    return tuple(results)


def monte_carlo(
    evaluator: ModelEvaluator, nominal_inputs: Mapping[str, float],
    input_standard_uncertainties: Mapping[str, float], *, samples: int, seed: int,
) -> MonteCarloSummary:
    """Propagate independent Gaussian input uncertainties with a recorded seed."""
    _validate_inputs(nominal_inputs, input_standard_uncertainties)
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ConfigurationError("Monte Carlo samples must be an integer >= 2")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ConfigurationError("Monte Carlo seed must be an integer")
    rng = random.Random(seed)
    collected: dict[str, list[float]] = {}
    for _ in range(samples):
        values = dict(nominal_inputs)
        for parameter, sigma in input_standard_uncertainties.items():
            values[parameter] = rng.gauss(values[parameter], sigma)
        output = evaluator(values)
        if not output or any(not math.isfinite(value) for value in output.values()):
            raise ConfigurationError("evaluator returned empty or nonfinite Monte Carlo output")
        if collected and set(output) != set(collected):
            raise ConfigurationError("evaluator output keys changed during Monte Carlo run")
        for name, value in output.items():
            collected.setdefault(name, []).append(value)
    means = {name: sum(values) / samples for name, values in collected.items()}
    stds = {name: math.sqrt(sum((value - means[name]) ** 2 for value in values) / (samples - 1))
            for name, values in collected.items()}
    return MonteCarloSummary(samples, seed, means, stds)


def _validate_inputs(nominal: Mapping[str, float], uncertainties: Mapping[str, float]) -> None:
    if not nominal or set(uncertainties) - set(nominal):
        raise ConfigurationError("nominal inputs must be nonempty and uncertainty keys must be a subset")
    if any(not name or not math.isfinite(value) for name, value in nominal.items()):
        raise ConfigurationError("nominal inputs must have names and finite values")
    if any(not name or not math.isfinite(value) or value < 0
           for name, value in uncertainties.items()):
        raise ConfigurationError("input standard uncertainties must be finite and nonnegative")
