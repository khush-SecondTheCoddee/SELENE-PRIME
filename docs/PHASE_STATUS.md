# Fifteen-phase delivery status

This matrix separates implementation increments from the scientific evidence required by the original completion criteria. “Implemented” means code exists and local tests ran; it does not mean scientifically validated or research-ready.

| Phase | Engineering increment | Evidence/status | Remaining completion gate |
|---|---|---|---|
| 1. Requirements and architecture | Requirements, assumptions, subsystem boundaries, risk and validation records | Documented in `docs/`; requirements trace to current modules | Update acceptance criteria when a specific use case/data product is selected |
| 2. Clean architecture | Typed modular Python package, tests, build metadata, CI workflow | Package and CI config exist; local suite and strict typing executed | Hosted CI confirmation; end-to-end orchestrator/CLI not implemented |
| 3. SPICE and ephemeris | Kernel manifest, hash checks, lifecycle, ownership, actual query/frame guards | Five genuine DE421-compatible kernels acquired; every local SHA-256 matches the manifest | Real KernelSession load, coverage, frame, and station-state queries are pending; no independent ephemeris truth yet |
| 4. Reference frames and lunar datum | Generic ellipsoid math, named epoch-dependent SPICE rotations, and radial vector from an explicitly spherical DEM | Apollo 11 coordinates and LOLA DE421 ME datum/frame mapping are documented in the case runner | Real SPICE transform and round-trip calculation are pending execution |
| 5. PDS/LOLA terrain ingestion | Scoped detached PDS3 LOLA GDR integer IMG reader with provenance | Authentic PDS3 LDEM_16 label/image opened; image digest matches a byte-for-byte copy from a second official host | Label has no separately published trusted digest; additional products/profiles absent |
| 6. DEM interpolation | Regular cylindrical grid, NoData-aware bilinear sampling, wrap/edge rules | Real product grid and Apollo 11 station sample were opened; reproducible independent stencil comparison is prepared | Real interpolation/horizon run and regional-grid validation remain pending |
| 7. Terrain horizons | Great-circle DEM ray trace on explicit sphere; fail closed on unknown/non-spherical axes | Flat, ridge, slope, cache and geometry rejection fixtures pass | Ellipsoid support, signed error bound, subpixel ridge guarantee and real DEM comparison absent |
| 8. Solar/Earth apparent positions | Station observer from body-fixed vector and reception Moon state; iterated geometric LT | Analytic linear-state mock checks pass | Stellar aberration, authentic kernel coverage and independent SPICE station comparison absent |
| 9. Solar disk radiometry | Finite gnomonic disk quadrature, linear limb darkening, DNI/DHI, required caller source strings | Synthetic disk limits and mask tests pass | Source-backed physical passband, irradiance uncertainty, coefficient review absent |
| 10. Earth/terrain occultation | Exact angular ray-vs-Earth-disk test; per-sample terrain mask and joint composition | Synthetic and planar analytic checks pass | Earth atmospheric model and independent spherical reference absent |
| 11. Scientific validation | Analytic/synthetic benchmark runner with predeclared values/tolerances | Three benchmark cases executed and recorded; suite includes analytic/mocked references | Genuine PDS/LOLA, SPICE, physical irradiance and independent terrain benchmarks absent |
| 12. Multi-resolution convergence | Generic successive-resolution framework plus executed four-level synthetic refinement | Values and successive absolute deltas in `reports/SYNTHETIC_REFINEMENT_STUDY.json` | No acceptance tolerance; no nested real DEM/kernel cases or lunar convergence claim |
| 13. Uncertainty and sensitivity | Local finite differences and seeded independent-Gaussian Monte Carlo | Analytic polynomial and linear stochastic checks pass | Real input distributions, correlations, DEM/ephemeris/radiometry uncertainty models absent |
| 14. Quality and reproducibility | `pyproject.toml`, `uv.lock`, tests, mypy, GitHub Actions, reproducibility guidance | 62 local tests, strict typing, package build, benchmark scripts and lock consistency executed | Ruff build fails on Termux Rust toolchain; hosted CI not observed; no full end-to-end deterministic replay |
| 15. Independent red-team audit | Findings, severity, fixes and readiness disposition | Audit recorded in `docs/FINAL_INDEPENDENT_AUDIT.md` | Critical external-data/reference gates remain open; system is not research-evaluation ready |

## Remaining evidence gates

The station, epoch, authentic terrain product, datum/frame mapping, and individually hashed SPK/PCK/FK/LSK inputs are selected and recorded. Run `scripts/run_apollo11_case.py` to execute the pending SPICE-backed case. Independent station-level terrain and ephemeris truth, a passband-specific limb-darkening source with uncertainty, and requirements-derived reference tolerances remain necessary.
