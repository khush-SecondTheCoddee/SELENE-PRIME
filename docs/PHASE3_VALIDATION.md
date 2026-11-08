# Phase 3 Geometry Validation Record

**Execution date:** 2026-11-08 (UTC date from the project environment).  
**Environment:** Python 3.14.6, Android/Termux.  
**Scope:** generic analytic geometry only; no lunar datum, external frame service, SPICE kernel, or real terrain product.

| Case | Reference | Tolerance | Actual | Absolute error | Status |
|---|---|---:|---:|---:|---|
| Unit-circle partial overlap, radii 1, separation 1 | `2π/3 − √3/2 = 1.2283696986087567` | 2e-15 area units | 1.228369698608757 | 4.440892098500626e-16 | Pass |
| Fraction of target unit disk occulted in same case | Analytic area divided by π: 0.39100221895577075 | 2e-15 | 0.39100221895577075 | 0 | Pass |
| Oblate ellipsoid at 45° planetographic latitude, zero height, axes 2 m/1 m, x | `4/√5 = 1.7888543819998317 m` | 1e-14 m | 1.788854381999832 m | 2.220446049250313e-16 m | Pass |
| Same point, z | `1/√5 = 0.4472135954999579 m` | 1e-14 m | 0.4472135954999579 m | 0 | Pass |
| Inverse coordinate latitude/longitude/height | 45° / 0 / 0 m by analytic construction | 2e-14 rad, 2e-14 rad, 2e-14 m | 45° / 0 / 0 m | 0 / 0 / 0 | Pass |
| Same surface point planetocentric latitude | `atan2(1,4) = 0.24497866312686414 rad` | 1e-15 rad | 0.24497866312686412 rad | 2.7755575615628914e-17 rad | Pass |

The reference equations and values are stored in `tests/references/geometry_reference_cases.json`. They are independent analytic identities rather than an external planetary-science dataset. Round-trip, domain, poles, vector invariants, and invalid-input checks are software tests; they do not constitute external physical validation.

The executed suite at this point reported 25 passing tests (7 Phase 2 foundation tests and 18 Phase 3 geometry tests). Strict mypy passed for all source files. Ruff and hosted CI remain unexecuted in the current environment; see `docs/TESTING.md`.
