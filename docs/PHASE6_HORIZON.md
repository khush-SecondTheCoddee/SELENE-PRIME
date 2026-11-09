# Phase 6: terrain horizon implementation record

## Implemented scope

`TerrainHorizonEngine` traces a station-relative great-circle bearing on a product's named reference sphere. It samples the actual DEM, adds radial terrain heights, converts samples to body-centered Cartesian coordinates, and evaluates their angle in the station's east/north/up tangent basis. Results are azimuth-specific and include maximum-sample range, sample count, largest sample step, product identifier, and reference radius. The bounded, synchronized cache can be explicitly cleared.

The default step is at most half the smaller local angular-grid cell (including east-west contraction by cosine latitude). A caller can refine to a smaller step or set a sample ceiling. Terrain beyond regional product bounds and any interpolation footprint touching NoData raise errors; these conditions are not silently treated as clear horizon. Flat reference-sphere terrain has a zero geometric-horizon baseline.

## Limits

This implementation requires planetocentric latitude on a regular simple-cylindrical grid and interprets product elevation radially from `reference_radius_m`. It rejects polar stations. It does not yet provide ellipsoidal surface geometry, frame/datum transformation, global azimuth profile caching/interpolation, certified ridge capture, or an error bound on a horizon angle. Half-pixel sampling limits sampling gaps relative to raster spacing, but bilinear interpolation can smooth narrow peaks and source DEMs cannot resolve subpixel terrain. Genuine LOLA product validation remains pending. This subsystem is not a mission-certified horizon model.

## Executed evidence

`pytest -q tests/unit/test_horizon.py` covers a flat sphere, an isolated ridge, azimuth normalization/cache clearing, and regional/polar failure paths. The synthetic ridge fixture establishes qualitative detection and the expected positive horizon; it is not real lunar data or an independent mission benchmark. Full test-suite and typing evidence are recorded in the current delivery note/CI history.
