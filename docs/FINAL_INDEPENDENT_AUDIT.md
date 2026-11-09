# Final independent red-team audit

**Disposition:** SELENE-PRIME is **not ready for scientific research evaluation** against the original completion criteria. The codebase has tested engineering increments for restricted geometries, but no end-to-end computation has been run with authentic lunar terrain and a compatible genuine kernel set. No NASA approval, certification, flight qualification, or mission readiness is claimed.

The review inspected the kernel/session lifecycle, frame adapter, coordinate primitives, PDS3 reader, grid interpolation, horizon trace, apparent-position solver, disk radiometry/masks, uncertainty/convergence utilities, test evidence, and current documentation. The review distinguishes defects fixed during this turn from remaining evidence and scope gaps.

## Findings

| ID | Severity | Finding | Disposition / evidence |
|---|---|---|---|
| C-01 | Critical | There is no genuine PDS/LOLA raster, compatible SPICE kernel set, selected use case, or independent station-level lunar benchmark in the repository/environment. The implementation has no end-to-end real-data result, so the primary research validity claim cannot be established. | **Open external gate.** Synthetic and analytic records are explicitly labeled. User-supplied authentic inputs and references are required. The project is not research-evaluation ready. |
| H-01 | High | A spherical-DEM site helper computes a radial Cartesian vector while preserving the product frame label, but no implemented adapter maps a selected product datum/frame label into a verified SPICE body-fixed frame for a named lunar use case. Generic geometry and caller-supplied body-fixed station vectors do not close that integration gap. | **Open.** Product datum, station use case, and SPICE frame mapping are not selected. Current APIs require explicit vectors/frames; no automatic conversion is claimed. |
| H-02 | High | The terrain horizon is spherical-only and has no certified horizon-angle error bound. Sampling no more than half a DEM pixel can still miss subpixel or aliased terrain, while bilinear interpolation smooths narrow peaks. | **Open limitation.** The engine now rejects absent/non-spherical reference axes. Analytic ridge/slope fixtures check behavior but do not establish an error guarantee. Do not use for a requirement demanding bounded missed-ridge error. |
| H-03 | High | Solar irradiance, passband, limb-darkening source, and their uncertainties are caller-supplied strings/numbers. The software validates presence/range but does not verify the scientific authority or spectral applicability of those values. | **Open.** No coefficients are bundled or described as spectrally accurate. A sourced, reviewed parameter set and independent radiometry comparison are required. |
| M-01 | Medium | Apparent positions implement iterated geometric light time and explicitly omit stellar aberration and relativistic deflection. | **Documented scope.** The correction label states LT without `+S`; no broader apparent-geometry accuracy claim is made. Add/validate corrections if required by the selected use case. |
| M-02 | Medium | Earth occultation treats Earth as an opaque angular disk. Refraction, extinction, scattering, oblateness, and atmosphere are not modeled. | **Documented scope.** Result provenance names the opaque geometric model; no atmospheric illumination claim is made. |
| M-03 | Medium | Monte Carlo uncertainty assumes independent Gaussian inputs; covariance, bounded distributions, and physical-domain rejection policies are not implemented as first-class inputs. | **Open.** Generic tools preserve the seed and model outputs; they are not a lunar uncertainty budget. |
| M-04 | Medium | Horizon cache identity uses the live grid object's identity and does not hash mutable backing terrain bytes. | **Mitigation documented.** Cache holds the grid alive and has an explicit `clear_cache`; callers must clear it after changing a backing raster. Content-addressed immutability remains preferable. |
| M-05 | Medium | Ruff could not execute in Termux because its `maturin` Rust build failed against the installed Android Rust toolchain (`std/core/alloc` rlib artifacts unavailable). | **Environment limitation.** `uv.lock` was generated; CI config includes Ruff, but no hosted CI run is available in this audit. |
| L-01 | Low | No user-facing CLI or end-to-end orchestration command exists; scripts currently execute analytic/synthetic reports only. | **Open scope.** Library components can be called independently; installation and use-case workflow remains incomplete. |
| L-02 | Low | PDS4, compressed/JPEG2000, polar products, floating encodings, irregular DEM grids, and ellipsoidal horizon rays are outside the implemented profile. | **Explicitly unsupported.** Existing adapters reject or do not accept these inputs; support requires separate product specifications and tests. |

## Defects fixed during this audit

1. The horizon engine previously accepted a grid without confirming that its reference axes matched the spherical model. It now fails closed unless all three declared axes equal the configured reference radius; tests cover missing and oblate axes.
2. The horizon engine previously initialized every ray's horizon to zero, which hid downhill local DEM slopes. It now estimates the one-sided local horizon from a short station-relative probe. Synthetic flat and downhill-slope tests pass. This probe is not a formal error bound.
3. Solar disk configuration previously ignored Earth direction values when no Earth angular radius was supplied. Partial Earth geometry now raises an error.
4. Project README, architecture, traceability, and validation status had stale Phase 5/proposal language. They now identify present implementation and external evidence gaps.

## Executed review evidence

- `pytest -q`: 62 passed. `mypy --strict`: 27 source files passed. Exact evidence is also recorded in `docs/TESTING.md`.
- Analytic/synthetic benchmark execution is stored in `reports/ANALYTIC_SYNTHETIC_BENCHMARKS.json`.
- Four-level synthetic refinement and successive deltas are stored in `reports/SYNTHETIC_REFINEMENT_STUDY.json`; no tolerance/pass claim is assigned.
- `uv.lock` is generated and lock consistency is checked. `uv build --no-sources` passed. Ruff remains unavailable in this Termux build environment; hosted CI is not confirmed.

## Readiness decision

The Critical finding and High findings remain open because required scientific inputs, conventions, and external reference evidence are absent. The software is suitable for continued implementation and controlled synthetic tests only. It must not be described as scientifically validated, complete for lunar research evaluation, mission-ready, or certified.
