# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is being developed as a modular research framework for lunar terrain horizons, solar and Earth occultation, and surface irradiance. The project is currently at the Phase 5 terrain ingestion and grid stage. It does not yet calculate scientifically meaningful illumination results and has no verified real-kernel or real-terrain integration.

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

The package provides immutable shared metadata records, typed exceptions, deterministic provenance JSON, JSON-line logging, generic geometry primitives, hash-bearing kernel manifests, explicit SPICE session lifecycle management, guarded epoch-specific ephemeris queries, a named frame service, PDS3 LOLA GDR cylindrical IMG ingestion, and regular-grid interpolation. Phase 4 lifecycle and Phase 5 product/grid behavior have unit tests. The terrain product tests use synthetic bytes modeled on published label metadata; no genuine LOLA raster or SPICE kernels are included, so real-data integration and scientific illumination remain unverified.

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
- [Terrain data support](docs/TERRAIN_DATA.md)
- [Phase 5 validation](docs/PHASE5_VALIDATION.md)

Real kernels, terrain products, passband choices, and reference benchmarks are not included. See [terrain product support and acquisition](docs/TERRAIN_DATA.md) for the currently supported PDS3 LOLA subset. Install the optional `spice` extra and supply authentic, individually listed kernels with independently obtained SHA-256 digests for real SPICE use. See the design decision gates before interpreting any future result.
