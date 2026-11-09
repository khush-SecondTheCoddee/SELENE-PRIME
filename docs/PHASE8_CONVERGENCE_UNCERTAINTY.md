# Phase 8: convergence and uncertainty framework

## Implemented tools

`selene_prime.validation.run_refinements` executes a supplied evaluator at at least two strictly increasing integer resolutions, records every metric value, compares each successive pair, and applies predeclared absolute and relative tolerances. Every pair must pass for `converged=true`. The report explicitly does not identify a true result and does not claim accuracy from refinement alone.

`finite_difference_sensitivities` estimates local derivatives using symmetric parameter perturbations. `monte_carlo` propagates caller-supplied independent Gaussian standard uncertainties using a recorded deterministic seed and sample count. These calculations preserve output uncertainty records separately from convergence differences. The caller remains responsible for scientifically justified input distributions, parameter units, model-domain constraints, and correlated-input treatment; correlated covariance matrices are not currently supported.

Results expose JSON-ready dictionaries. Existing `RunProvenance` provides deterministic serialization for input identities, configuration hash, software version, revision, and time. No autonomous result writer currently claims a benchmark has run.

## Executed evidence and limitations

`tests/unit/test_validation_tools.py` verifies successive-refinement bookkeeping, tolerance validation, polynomial finite-difference sensitivities, and repeatable seeded Monte Carlo against a linear analytic uncertainty calculation. The executed full suite: 56 passed. Strict mypy: 25 package source files passed.

No lunar reference case, authentic LOLA data, loaded kernel, passband coefficient source, uncertainty distribution, or scientifically approved acceptance tolerance has been supplied. Therefore this increment produces no lunar convergence report and no mission uncertainty estimate. A future run must store evaluator/configuration, each refinement value, input distributions, seed, units, and reference provenance.
