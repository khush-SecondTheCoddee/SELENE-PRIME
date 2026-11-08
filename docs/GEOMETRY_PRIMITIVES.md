# Phase 3 — Independent Geometry Primitives

**Status:** implemented for generic geometry; no lunar datum, body frame, ephemeris, or mission case is selected or validated.

## API and conventions

- `Vector3` stores finite components with one explicit unit label. Addition/subtraction require identical labels. Dot products return a scalar (the caller tracks squared units); cross products retain an explicitly parenthesized squared unit label. Normalization returns a direction labeled `1`. Vectors do not imply an origin or reference frame.
- `Rotation3` maps column vectors by left multiplication. It accepts only 3×3 proper orthonormal matrices (`RᵀR = I`, `det(R)=+1`) within an explicit tolerance, and preserves a vector's unit label. It has no frame names or epoch; those are required at the later frame-service boundary.
- `ReferenceEllipsoid` requires caller-provided semi-major/minor axes in metres, an identifier, and a parameter-source string. It deliberately contains no built-in lunar parameter set. This implementation accepts oblate or spherical ellipsoids.
- `GeodeticPoint` means planetographic latitude, east longitude, and height above the named ellipsoid. `PlanetocentricPoint` means latitude measured from the body-centered radial vector, east longitude, and distance from the origin. Angles are radians. Longitude must explicitly use `EAST_180` (−π…π) or `EAST_360` (0…2π). At an exact pole the inverse chooses longitude zero as a deterministic convention because longitude is geometrically undefined there.
- Cartesian coordinate conversions require metre-valued vectors and matching ellipsoid identifiers. The geodetic inverse iterates a normal-coordinate equation; failure to converge is reported. The origin has no defined coordinate result. Interior points can have ambiguous normal coordinates; only tested cases are claimed.
- `circle_overlap_area` returns the analytical intersection area for coplanar disks whose radii and separation share a unit. `occulted_fraction` divides that area by the target disk area and clamps only final roundoff to [0,1]. This is geometry only: it does not model limb darkening, atmospheric effects, or a spatial visibility mask.

The analytical reference fixture uses an intentionally simple ellipsoid with axes 2 m and 1 m. It is a math fixture, not a lunar datum. For geodetic latitude 45° at zero height, the independently reduced ellipsoid equations give `x=4/√5`, `z=1/√5`; radial latitude is `atan(1/4)`. For unit circles one radius apart, the overlap area is `2π/3 − √3/2`, giving a covered fraction of approximately 0.39100221895577075. The saved reference values are compared directly by tests.

## Validation evidence

`tests/unit/test_geometry.py` covers vector arithmetic/unit mismatch, a known 90° rotation and inverse, rejection of improper matrices, analytic circle overlap boundaries and partial overlap, an independent ellipsoid point, coordinate round trips, pole handling, longitude convention, mismatched ellipsoid IDs, invalid origin, and unit rejection. The references are in `tests/references/geometry_reference_cases.json`.

These are analytic/synthetic math references; they are not an external lunar-coordinate or SPICE frame validation. Real datum parameters, published reference points, frame-rotation cases, broader inverse robustness, and scientific error tolerances remain pending until a concrete supported datum/frame/use case is selected.
