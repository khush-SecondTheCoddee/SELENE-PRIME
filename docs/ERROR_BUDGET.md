# Error budget status

A numerical error budget requires selected scientific inputs and requirements for the evaluated use case. None are currently available for a real lunar illumination run. This document separates known error contributors from quantified numerical results; the table intentionally leaves quantitative bounds pending rather than assigning convenient tolerances.

| Contributor | Current model/control | Evidence available | Quantitative bound/status |
|---|---|---|---|
| Terrain vertical error | Inherited from selected DEM product; no uncertainty propagation from labels yet | Synthetic DEM interpolation and horizon fixtures | Pending real product accuracy and spatial covariance |
| Reference-surface mismatch | Horizon now rejects missing axes or axes not equal to its explicit spherical radius | Failure tests for unknown and oblate axes | Prevented by fail-closed validation; ellipsoidal ray geometry remains unsupported |
| DEM horizontal resolution / ridge loss | Horizon sample step defaults to <= half local pixel; bilinear DEM interpolation | Isolated synthetic ridge detection | No certified miss-angle bound; source may omit subpixel terrain |
| Station coordinates/datum | Apparent service accepts explicit body-fixed vector in km | Mock rotations and state chain | Product datum conversion and station survey uncertainty pending |
| Ephemeris and lunar orientation | Session validates actual SPICE state/frame queries | Mock failure/geometry tests | No genuine kernel set/reference comparison available |
| Solar angular radius/direction | Caller-provided apparent geometry | Synthetic disk geometry | Kernel/reference uncertainty pending |
| Solar irradiance/passband | Caller-provided irradiance and passband provenance | Synthetic configured values only | Physical source and uncertainty not selected |
| Limb darkening | Caller-provided linear coefficient and source | Uniform disk synthetic tests | No passband-specific coefficient source selected |
| Earth occultation atmosphere | Opaque geometric disk | Synthetic angular-disk mask | Atmospheric transmission/refraction omitted and unquantified |
| Disk quadrature | Configured finite midpoint grid | Analytic limits and overlap comparison | No successive physical-model convergence run yet |
| Horizon ray sampling | Configurable <= half-pixel default plus sample count | Flat/ridge synthetic fixtures | Angle error tolerance and independent refinement pending |
| Monte Carlo sampling | Seeded independent Gaussian input model | Synthetic linear model repeatability | No lunar distributions or finite-sample convergence study |

Numerical convergence error and input/model uncertainty must remain separate in future reports. Tolerances require a downstream scientific requirement or independently sourced reference before they can be set.

The synthetic refinement run in `reports/SYNTHETIC_REFINEMENT_STUDY.json` lists successive differences, but it assigns no acceptance tolerance and must not be read as a populated lunar error budget.
