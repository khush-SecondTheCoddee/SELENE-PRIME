"""Independent mathematical primitives for later scientific subsystems."""

from selene_prime.geometry.circles import circle_overlap_area, occulted_fraction
from selene_prime.geometry.ellipsoid import (
    GeodeticPoint,
    LongitudeConvention,
    PlanetocentricPoint,
    ReferenceEllipsoid,
    cartesian_to_geodetic,
    cartesian_to_planetocentric,
    geodetic_to_cartesian,
    planetocentric_to_cartesian,
)
from selene_prime.geometry.rotations import Rotation3
from selene_prime.geometry.vectors import Vector3

__all__ = [
    "GeodeticPoint",
    "LongitudeConvention",
    "PlanetocentricPoint",
    "ReferenceEllipsoid",
    "Rotation3",
    "Vector3",
    "cartesian_to_geodetic",
    "cartesian_to_planetocentric",
    "circle_overlap_area",
    "geodetic_to_cartesian",
    "occulted_fraction",
    "planetocentric_to_cartesian",
]
