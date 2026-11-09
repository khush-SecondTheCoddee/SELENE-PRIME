# Testing Strategy and Current Coverage

**Status:** Phase 4 kernel/frame adapter failure-injection tests exist. They do not establish real ephemeris or scientific validity.

## Local checks

Install the development extra and run:

```sh
python -m pytest
python -m ruff check .
python -m mypy
```

The GitHub Actions workflow runs these commands on Python 3.11–3.14. CI configuration is present; a successful hosted run has not yet been recorded.

## Current tests

`tests/unit/test_foundation.py` covers shared model and logging behavior. `tests/unit/test_geometry.py` covers generic coordinates, vector/rotation invariants, and analytic circle overlap. `tests/unit/test_kernel_session.py` injects a fake SPICE API to exercise manifest integrity, explicit ownership, reverse-order cleanup, preloaded-pool refusal, rollback, state-chain failure, coverage gaps, and frame transforms. Its temporary bytes are deliberately invalid as SPICE kernels; no test loads them into CSPICE. `tests/unit/test_terrain.py` covers a synthetic PDS3 LOLA-like label/image fixture, signed sample decoding, height scale/reference radius separation, hashes, grid interpolation, antimeridian, edges, poles, NoData, and format rejection. No test exercises a genuine SPICE kernel, authentic PDS/LOLA raster, selected lunar datum transformation, apparent positions, radiometry, or mission-specific results.

## Planned layers

Add unit and property tests alongside each subsystem, then integration tests using genuine user-supplied kernels and products, independent validation cases, regression benchmarks, convergence runs, and reproducibility checks. Synthetic fixtures must be marked synthetic. A test is reported as passing only after it is actually executed.

## Phase 2 execution record

- `python -m pytest`: **7 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy`: **passed**, strict configuration, 4 source files checked (mypy 1.20.2).
- Editable base install (`python -m pip install -e .`): **passed** with build isolation.
- `python -m ruff check .`: **not run**. Installing the dev extra attempted to build Ruff from source on Termux; its Rust/maturin build failed against this Android toolchain. The GitHub Actions Linux runner is configured to run Ruff, but no hosted CI result is available.
- A no-build-isolation install was also attempted and failed because setuptools is not installed in the system interpreter; this does not affect the isolated editable install.

These Phase 2 results cover only software-foundation behavior, not scientific correctness.

## Phase 3 execution record

- `python -m pytest`: **25 passed** on Python 3.14.6 / Android (Termux), including analytic geometry references and boundary/failure cases.
- `python -m mypy`: strict check passed for all 9 source files.
- Ruff and hosted CI remain pending for the Termux/toolchain reasons above.
- Analytic expected/actual values and absolute errors are recorded in [the Phase 3 validation record](PHASE3_VALIDATION.md).

## Phase 4 execution record

- `pytest -q tests/unit/test_kernel_session.py`: **7 passed** on Python 3.14.6 / Android (Termux). These are mock-adapter lifecycle and failure-injection tests only.
- `python -m pytest -q`: **32 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy`: **passed**, strict configuration, 14 source files checked.
- Ruff was not run because Ruff is not installed in this environment. Hosted CI remains pending.
- No genuine kernels are available. Actual NAIF coverage, transformations, state queries, and results from mission kernels remain unevaluated.


## Phase 5 execution record

- `pytest -q tests/unit/test_terrain.py`: **9 passed**.
- `python -m pytest -q`: **41 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy`: **passed**, strict configuration, 17 source files checked.
- `python -m compileall -q src tests` and `git diff --check`: **passed**.
- Ruff was not run because the module is not installed. Hosted CI has not been run.
- Terrain data limitations and the supported label profile are documented in [Terrain data support](TERRAIN_DATA.md); test evidence is itemized in [Phase 5 validation](PHASE5_VALIDATION.md).
