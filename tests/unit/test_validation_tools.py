"""Synthetic tests for successive refinement and input uncertainty utilities."""
from __future__ import annotations

import pytest

from selene_prime.errors import ConfigurationError
from selene_prime.validation import finite_difference_sensitivities, monte_carlo, run_refinements


def test_refinement_compares_every_successive_pair_without_ground_truth() -> None:
    report = run_refinements(
        (10, 20, 40), lambda n: {"visibility": 1.0 - 1.0 / n, "horizon": 2.0 + 1.0 / n**2},
        absolute_tolerances={"visibility": 0.02, "horizon": 0.01},
        relative_tolerances={"visibility": 0.02, "horizon": 0.01},
    )
    assert len(report.steps) == 2
    assert report.steps[0].differences[1].absolute_difference > 0
    assert not report.converged
    assert report.to_dict()["resolutions"] == (10, 20, 40)


def test_refinement_tolerance_validation_and_pass_state() -> None:
    passing = run_refinements((2, 4), lambda n: {"f": 0.5},
                              absolute_tolerances={"f": 0}, relative_tolerances={"f": 0})
    assert passing.converged and passing.steps[0].passed
    with pytest.raises(ConfigurationError, match="strictly increasing"):
        run_refinements((4, 2), lambda n: {"f": 1}, absolute_tolerances={"f": 1},
                        relative_tolerances={"f": 1})


def test_local_sensitivity_matches_analytic_polynomial() -> None:
    evaluator = lambda x: {"y": x["a"] ** 2 + 3 * x["b"]}
    values = finite_difference_sensitivities(evaluator, {"a": 2.0, "b": 4.0},
                                             {"a": 0.1, "b": 0.2})
    assert [(item.parameter, item.output) for item in values] == [("a", "y"), ("b", "y")]
    assert values[0].derivative_per_unit == pytest.approx(4.0, rel=1e-8)
    assert values[0].propagated_standard_uncertainty == pytest.approx(0.4, rel=1e-8)
    assert values[1].derivative_per_unit == pytest.approx(3.0, rel=1e-8)


def test_monte_carlo_is_seeded_and_matches_linear_uncertainty() -> None:
    evaluate = lambda x: {"sum": x["a"] + 2 * x["b"]}
    first = monte_carlo(evaluate, {"a": 1.0, "b": -2.0}, {"a": 0.2, "b": 0.1},
                        samples=20_000, seed=8)
    second = monte_carlo(evaluate, {"a": 1.0, "b": -2.0}, {"a": 0.2, "b": 0.1},
                         samples=20_000, seed=8)
    assert first == second
    assert first.output_means["sum"] == pytest.approx(-3.0, abs=0.01)
    assert first.output_standard_deviations["sum"] == pytest.approx((0.2**2 + (2*0.1)**2) ** 0.5, abs=0.01)
    assert first.to_dict()["seed"] == 8


def test_benchmark_record_preserves_reference_error_and_status() -> None:
    from selene_prime.validation import BenchmarkCase, execute_benchmark

    case = BenchmarkCase("analytic_half_disk", "visibility", "analytic",
                        "area of a half-circle divided by full circle", "half-plane mask", 0.5,
                        "fraction", 1e-6, 0.0)
    result = execute_benchmark(case, lambda: 0.5000002)
    assert result.status == "pass"
    assert result.absolute_error == pytest.approx(2e-7)
    assert result.relative_error == pytest.approx(4e-7)
    assert '"status":"pass"' in result.to_json()
