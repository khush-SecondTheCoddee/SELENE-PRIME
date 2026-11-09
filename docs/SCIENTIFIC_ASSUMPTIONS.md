# Scientific Assumptions and Limitations

**Status:** design assumptions register. Choices are provisional until linked to a product, use case, source, and validation case. Unresolved choices remain explicit in output metadata.

## Coordinate, time, and frame conventions

- Every epoch identifies its time system and conversion path. UTC input requires validated leap-second data; SPICE queries use the library's required ephemeris-time convention. No implicit conversion.
- Every vector/state identifies origin, frame, epoch, units, and aberration policy. Body-fixed orientation is time-dependent and requires compatible orientation data where needed.
- A site specifies latitude type, longitude range/sign, datum, reference model, height meaning, and coordinate epoch.
- Product elevation may reference a named surface; it is not automatically radial height above a sphere or ellipsoid.
- Native frame, datum, and registration come from product metadata. Unknown or ambiguous metadata is a hard validation issue.

## Ephemerides and apparent geometry

- Geometric and apparent directions differ. The SPICE aberration correction, including light-time and stellar-aberration treatment, is named and consistent for Sun and Earth.
- Station topocentric geometry requires station position and, when the selected apparent-state calculation requires it, observer velocity/state. A Moon-center direction with subtracted position is not an accepted substitute for a validated station observer query.
- Target/observer coverage and frame transformation availability are established for each requested epoch by actual queries. File presence or nominal coverage does not prove a successful state chain.
- Angular body radii require a sourced physical-radius convention and observer-target range.

## Terrain and horizon

- DEM values are sampled terrain at product-defined registration. The first implemented importer supports detached PDS3 LOLA GDR simple cylindrical integer IMG only; pixel-center registration follows the PDS3 image map projection convention. Polar stereographic, PDS4, JPEG2000, and PC/VAX floating encodings are explicitly rejected.
- For LOLA GDR `HEIGHT` samples, stored values are converted by `DN × SCALING_FACTOR` in metres; the label `OFFSET` is separately retained as the reference radius per the LOLA SIS. The adapter does not treat this reference radius as an additive height offset.
- Interpolation cannot reconstruct features below raster resolution and may smooth narrow ridges.
- Terrain horizon is observer-relative and requires curved-surface geometry. A tangent-plane approximation is limited to explicitly bounded conditions and cannot silently replace curved geometry.
- Adaptive sampling can bound numerical misses only under assumptions about terrain bandwidth/roughness and raster sampling. It cannot detect features absent from the DEM.
- NoData is not zero elevation. Policy distinguishes unknown obstruction from known terrain; default behavior should be invalid/unknown unless an explicitly declared conservative policy applies.
- Horizon cache keys include data identity, site, datum, frame, settings, and algorithm version; cached interpolation has an error estimate.

## Solar disk and radiometry

- Disk integration requires a stated angular radius, quadrature, passband, reference irradiance and uncertainty, and sourced limb-darkening law/coefficients. Coefficients cannot be transferred between passbands without justification.
- Direct-normal irradiance is unblocked irradiance normal to incoming rays under the selected model. Direct-horizontal irradiance uses the local surface normal and incidence geometry; a negative cosine contributes zero.
- Terrain/Earth visibility is a spatial mask over the finite solar disk. Multiplying independently integrated visibility fractions is generally invalid because obscured regions can overlap; combine masks before integration.
- Scattering, reflection, thermal emission, and atmospheric transmission are excluded unless separately modeled. Reports name exactly which components are included.

## Earth occultation

- Earth is a finite apparent disk under a declared radius/shape convention. Atmospheric refraction, extinction, and scattering are excluded by default or modeled with an explicit sourced option.
- Earth-Sun geometry uses the same lunar station epoch and compatible apparent-position conventions. Simplified angular circle overlap is used only within validated assumptions.

## Uncertainty, convergence, and validation

- Numerical integration/convergence error, terrain sampling/interpolation error, input uncertainty, parameter uncertainty, and model-form limitation are distinct.
- Refinement measures discretization convergence; it does not prove terrain, ephemeris, datum, or physical-model accuracy.
- Synthetic fixtures establish behavior for defined geometry only, not real lunar products or ephemerides.
- Independent references use an independent implementation/source or analytic derivation, not the code under test with different inputs.
- Monte Carlo studies declare distributions, correlations, sample count, random generator/seed, and convergence diagnostics; distribution assumptions may dominate.

## Open scientific decisions

1. Which lunar reference frame(s), datum/ellipsoid, and DEM products define initial use cases?
2. Which product label dialects and LOLA gridded product family are supported first?
3. Which passband and sourced solar irradiance/limb-darkening model define baseline output?
4. Which site/time cases and independent references can be obtained and documented?
5. Which uncertainty inputs/distributions are justified for the research context?

These are phase gates, not values to fill with unsupported conventional defaults.
