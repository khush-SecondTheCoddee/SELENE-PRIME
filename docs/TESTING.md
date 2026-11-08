# Testing Strategy and Current Coverage

**Status:** Phase 2 foundation tests exist. They do not establish scientific validity.

## Local checks

Install the development extra and run:

```sh
python -m pytest
python -m ruff check .
python -m mypy
```

The GitHub Actions workflow runs these commands on Python 3.11–3.14. CI configuration is present; a successful hosted run has not yet been recorded.

## Current tests

`tests/unit/test_foundation.py` covers nonempty epoch labels, finite quantities, SHA-256 syntax, provenance timestamp validation and JSON round trips, and package logger output/root-logger isolation. `tests/unit/test_geometry.py` covers generic coordinates, vector/rotation invariants, and analytic circle overlap. Digest validation checks formatting only; it does not hash an artifact. No test exercises SPICE, a lunar datum, real terrain, apparent positions, radiometry, or mission-specific results.

## Planned layers

Add unit and property tests alongside each subsystem, then integration tests using genuine user-supplied kernels and products, independent validation cases, regression benchmarks, convergence runs, and reproducibility checks. Synthetic fixtures must be marked synthetic. A test is reported as passing only after it is actually executed.

## Phase 2 execution record

- `python -m pytest`: **7 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy`: **passed**, strict configuration, 4 source files checked (mypy 1.20.2).
- Editable base install (`python -m pip install -e .`): **passed** with build isolation.
- `python -m ruff check .`: **not run**. Installing the dev extra attempted to build Ruff from source on Termux; its Rust/maturin build failed against this Android toolchain. The GitHub Actions Linux runner is configured to run Ruff, but no hosted CI result is available.
- A no-build-isolation install was also attempted and failed because setuptools is not installed in the system interpreter; this does not affect the isolated editable install.

These results cover only software-foundation behavior, not scientific correctness.

## Phase 3 execution record

- `python -m pytest`: **25 passed** on Python 3.14.6 / Android (Termux), including analytic geometry references and boundary/failure cases.
- `python -m mypy`: strict check passed for all 9 source files.
- Ruff and hosted CI remain pending for the Termux/toolchain reasons above.
- Analytic expected/actual values and absolute errors are recorded in [the Phase 3 validation record](PHASE3_VALIDATION.md).
