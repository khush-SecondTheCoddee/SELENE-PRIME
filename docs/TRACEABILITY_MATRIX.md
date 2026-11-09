# Requirements Traceability Matrix

**Status:** requirements are traced to design and executed local evidence where available. Scientific integration evidence remains pending.

| Requirement | Design location | Planned verification | Current status |
|---|---|---|---|
| FR-01 Kernel lifecycle, integrity, provenance | `src/selene_prime/kernels/manifest.py`, `session.py` | Fake-API lifecycle, integrity, ownership and cleanup failure tests | Implemented; 7 adapter tests passed. Authentic kernel provenance/integration unavailable. |
| FR-02 Coverage and state-chain validation | `KernelSession.check_spk_body_coverage`, `validate_state_query` | Mocked gap/absent body and actual query failure tests; genuine SPK integration | Point-query and coverage guard implemented; mock failure cases passed. Genuine SPICE validation pending. |
| FR-03 Explicit frame transforms | `src/selene_prime/frames/service.py`, `KernelSession.frame_rotation` | Mocked proper rotation and missing frame; independent genuine SPICE references | Named frame service and guards implemented; mock test passed. Independent SPICE reference pending. |
| FR-04 Lunar datum and coordinate semantics | Coordinate subsystem | Independent round trips and known-point cases | Not implemented; datum choice open |
| FR-05 Real PDS/LOLA ingestion | `src/selene_prime/terrain/pds3_lola.py`, `docs/TERRAIN_DATA.md` | Synthetic PDS3 label/byte tests, digest mismatch, encoding and size rejection; genuine LOLA product integration | Partial implementation: detached PDS3 LOLA GDR cylindrical 16-bit signed integer IMG only. Synthetic tests pass; no real raster is available. |
| FR-06 DEM interpolation | `src/selene_prime/terrain/grid.py` | Analytic pixel-center, regional/global, antimeridian, pole, edge, NoData and malformed-axis cases | Regular simple cylindrical grid interpolation implemented; 9 terrain tests pass. NoData edges are rejected conservatively. |
| FR-07 Terrain horizon | `src/selene_prime/terrain/horizon.py`, `docs/PHASE6_HORIZON.md` | Analytic fixtures, curvature and ridge checks; later refinement/miss-error study | Implemented for planetocentric regular grids on a spherical reference surface; 4 synthetic tests pass. Ellipsoidal validation, certified capture/error bounds, and real-product integration pending |
| FR-08 Apparent Sun/Earth geometry | Ephemeris/apparent subsystem | Independent station-level SPICE reference cases | Not implemented; correction policy open |
| FR-09 Solar disk and irradiance | Radiometry subsystem | Analytic limits, independent integration, sourced radiometry | Not implemented; passband/source open |
| FR-10 Earth occultation | Earth occultation subsystem | Analytic overlap and independent quadrature | Not implemented; atmosphere policy open |
| FR-11 Joint masks | Composition subsystem | Joint overlap cases and independent disk-mask calculation | Not implemented |
| FR-12 Uncertainty/sensitivity | Uncertainty subsystem | Analytical and recorded Monte Carlo/sensitivity studies | Not implemented; distributions open |
| FR-13 Provenance/reporting | Reporting subsystem | Schema/provenance assertions and deterministic replay | Not implemented |
| FR-14 Benchmarks/convergence | Validation subsystem | Executed benchmark records and successive refinement report | Not implemented; no benchmark evidence |
| NFR scientific honesty | Models/reporting and validation policy | Review output labels, synthetic/real distinction, audit | Policy documented; implementation pending |
| NFR determinism | Validation/reproducibility design | Repeat-run comparison with fixed inputs | Not implemented |
| NFR safe failures/resources | `KernelSession` and `tests/unit/test_kernel_session.py` | Failure injection for setup, rollback, foreign pool, cleanup and query errors | Implemented; 7 adapter tests passed. Fork safety is fail-closed and real multi-process SPICE behavior remains unvalidated. |
| NFR reproducible quality gates | `pyproject.toml` and `.github/workflows/quality.yml` | Install, lint, typing, unit/integration CI evidence | Editable install, tests, and mypy pass locally; Ruff and hosted CI pending |
| Phase 2 foundation | `pyproject.toml`, `src/selene_prime/`, `README.md`, `docs/TESTING.md`, `docs/REPRODUCIBILITY.md`, `.github/workflows/quality.yml` | Editable install; unit tests; strict mypy; hosted CI | Implemented; local install, 7 foundation tests, and mypy passed. Ruff/hosted CI pending due Termux toolchain limitation. |
| Phase 3 generic geometry primitives | `src/selene_prime/geometry/`, `tests/unit/test_geometry.py`, `tests/references/geometry_reference_cases.json`, `docs/GEOMETRY_PRIMITIVES.md` | Analytic circle/ellipsoid references, vector/rotation invariants, coordinate round trips/domains, failure cases | Implemented and locally verified for generic math; no selected lunar parameters or external frame validation. |
| Phase 5 PDS3 terrain/grid subset | `src/selene_prime/terrain/`, `tests/unit/test_terrain.py`, `docs/TERRAIN_DATA.md`, `docs/PHASE5_VALIDATION.md` | Synthetic label/image byte fixture, scaling/offset reference, hash verification, file-layout rejection, independent grid-coordinate calculations | Partial format implementation; 9 focused terrain tests pass. The tests are synthetic and do not establish ingestion of an authentic PDS/LOLA product. |
| Phase 4 kernel/frame adapter | `src/selene_prime/kernels/`, `src/selene_prime/frames/`, `docs/PHASE4_VALIDATION.md` | Mocked lifecycle, integrity, frame, coverage and target-observer query failures; genuine kernel checks when supplied | Adapter implemented; 7 focused tests passed. Genuine-kernel validation unavailable. |

## Evidence bookkeeping convention

When implementation begins, add source links and executed test/benchmark identifiers per row. Mark a requirement implemented only when code exists; mark verified only when stated evidence has actually run and passed. Partial support and unavailable external inputs remain explicit. Documentation or a planned test alone is not verification evidence.

| Phase 6a terrain horizon | `src/selene_prime/terrain/horizon.py`, `tests/unit/test_horizon.py`, `docs/PHASE6_HORIZON.md` | Flat sphere, ridge, cache, bounds and pole synthetic cases | Implemented in the stated restricted geometry; full suite 45 tests and strict mypy pass. Not independently validated against real LOLA or external horizon software. |
