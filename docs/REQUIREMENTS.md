# SELENE-PRIME 1.0.0 — Technical Requirements

**Status:** Requirements baseline with incremental implementation and executed synthetic evidence recorded in the phase status and traceability documents. No end-to-end lunar scientific result is verified.

## Purpose and scope

SELENE-PRIME is a clean-room, reproducible research framework for estimating illumination and irradiance at lunar surface locations. It combines kernels/ephemerides, explicit lunar frames and datum, terrain elevations and horizons, finite solar-disk visibility, Earth occultation, and uncertainty reporting. It is a research tool; this specification grants no NASA approval, certification, flight qualification, or mission-readiness claim.

The primary output is a provenance-bearing result for a stated site, epoch, terrain product, kernel set, radiometric model, and numerical configuration. Outputs distinguish geometric visibility, irradiance, uncertainty, and numerical convergence. Missing inputs or unsupported geometry must produce a clear failure or qualified result, never a silently fabricated/default scientific value.

## Repository reconnaissance (2026-11-08)

- The working directory is a general home workspace containing unrelated projects, not a Git repository at its root.
- Searches found no SELENE, LOLA, lunar illumination, or SPICE project files and no matching project-level Python packaging or test configuration.
- No candidate PDS labels, lunar rasters, SPK, CK, PCK, FK, or LSK kernels were found in the inspected workspace.
- Python imports checked: `pytest` and `pydantic` are available; `spiceypy`, `numpy`, `scipy`, `rasterio`, and `hypothesis` are unavailable in the current interpreter. This is an environment observation, not a dependency decision.
- Existing home files and neighboring projects are not treated as source code or validation evidence.

## Users and operating modes

1. **Research analyst:** supplies site/time, terrain, kernels, and model settings; receives numeric results and provenance.
2. **Data curator:** validates and inventories terrain products and kernel manifests.
3. **Developer/validator:** runs unit, integration, regression, independent-reference, convergence, and uncertainty workflows.

Initial supported operation is a Python library plus reproducible command-line benchmark/report entry points. A GUI, web service, real-time operations, and mission flight software are out of scope for 1.0.0.

## Functional requirements

| ID | Requirement | Acceptance evidence (future gate) |
|---|---|---|
| FR-01 | Manage explicit SPICE kernel manifests, SHA-256, provenance, ownership, load/unload lifecycle, rollback, and actionable errors. | Lifecycle tests plus genuine-kernel integration; mismatch, coverage, frame, and cleanup failures reject safely. |
| FR-02 | Validate requested ephemeris query, target-observer state chain, time coverage, and required frame/orientation data at the requested epoch. | Negative tests for missing coverage/frame cases and independent reference queries. |
| FR-03 | Transform between explicitly named inertial and body-fixed frames using validated SPICE transformations; reject unknown/unavailable transforms. | Rotation invariants, independent known-frame cases, and failure injection. |
| FR-04 | Convert geodetic/planetographic, planetocentric, Cartesian, and DEM-native coordinates using a named lunar datum and verified parameters. Current generic ellipsoid math and spherical-grid vector conversion do not select/map a lunar product datum to SPICE. | Independent forward/inverse tests and source-backed reference points within declared tolerances. |
| FR-05 | Ingest selected real PDS/LOLA product types, preserving labels, identifiers, encoding, scaling, units, NoData, projection, registration, datum, resolution, integrity, and provenance. Initial implementation scopes PDS3 LOLA GDR cylindrical IMG, 16-bit signed integer. | Genuine product checks; malformed metadata/checksum cases reject. Synthetic arrays do not count as ingestion evidence. |
| FR-06 | Validate DEM grids and provide documented NoData-aware interpolation with longitude convention, pixel registration, edges, poles, and antimeridian behavior explicit. Initial implementation supports regular simple cylindrical LOLA grids. | Independent cases for global 0–360 and −180–180 grids, regions, edges, NoData, malformed grids, and wraparound. |
| FR-07 | Compute station-relative, azimuth-dependent terrain horizons with lunar curvature, adaptive resolution-aware sampling, configured range/tolerance, cache provenance, and cache error estimate. | Analytic fixtures and refinement studies show ridge capture and bounded error for stated cases. |
| FR-08 | Compute topocentric Sun and Earth apparent geometry at the lunar station for documented time scale, observer state, frame, and aberration/light-time policy. | Independent SPICE reference cases meet declared angular tolerances and reject invalid epochs/frames. |
| FR-09 | Integrate a finite solar disk using a named, sourced, passband-appropriate radiometric and limb-darkening model; calculate visible fraction and direct-normal/horizontal irradiance. | Analytic limits, independent numerical integration, sourced irradiance reference, and convergence evidence. |
| FR-10 | Compute Earth disk occultation of the solar disk including angular radii and declared atmospheric assumptions; keep it inspectable separately from terrain obstruction. | Analytic circle-overlap cases and independent quadrature. |
| FR-11 | Combine terrain and Earth obstruction masks without double counting, with clear geometric assumptions. | Joint-obstruction boundary cases and comparison to independent ray/disk integration. |
| FR-12 | Quantify uncertainty and sensitivity for terrain, site coordinates, datum, ephemerides, solar irradiance/limb darkening, atmosphere, and numerical integration. | Reproducible analytical/sensitivity/Monte Carlo reports; uncertainty separate from numerical convergence. |
| FR-13 | Emit machine-readable results and human-readable reports with input hashes/identifiers, model/config versions, units, limitations, and benchmark records. | Deterministic fixture replay and schema/provenance assertions. |
| FR-14 | Provide reproducible benchmark and multi-resolution workflows for visible fraction, irradiance, horizon, Earth occultation, and combined visibility. | Recorded inputs, references, successive-refinement deltas, tolerances, and actual results; no unexecuted result marked pass. |

## Nonfunctional requirements

- **Scientific honesty:** distinguish observed inputs, assumptions, synthetic fixtures, numerical estimates, and external reference values. No fabricated data, checksum, coverage, coefficient, or benchmark.
- **Traceability:** every output is attributable to exact input products, kernel manifest, model, configuration, and software revision/version.
- **Determinism:** fixed inputs and deterministic algorithms produce stable outputs within declared platform tolerances; stochastic studies record seed and sampling configuration.
- **Failure behavior:** reject invalid physical ranges, nonfinite inputs, incompatible frames/datums, missing coverage, corrupt products, and unsupported formats with typed exceptions and context.
- **Resource safety:** explicit context-managed kernel lifetime; thread/process policy documented; cleanup errors surfaced without masking active failures.
- **Modularity:** public subsystem contracts permit isolated unit tests and alternative validated implementations.
- **Numerical reporting:** units and meaningful significant figures are mandatory; convergence is not equated with total scientific accuracy.
- **Maintainability:** type annotations, public API docstrings, structured logging, reproducible dependency resolution, lint/type/test CI, installation and data-acquisition guidance.
- **Portability:** supported Python/platform matrix selected after dependency and SPICE assessment; current Termux environment is not presumed supported.

## Proposed inputs and outputs

Inputs: UTC/ET epoch with explicit conversion provenance; site with latitude/longitude convention, datum, elevation meaning, and coordinate epoch; terrain product or explicitly marked synthetic fixture; kernel manifest with hashes, roles, and provenance; radiometric passband/reference/limb-darkening source; atmospheric, integration, horizon, and uncertainty settings.

Outputs: Sun/Earth apparent directions and angular radii in named frames; terrain horizon versus azimuth and error diagnostics; solar visible fraction and separate terrain/Earth/combined visibility; direct-normal and direct-horizontal irradiance with units; uncertainty and convergence diagnostics; warnings and provenance. Benchmark records include reference source/value, tolerance, actual value, absolute/relative error where defined, and pass/fail only after execution.

## Scientific acceptance policy

No universal numeric tolerance is asserted before a model, use case, reference source, and error budget are selected. Each validation case must state a predeclared tolerance justified by the allocated error budget and independent reference quality. A result passes only after actual execution. Unavailable references remain pending, not passing.

## Out of scope for initial release

Flight/mission certification; spacecraft/lander command or control; operational safety claims; thermal reradiation, subsurface conduction, albedo/emission, scattering, and full spectral transfer unless separately added and validated; global completeness claims for LOLA products; automatic trust of arbitrary kernels; unsupported product formats.
