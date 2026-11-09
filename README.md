# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is an incremental clean-room research framework for lunar terrain horizons, station-level apparent Sun/Earth geometry, solar-disk occultation, and surface irradiance. It currently provides restricted standalone scientific components, but not a validated end-to-end lunar illumination product. No genuine SPICE kernels or LOLA raster have been used for integration evidence.

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

Implemented components include generic vectors/rotations/ellipsoid math; owned SPICE kernel/session and frame adapters; a scoped detached PDS3 LOLA GDR reader; regular-grid interpolation; spherical terrain horizons; iterated geometric light-time positions for a body-fixed lunar station; finite solar-disk quadrature with pointwise terrain/Earth masks; provenance; successive-resolution comparisons; and generic sensitivity/Monte Carlo tools. Synthetic/analytic test coverage is executed locally. Datum conversion from product to station coordinates, independent real-kernel/real-product validation, physical passband selection, convergence/error bounds, and an end-to-end scientific report remain pending. See the traceability matrix and audit for exact scope.

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

- [Fifteen-phase delivery status](docs/PHASE_STATUS.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scientific assumptions](docs/SCIENTIFIC_ASSUMPTIONS.md)
- [Validation plan](docs/VALIDATION_PLAN.md)
- [Traceability matrix](docs/TRACEABILITY_MATRIX.md)
- [Terrain data support](docs/TERRAIN_DATA.md)
- [Phase 5 validation](docs/PHASE5_VALIDATION.md)
- [Phase 6 horizon](docs/PHASE6_HORIZON.md)
- [Phase 6 apparent geometry](docs/PHASE6_APPARENT_GEOMETRY.md)
- [Phase 7 radiometry and occultation](docs/PHASE7_RADIOMETRY_OCCULTATION.md)
- [Phase 8 convergence and uncertainty](docs/PHASE8_CONVERGENCE_UNCERTAINTY.md)
- [Error budget](docs/ERROR_BUDGET.md)
- [Executed analytic/synthetic benchmarks](reports/ANALYTIC_SYNTHETIC_BENCHMARKS.json)
- [Independent audit](docs/FINAL_INDEPENDENT_AUDIT.md)

No real kernels, terrain rasters, physical solar coefficient set, or lunar benchmark is included. The checked-in benchmark JSON is analytic/synthetic only. See [terrain product support and acquisition](docs/TERRAIN_DATA.md) for the supported PDS3 LOLA subset. Install the optional `spice` extra and supply authentic kernels and trusted SHA-256 digests for SPICE queries.
