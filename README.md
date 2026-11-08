# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is being developed as a modular research framework for lunar terrain horizons, solar and Earth occultation, and surface irradiance. The project is currently at the Phase 2 software-foundation stage. It does not yet calculate scientifically meaningful illumination results and has no verified real-kernel or real-terrain integration.

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

The package currently provides immutable shared metadata records, typed base exceptions, deterministic provenance JSON, JSON-line logging, and generic geometry primitives for vectors, rotations, ellipsoid coordinate conversion, and circle overlap. The ellipsoid requires caller-supplied parameters; no lunar datum, SPICE frame, terrain model, or illumination calculation has been selected or verified. Scientific and product-format dependencies remain deferred until their design gates are resolved.

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

Real kernels, terrain products, passband choices, and reference benchmarks are not included. See the design decision gates before interpreting any future result.
