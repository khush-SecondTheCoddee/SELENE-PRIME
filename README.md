# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is being developed as a modular research framework for lunar terrain horizons, solar and Earth occultation, and surface irradiance. The project is currently at the Phase 4 kernel and frame adapter stage. It does not yet calculate scientifically meaningful illumination results and has no verified real-kernel or real-terrain integration.

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

The package provides immutable shared metadata records, typed exceptions, deterministic provenance JSON, JSON-line logging, generic geometry primitives, hash-bearing kernel manifests, explicit SPICE session lifecycle management, guarded epoch-specific ephemeris queries, and a named frame service. Phase 4 lifecycle and adapter behavior is tested through a fake SPICE API. No genuine SPICE kernels are present, so real ephemeris coverage, frame availability, and lunar frame results remain unverified. No lunar datum, terrain model, or illumination calculation has been selected or verified.

## Install for development

Use Python 3.11 or later:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

The development extra installs pytest, Ruff, and mypy using the ranges in `pyproject.toml`. These ranges provide compatibility bounds, not a fully locked environment. A platform-specific dependency lock will be added after scientific and terrain dependencies are selected and resolved.

Run the configured checks:

```sh
python -m pytest
python -m ruff check .
python -m mypy
```

See [docs/TESTING.md](docs/TESTING.md) and [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Project documents

- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scientific assumptions](docs/SCIENTIFIC_ASSUMPTIONS.md)
- [Validation plan](docs/VALIDATION_PLAN.md)
- [Traceability matrix](docs/TRACEABILITY_MATRIX.md)

Real kernels, terrain products, passband choices, and reference benchmarks are not included. Install the optional `spice` extra and supply individually listed, authentic kernels with independently obtained SHA-256 digests for real SPICE use. See the design decision gates before interpreting any future result.
