"""Tests against analytic geometry identities, separate from implementation paths."""

import json
import math
from pathlib import Path

import pytest

from selene_prime.errors import ConfigurationError
from selene_prime.geometry import (
    GeodeticPoint,
    LongitudeConvention,
    PlanetocentricPoint,
    ReferenceEllipsoid,
    Rotation3,
    Vector3,
    cartesian_to_geodetic,
    cartesian_to_planetocentric,
    circle_overlap_area,
    geodetic_to_cartesian,
    occulted_fraction,
    planetocentric_to_cartesian,
)

REFERENCE = json.loads(
    (Path(__file__).parents[1] / "references" / "geometry_reference_cases.json").read_text()
)
ELLIPSOID = ReferenceEllipsoid(
    "analytic-ellipsoid-test", 2.0, 1.0, "analytic test fixture axes (metres)"
)


def test_vector_operations_preserve_units_and_norm() -> None:
    first = Vector3(1.0, 2.0, 2.0, "m")
    second = Vector3(2.0, 0.0, 1.0, "m")
    assert first.dot(second) == 4.0
    assert first.cross(second) == Vector3(2.0, 3.0, -4.0, "(m)^2")
    assert first.normalized().magnitude == pytest.approx(1.0)
    assert (first + second).unit == "m"
    with pytest.raises(ConfigurationError):
        first + Vector3(1.0, 1.0, 1.0, "km")
    with pytest.raises(ConfigurationError):
        Vector3(0.0, 0.0, 0.0, "m").normalized()


def test_rotation_maps_basis_vector_and_inverse_recovers_input() -> None:
    quarter_turn = Rotation3(
        ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    )
    vector = Vector3(1.0, 0.0, 0.0, "1")
    rotated = quarter_turn.apply(vector)
    assert rotated.x == pytest.approx(0.0)
    assert rotated.y == pytest.approx(1.0)
    assert rotated.z == pytest.approx(0.0)
    recovered = quarter_turn.transpose().apply(rotated)
    assert recovered.x == pytest.approx(vector.x)
    assert recovered.y == pytest.approx(vector.y)
    assert recovered.z == pytest.approx(vector.z)
    assert rotated.magnitude == pytest.approx(vector.magnitude)


@pytest.mark.parametrize(
    "rows",
    [
        ((1.0, 0.0), (0.0, 1.0)),
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
        ((1.0, 0.1, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ],
)
def test_rotation_rejects_non_proper_matrices(rows: tuple[tuple[float, ...], ...]) -> None:
    with pytest.raises(ConfigurationError):
        Rotation3(rows)  # type: ignore[arg-type]


def test_circle_overlap_reference_cases() -> None:
    reference = REFERENCE["circle_equal_unit_radii_unit_separation"]
    area = circle_overlap_area(1.0, 1.0, 1.0)
    assert area == pytest.approx(reference["overlap_area"], abs=2e-15)
    assert occulted_fraction(1.0, 1.0, 1.0) == pytest.approx(
        reference["fraction_of_either_disk"], abs=2e-15
    )
    assert circle_overlap_area(1.0, 2.0, 0.0) == pytest.approx(math.pi)
    assert circle_overlap_area(1.0, 1.0, 2.0) == 0.0
    assert circle_overlap_area(1.0, 1.0, 0.0) == pytest.approx(math.pi)


def test_circle_geometry_rejects_invalid_physical_ranges() -> None:
    for arguments in ((0.0, 1.0, 0.0), (1.0, -1.0, 0.0), (1.0, 1.0, -0.1)):
        with pytest.raises(ConfigurationError):
            circle_overlap_area(*arguments)


def test_geodetic_surface_point_matches_independent_analytic_reference() -> None:
    reference = REFERENCE["oblate_ellipsoid_a2_b1_geodetic_latitude_45_surface"]
    point = GeodeticPoint(
        math.pi / 4,
        0.0,
        0.0,
        ELLIPSOID.identifier,
        LongitudeConvention.EAST_180,
    )
    position = geodetic_to_cartesian(point, ELLIPSOID)
    assert position.x == pytest.approx(reference["x_m"], abs=1e-14)
    assert position.y == reference["y_m"]
    assert position.z == pytest.approx(reference["z_m"], abs=1e-14)

    # At this analytic surface point, geocentric latitude is atan2(z, x)=atan(1/4).
    centric = cartesian_to_planetocentric(position, ELLIPSOID, LongitudeConvention.EAST_180)
    assert centric.latitude_rad == pytest.approx(
        reference["planetocentric_latitude_rad"], abs=1e-15
    )
    assert centric.latitude_rad != pytest.approx(point.latitude_rad)


def test_geodetic_and_planetocentric_round_trips() -> None:
    geodetic = GeodeticPoint(
        math.radians(-32.0),
        math.radians(120.0),
        0.25,
        ELLIPSOID.identifier,
        LongitudeConvention.EAST_180,
    )
    cartesian = geodetic_to_cartesian(geodetic, ELLIPSOID)
    recovered = cartesian_to_geodetic(cartesian, ELLIPSOID, LongitudeConvention.EAST_180)
    assert recovered.latitude_rad == pytest.approx(geodetic.latitude_rad, abs=2e-14)
    assert recovered.longitude_rad == pytest.approx(geodetic.longitude_rad, abs=2e-14)
    assert recovered.height_m == pytest.approx(geodetic.height_m, abs=2e-14)

    centric = PlanetocentricPoint(
        math.radians(20.0),
        math.radians(-150.0),
        3.0,
        ELLIPSOID.identifier,
        LongitudeConvention.EAST_180,
    )
    converted = planetocentric_to_cartesian(centric)
    recovered_centric = cartesian_to_planetocentric(
        converted, ELLIPSOID, LongitudeConvention.EAST_180
    )
    assert recovered_centric.latitude_rad == pytest.approx(centric.latitude_rad)
    assert recovered_centric.longitude_rad == pytest.approx(centric.longitude_rad)
    assert recovered_centric.radius_m == pytest.approx(centric.radius_m)


def test_coordinate_poles_longitude_domains_and_invalid_inputs() -> None:
    north_pole = cartesian_to_geodetic(
        Vector3(0.0, 0.0, 1.5, "m"), ELLIPSOID, LongitudeConvention.EAST_360
    )
    assert north_pole.latitude_rad == pytest.approx(math.pi / 2)
    assert north_pole.longitude_rad == 0.0
    assert north_pole.height_m == pytest.approx(0.5)

    wrapped = cartesian_to_geodetic(
        Vector3(0.0, -2.0, 0.0, "m"), ELLIPSOID, LongitudeConvention.EAST_360
    )
    assert wrapped.longitude_rad == pytest.approx(3 * math.pi / 2)

    with pytest.raises(ConfigurationError):
        GeodeticPoint(
            math.radians(91), 0.0, 0.0, ELLIPSOID.identifier, LongitudeConvention.EAST_180
        )
    with pytest.raises(ConfigurationError):
        GeodeticPoint(0.0, 2 * math.pi, 0.0, ELLIPSOID.identifier, LongitudeConvention.EAST_180)
    with pytest.raises(ConfigurationError):
        geodetic_to_cartesian(
            GeodeticPoint(0.0, 0.0, 0.0, "different", LongitudeConvention.EAST_180),
            ELLIPSOID,
        )
    with pytest.raises(ConfigurationError):
        cartesian_to_geodetic(Vector3(0.0, 0.0, 0.0, "m"), ELLIPSOID, LongitudeConvention.EAST_180)
    with pytest.raises(ConfigurationError):
        cartesian_to_planetocentric(
            Vector3(1.0, 2.0, 3.0, "km"), ELLIPSOID, LongitudeConvention.EAST_180
        )


@pytest.mark.parametrize("latitude_deg", [-89.0, -80.0, -45.0, -5.0, 5.0, 45.0, 80.0, 89.0])
def test_geodetic_round_trip_over_latitude_range(latitude_deg: float) -> None:
    point = GeodeticPoint(
        math.radians(latitude_deg),
        math.radians(275.0),
        0.1,
        ELLIPSOID.identifier,
        LongitudeConvention.EAST_360,
    )
    restored = cartesian_to_geodetic(
        geodetic_to_cartesian(point, ELLIPSOID),
        ELLIPSOID,
        LongitudeConvention.EAST_360,
    )
    assert restored.latitude_rad == pytest.approx(point.latitude_rad, abs=2e-14)
    assert restored.longitude_rad == pytest.approx(point.longitude_rad, abs=2e-14)
    assert restored.height_m == pytest.approx(point.height_m, abs=2e-14)
