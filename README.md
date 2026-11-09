# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is an incremental clean-room research framework for lunar terrain horizons, station-level apparent Sun/Earth geometry, solar-disk occultation, and surface irradiance. It currently provides restricted standalone scientific components, but not a validated end-to-end lunar illumination product. Authentic LOLA terrain and an individually hash-pinned DE421 kernel set have now been acquired for an Apollo 11 case study. The reproducible runner is checked in, but its full SPICE-backed case has not yet been executed; see [real-data case status](docs/REAL_DATA_CASE.md).

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

Implemented components include generic vectors/rotations/ellipsoid math; owned SPICE kernel/session and frame adapters; a scoped detached PDS3 LOLA GDR reader; regular-grid interpolation; spherical terrain horizons; iterated geometric light-time positions for a body-fixed lunar station; finite solar-disk quadrature with pointwise terrain/Earth masks; provenance; successive-resolution comparisons; and generic sensitivity/Monte Carlo tools. Synthetic/analytic test coverage is executed locally. The Apollo 11 datum/frame transformation and calculation workflow are implemented in the case runner but await a successful SPICE-backed execution. Independent ephemeris truth, a reviewed physical passband, convergence/error bounds, and an end-to-end scientific report remain pending. See the traceability matrix and audit for exact scope.

## Install for development

Use Python 3.11 or later:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

The development extra installs pytest, Ruff, and mypy using the ranges in `pyproject.toml`. These ranges provide compatibility bounds, not a fully locked environment. The checked-in `uv.lock` pins development and optional SPICE dependencies. Runtime kernel and terrain files are user-supplied and not included.

Run the configured checks:

```sh
python -m pytest
python -m ruff check .
python -m mypy
```

See [docs/TESTING.md](docs/TESTING.md) and [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md).

## Project documents

- [Fifteen-phase delivery status](docs/PHASE_STATUS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scientific assumptions](docs/SCIENTIFIC_ASSUMPTIONS.md)
- [Validation plan](docs/VALIDATION_PLAN.md)
- [Traceability matrix](docs/TRACEABILITY_MATRIX.md)
- [Real-data Apollo 11 case and run status](docs/REAL_DATA_CASE.md)
- [Terrain data support](docs/TERRAIN_DATA.md)
- [Phase 5 validation](docs/PHASE5_VALIDATION.md)
- [Phase 6 horizon](docs/PHASE6_HORIZON.md)
- [Phase 6 apparent geometry](docs/PHASE6_APPARENT_GEOMETRY.md)
- [Phase 7 radiometry and occultation](docs/PHASE7_RADIOMETRY_OCCULTATION.md)
- [Phase 8 convergence and uncertainty](docs/PHASE8_CONVERGENCE_UNCERTAINTY.md)
- [Error budget](docs/ERROR_BUDGET.md)
- [Executed analytic/synthetic benchmarks](reports/ANALYTIC_SYNTHETIC_BENCHMARKS.json)
- [Independent audit](docs/FINAL_INDEPENDENT_AUDIT.md)

No kernel binaries or terrain rasters are included in Git. The acquired local files are ignored; the checked-in benchmark JSON remains analytic/synthetic only until the real case is run. See [terrain product support and acquisition](docs/TERRAIN_DATA.md) for the supported PDS3 LOLA subset. Install the optional `spice` extra and supply authentic kernels and trusted SHA-256 digests for SPICE queries.
