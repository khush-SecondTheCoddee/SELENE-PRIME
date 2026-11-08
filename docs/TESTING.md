# Testing Strategy and Current Coverage

**Status:** Phase 2 and Phase 3 execution records are available; Phase 4 tests have been added but have not yet been executed in this environment.

## Local checks

Install the development extra and run:

```sh
python -m pytest
python -m ruff check .
python -m mypy
```

The GitHub Actions workflow runs these commands on Python 3.11–3.14. CI configuration is present; a successful hosted run has not yet been recorded for this branch.

## Current tests

- `tests/unit/test_foundation.py`: epoch labels, finite quantities, SHA-256 syntax, provenance timestamp validation/JSON round trips, and package logger behavior.
- `tests/unit/test_geometry.py`: generic coordinates, vector/rotation invariants, and analytic circle overlap.
- `tests/unit/test_frames.py`: explicit frame registry, body-fixed classification, same-origin constraint, rotation direction, unit preservation, invalid ET, unknown frames, and SPICE adapter behavior using injected fake providers.

Frame tests use synthetic frame declarations and fake SPICE interfaces. They test software contracts only; they do not validate any real lunar frame, kernel, datum, or external reference point. Digest validation checks formatting only; it does not hash an artifact.

## Planned layers

Add integration tests using genuine user-supplied kernels and products, independent validation cases, regression benchmarks, convergence runs, and reproducibility checks. Synthetic fixtures must be marked synthetic. A test is reported as passing only after it is actually executed.

## Phase 2 execution record

- `python -m pytest`: **7 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy`: **passed**, strict configuration, 4 source files checked (mypy 1.20.2).
- Editable base install (`python -m pip install -e .`): **passed** with build isolation.
- Ruff and hosted CI were not run; the Termux Rust/maturin build failed when attempting to build Ruff from source.

## Phase 3 execution record

- `python -m pytest`: **25 passed** on Python 3.14.6 / Android (Termux), including analytic geometry references and boundary/failure cases.
- `python -m mypy`: strict check passed for all 9 source files.
- Ruff and hosted CI remain pending.
- Analytic expected/actual values and absolute errors are recorded in [the Phase 3 validation record](PHASE3_VALIDATION.md).

## Phase 4 execution record

- New frame-service tests have been added. They have **not yet been executed** by this authoring workflow.
- No real SPICE kernel pool, lunar frame definition, lunar datum, or independent lunar frame reference was available for validation.
- The optional SpiceyPy dependency is declared separately as `spice`; importing the core package does not require it.
