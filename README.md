# SELENE-PRIME

**Version 1.0.0 — clean-room research implementation**

SELENE-PRIME is being developed as a modular research framework for lunar terrain horizons, solar and Earth occultation, and surface irradiance. The project has implemented its software foundation, generic geometry primitives, and an initial reference-frame service. It does not yet calculate scientifically meaningful lunar illumination results and has no verified real-kernel, lunar-datum, or real-terrain integration.

This is research software. It is not NASA-approved, certified, flight-qualified, or mission-ready.

## Current foundation

The package provides immutable shared metadata records, typed exceptions, deterministic provenance JSON, JSON-line logging, generic geometry primitives, and a fail-closed frame transformation interface. Frame names and center identifiers must be explicitly declared by the caller. An optional SpiceyPy adapter calls SPICE `pxform` using an already furnished kernel pool.

No default lunar frame or lunar datum is selected. The current frame service rotates vectors only between frames declared to share an origin; it does not transform states between different centers. Kernel lifecycle, kernel coverage, time conversion, triaxial lunar shape, terrain, and illumination calculations remain future work. See [the Phase 4 implementation record](docs/PHASE4_FRAME_DESIGN.md).

## Install for development

Use Python 3.11 or later:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

For the optional SPICE frame adapter, install SpiceyPy:

```sh
python -m pip install -e ".[spice]"
```

For both development tools and SPICE:

```sh
python -m pip install -e ".[dev,spice]"
```

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
- [Phase 4 frame design and limitations](docs/PHASE4_FRAME_DESIGN.md)

Real kernels, a selected lunar datum, terrain products, passband choices, and independent lunar reference benchmarks are not included. Do not interpret the software interface tests as validation of lunar frame definitions or scientific results.
