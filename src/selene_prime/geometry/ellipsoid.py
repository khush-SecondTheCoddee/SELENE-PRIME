"""Generic reference-ellipsoid coordinate conversions.

No lunar radii or datum are bundled. Callers must supply explicitly sourced
ellipsoid parameters. Geodetic latitude here means planetographic latitude.
Angles are radians and longitudes are east-positive under the selected range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from selene_prime.errors import ConfigurationError
from selene_prime.geometry.vectors import Vector3


class LongitudeConvention(str, Enum):
    """Supported east-positive longitude domains, in radians."""

    EAST_180 = "east_-pi_to_pi"
    EAST_360 = "east_0_to_2pi"


@dataclass(frozen=True, slots=True)
class ReferenceEllipsoid:
    """Named oblate ellipsoid with source provenance supplied by the caller."""

    identifier: str
    semi_major_axis_m: float
    semi_minor_axis_m: float
    parameter_source: str

    def __post_init__(self) -> None:
        if not self.identifier.strip() or not self.parameter_source.strip():
            raise ConfigurationError("ellipsoid identifier and parameter_source are required")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (self.semi_major_axis_m, self.semi_minor_axis_m)
        ):
            raise ConfigurationError("ellipsoid axes must be finite numbers")
        if self.semi_major_axis_m <= 0 or self.semi_minor_axis_m <= 0:
            raise ConfigurationError("ellipsoid axes must be positive")
        if self.semi_minor_axis_m > self.semi_major_axis_m:
            raise ConfigurationError("this implementation supports oblate or spherical ellipsoids")

    @property
    def eccentricity_squared(self) -> float:
        """First eccentricity squared."""
        ratio = self.semi_minor_axis_m / self.semi_major_axis_m
        return 1.0 - ratio * ratio


@dataclass(frozen=True, slots=True)
class GeodeticPoint:
    """Planetographic latitude, east longitude, and height above ellipsoid."""

    latitude_rad: float
    longitude_rad: float
    height_m: float
    ellipsoid_id: str
    longitude_convention: LongitudeConvention

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (self.latitude_rad, self.longitude_rad, self.height_m)
        ):
            raise ConfigurationError("geodetic coordinate values must be finite numbers")
        if not -math.pi / 2 <= self.latitude_rad <= math.pi / 2:
            raise ConfigurationError("planetographic latitude must be within [-pi/2, pi/2]")
        if not self.ellipsoid_id.strip():
            raise ConfigurationError("ellipsoid_id must not be empty")
        if not isinstance(self.longitude_convention, LongitudeConvention):
            raise ConfigurationError("longitude_convention must be explicit")
        _validate_longitude(self.longitude_rad, self.longitude_convention)


@dataclass(frozen=True, slots=True)
class PlanetocentricPoint:
    """Planetocentric latitude, east longitude, and distance from the origin."""

    latitude_rad: float
    longitude_rad: float
    radius_m: float
    ellipsoid_id: str
    longitude_convention: LongitudeConvention

    def __post_init__(self) -> None:
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (self.latitude_rad, self.longitude_rad, self.radius_m)
        ):
            raise ConfigurationError("planetocentric coordinate values must be finite numbers")
        if not -math.pi / 2 <= self.latitude_rad <= math.pi / 2:
            raise ConfigurationError("planetocentric latitude must be within [-pi/2, pi/2]")
        if self.radius_m <= 0:
            raise ConfigurationError("planetocentric radius must be positive")
        if not self.ellipsoid_id.strip():
            raise ConfigurationError("ellipsoid_id must not be empty")
        if not isinstance(self.longitude_convention, LongitudeConvention):
            raise ConfigurationError("longitude_convention must be explicit")
        _validate_longitude(self.longitude_rad, self.longitude_convention)


def _validate_longitude(longitude_rad: float, convention: LongitudeConvention) -> None:
    if convention is LongitudeConvention.EAST_180:
        valid = -math.pi <= longitude_rad <= math.pi
    else:
        valid = 0.0 <= longitude_rad <= 2.0 * math.pi
    if not valid:
        raise ConfigurationError(f"longitude is outside convention {convention.value}")


def geodetic_to_cartesian(point: GeodeticPoint, ellipsoid: ReferenceEllipsoid) -> Vector3:
    """Convert planetographic coordinates to body-centered Cartesian metres."""
    _require_ellipsoid(point.ellipsoid_id, ellipsoid)
    a = ellipsoid.semi_major_axis_m
    e2 = ellipsoid.eccentricity_squared
    sin_lat = math.sin(point.latitude_rad)
    cos_lat = math.cos(point.latitude_rad)
    prime_vertical_radius = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
    radial = (prime_vertical_radius + point.height_m) * cos_lat
    return Vector3(
        radial * math.cos(point.longitude_rad),
        radial * math.sin(point.longitude_rad),
        (prime_vertical_radius * (1.0 - e2) + point.height_m) * sin_lat,
        "m",
    )


def cartesian_to_geodetic(
    position: Vector3,
    ellipsoid: ReferenceEllipsoid,
    longitude_convention: LongitudeConvention,
) -> GeodeticPoint:
    """Convert body-centered Cartesian metres to planetographic coordinates.

    An iterative normal-coordinate solution is used for non-equatorial points.
    At either exact polar axis,
    longitude is undefined geometrically; this API uses east longitude zero as a
    deterministic canonical value.
    """
    _require_position_unit(position)
    p = math.hypot(position.x, position.y)
    radius = math.hypot(p, position.z)
    if radius == 0.0:
        raise ConfigurationError("planetographic coordinates are undefined at the ellipsoid origin")
    if p == 0.0:
        latitude = math.copysign(math.pi / 2.0, position.z)
        height = abs(position.z) - ellipsoid.semi_minor_axis_m
        longitude = 0.0
    elif position.z == 0.0:
        # The equatorial plane has a direct, well-defined normal coordinate.
        latitude = 0.0
        height = p - ellipsoid.semi_major_axis_m
        longitude = math.atan2(position.y, position.x)
    else:
        a = ellipsoid.semi_major_axis_m
        e2 = ellipsoid.eccentricity_squared
        lower = -math.pi / 2.0
        upper = math.pi / 2.0
        converged = False
        for _ in range(100):
            latitude = (lower + upper) / 2.0
            sin_lat = math.sin(latitude)
            prime_vertical_radius = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
            residual = (
                p * math.tan(latitude)
                - e2 * prime_vertical_radius * sin_lat
                - position.z
            )
            if abs(residual) <= 1e-14 * max(1.0, radius):
                converged = True
                break
            if residual > 0.0:
                upper = latitude
            else:
                lower = latitude
            if upper - lower <= 1e-14:
                latitude = (lower + upper) / 2.0
                converged = True
                break
        if not converged:
            raise ConfigurationError("geodetic inverse did not converge for this position")
        sin_lat = math.sin(latitude)
        cos_lat = math.cos(latitude)
        prime_vertical_radius = a / math.sqrt(1.0 - e2 * sin_lat * sin_lat)
        if abs(cos_lat) > 0.5:
            height = p / cos_lat - prime_vertical_radius
        else:
            height = position.z / sin_lat - prime_vertical_radius * (1.0 - e2)
        longitude = math.atan2(position.y, position.x)
    if longitude_convention is LongitudeConvention.EAST_360 and longitude < 0.0:
        longitude += 2.0 * math.pi
    return GeodeticPoint(latitude, longitude, height, ellipsoid.identifier, longitude_convention)


def planetocentric_to_cartesian(point: PlanetocentricPoint) -> Vector3:
    """Convert planetocentric latitude/longitude/radius to Cartesian metres."""
    cos_lat = math.cos(point.latitude_rad)
    return Vector3(
        point.radius_m * cos_lat * math.cos(point.longitude_rad),
        point.radius_m * cos_lat * math.sin(point.longitude_rad),
        point.radius_m * math.sin(point.latitude_rad),
        "m",
    )


def cartesian_to_planetocentric(
    position: Vector3,
    ellipsoid: ReferenceEllipsoid,
    longitude_convention: LongitudeConvention,
) -> PlanetocentricPoint:
    """Convert body-centered Cartesian metres to planetocentric coordinates."""
    _require_position_unit(position)
    radius = position.magnitude
    if radius == 0.0:
        raise ConfigurationError("planetocentric coordinates are undefined at the origin")
    p = math.hypot(position.x, position.y)
    latitude = math.atan2(position.z, p)
    longitude = 0.0 if p == 0.0 else math.atan2(position.y, position.x)
    if longitude_convention is LongitudeConvention.EAST_360 and longitude < 0.0:
        longitude += 2.0 * math.pi
    return PlanetocentricPoint(
        latitude, longitude, radius, ellipsoid.identifier, longitude_convention
    )


def _require_ellipsoid(point_ellipsoid_id: str, ellipsoid: ReferenceEllipsoid) -> None:
    if point_ellipsoid_id != ellipsoid.identifier:
        raise ConfigurationError(
            f"coordinate ellipsoid {point_ellipsoid_id!r} does not match "
            f"{ellipsoid.identifier!r}"
        )


def _require_position_unit(position: Vector3) -> None:
    if position.unit != "m":
        raise ConfigurationError("coordinate conversion requires Cartesian positions in metres")
