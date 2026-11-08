# Requirements Traceability Matrix

**Status:** baseline links requirements to planned design and evidence. Implementation/evidence remains pending.

| Requirement | Design location | Planned verification | Current status |
|---|---|---|---|
| FR-01 Kernel lifecycle, integrity, provenance | `ARCHITECTURE.md` kernel subsystem/resource policy | Lifecycle unit/integration/failure tests | Not implemented; no kernels present |
| FR-02 Coverage and state-chain validation | Kernel/ephemeris contract | Genuine-kernel positive and missing-coverage negative tests | Not implemented; no kernels present |
| FR-03 Explicit frame transforms | Frame subsystem | Independent SPICE references, invariants, missing-frame tests | Not implemented |
| FR-04 Lunar datum and coordinate semantics | Coordinate subsystem | Independent round trips and known-point cases | Not implemented; datum choice open |
| FR-05 Real PDS/LOLA ingestion | Product adapter | Genuine label/product checks and corruption cases | Not implemented; no product found; formats open |
| FR-06 DEM interpolation | Grid/interpolation subsystem | Independent global/regional/edge/NoData cases | Not implemented |
| FR-07 Terrain horizon | Horizon/cache subsystem | Analytic fixtures and refinement/miss-error study | Not implemented |
| FR-08 Apparent Sun/Earth geometry | Ephemeris/apparent subsystem | Independent station-level SPICE reference cases | Not implemented; correction policy open |
| FR-09 Solar disk and irradiance | Radiometry subsystem | Analytic limits, independent integration, sourced radiometry | Not implemented; passband/source open |
| FR-10 Earth occultation | Earth occultation subsystem | Analytic overlap and independent quadrature | Not implemented; atmosphere policy open |
| FR-11 Joint masks | Composition subsystem | Joint overlap cases and independent disk-mask calculation | Not implemented |
| FR-12 Uncertainty/sensitivity | Uncertainty subsystem | Analytical and recorded Monte Carlo/sensitivity studies | Not implemented; distributions open |
| FR-13 Provenance/reporting | Reporting subsystem | Schema/provenance assertions and deterministic replay | Not implemented |
| FR-14 Benchmarks/convergence | Validation subsystem | Executed benchmark records and successive refinement report | Not implemented; no benchmark evidence |
| NFR scientific honesty | Models/reporting and validation policy | Review output labels, synthetic/real distinction, audit | Policy documented; implementation pending |
| NFR determinism | Validation/reproducibility design | Repeat-run comparison with fixed inputs | Not implemented |
| NFR safe failures/resources | Kernel and error contracts | Failure injection and cleanup tests | Not implemented |
| NFR reproducible quality gates | `pyproject.toml` and `.github/workflows/quality.yml` | Install, lint, typing, unit/integration CI evidence | Editable install, tests, and mypy pass locally; Ruff and hosted CI pending |
| Phase 2 foundation | `pyproject.toml`, `src/selene_prime/`, `README.md`, `docs/TESTING.md`, `docs/REPRODUCIBILITY.md`, `.github/workflows/quality.yml` | Editable install; unit tests; strict mypy; hosted CI | Implemented; local install, 7 foundation tests, and mypy passed. Ruff/hosted CI pending due Termux toolchain limitation. |
| Phase 3 generic geometry primitives | `src/selene_prime/geometry/`, `tests/unit/test_geometry.py`, `tests/references/geometry_reference_cases.json`, `docs/GEOMETRY_PRIMITIVES.md` | Analytic circle/ellipsoid references, vector/rotation invariants, coordinate round trips/domains, failure cases | Implemented and locally verified for generic math; no selected lunar parameters or external frame validation. |

## Evidence bookkeeping convention

When implementation begins, add source links and executed test/benchmark identifiers per row. Mark a requirement implemented only when code exists; mark verified only when stated evidence has actually run and passed. Partial support and unavailable external inputs remain explicit. Documentation or a planned test alone is not verification evidence.
