"""Auditable benchmark records for supplied independent reference values."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Callable

from selene_prime.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One reference result whose source and acceptance tolerance are explicit."""
    case_id: str
    category: str
    designation: str
    reference_source: str
    inputs: str
    expected: float
    unit: str
    absolute_tolerance: float
    relative_tolerance: float

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (self.case_id, self.category, self.designation,
                                                self.reference_source, self.inputs, self.unit)):
            raise ConfigurationError("benchmark identity, source, inputs and unit are required")
        if self.designation not in {"analytic", "synthetic", "external"}:
            raise ConfigurationError("benchmark designation must be analytic, synthetic, or external")
        if any(not math.isfinite(value) for value in
               (self.expected, self.absolute_tolerance, self.relative_tolerance)):
            raise ConfigurationError("benchmark values and tolerances must be finite")
        if self.absolute_tolerance < 0 or self.relative_tolerance < 0:
            raise ConfigurationError("benchmark tolerances must be nonnegative")


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Executed comparison with actual result and absolute/relative error."""
    case: BenchmarkCase
    actual: float
    absolute_error: float
    relative_error: float
    status: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))


def execute_benchmark(case: BenchmarkCase, evaluator: Callable[[], float]) -> BenchmarkResult:
    """Execute one case and apply its predeclared absolute-plus-relative limit."""
    actual = evaluator()
    if not math.isfinite(actual):
        raise ConfigurationError(f"benchmark {case.case_id} produced a nonfinite result")
    absolute = abs(actual - case.expected)
    relative = absolute / max(abs(case.expected), 1e-300)
    allowed = case.absolute_tolerance + case.relative_tolerance * abs(case.expected)
    return BenchmarkResult(case, actual, absolute, relative, "pass" if absolute <= allowed else "fail")
