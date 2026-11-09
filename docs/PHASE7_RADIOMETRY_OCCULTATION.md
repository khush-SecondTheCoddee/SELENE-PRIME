# Phase 7: finite solar disk, terrain and Earth masks

`integrate_solar_disk` evaluates deterministic midpoint quadrature in a gnomonic tangent plane around the solar center. It supports caller-configured finite solar angular radius, solar center azimuth/elevation, 1-AU irradiance, Sun distance, linear limb-darkening coefficient, its source, passband, and resolution. No scientific irradiance or limb-darkening values are silently selected. Disk samples receive the linear intensity law and projected solid-angle weighting. The result reports visible, Earth-only, terrain-only, and combined blocked fractions, direct-normal irradiance, and direct-horizontal irradiance.

Earth occultation uses an opaque spherical angular disk and exact ray-direction angular separation at each quadrature point. Atmospheric transmission/refraction is excluded by default and reported as an explicit opaque-geometric-disk assumption; callers can name another assumption but must supply a future model to implement it. Terrain occultation evaluates each sample ray against a caller-provided azimuth-dependent horizon in local ENU geometry. Earth and terrain masks are combined sample by sample to avoid double counting. The apparent Sun/Earth ENU directions and angular radii must be calculated externally using validated station geometry.

## Numerical and scientific limits

The implementation uses a finite square midpoint grid and a linear limb-darkening law. Refinement changes quadrature error; no automatic error bound is inferred. The supplied test uses a uniform synthetic disk (`u=0`) so it does not establish a physical solar passband model. There is no selected solar reference spectrum/passband, limb-darkening source, Earth atmosphere transmission, terrain cache interpolation, or independent real-kernel comparison. Any nonuniform passband result remains caller-configured research input, not a bundled recommendation.

## Executed synthetic checks

`tests/unit/test_solar_disk.py` checks clear/fully blocked limits, comparison of a partial Earth overlap with analytic planar circle area, joint Earth/terrain masking without double-counting, near-horizon behavior, and input errors. The circle-area comparison is a small-angle synthetic check, not an exact spherical Earth-Sun validation. The complete current suite has 52 passing tests; strict mypy covers 22 source files.
