"""Mocked state-chain tests for topocentric iterated light-time geometry."""
from __future__ import annotations

import math

import pytest

from selene_prime.apparent import ApparentPositionService
from selene_prime.errors import EphemerisQueryError
from selene_prime.geometry.rotations import Rotation3
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels.session import AberrationCorrection, StateQueryResult


class MovingBodies:
    def __init__(self) -> None:
        self.queries: list[tuple[str, float, AberrationCorrection]] = []

    def frame_rotation(self, from_frame: str, to_frame: str, et: float) -> Rotation3:
        assert (from_frame, to_frame, et) == ("IAU_MOON", "J2000", 0.0)
        return Rotation3.identity()

    def validate_state_query(self, target: str, observer: str, et: float, frame: str,
                             correction: AberrationCorrection) -> StateQueryResult:
        assert observer == "SOLAR SYSTEM BARYCENTER"
        assert frame == "J2000"
        self.queries.append((target, et, correction))
        if target == "MOON":
            state = (100.0 + 10.0 * et, 0.0, 0.0, 10.0, 0.0, 0.0)
        elif target == "SUN":
            state = (300_000.0 + 100.0 * et, 0.0, 0.0, 100.0, 0.0, 0.0)
        else:
            raise RuntimeError("unexpected target")
        return StateQueryResult(target, observer, frame, et, correction, state, 0.0, ())


def test_station_barycentric_position_and_iterated_emission_time() -> None:
    api = MovingBodies()
    result = ApparentPositionService(api).position(
        "SUN", 0.0, Vector3(1.0, 0.0, 0.0, "km"), "IAU_MOON", target_radius_km=6_950.0,
    )
    expected_distance = 299_899.0 / (1.0 + 100.0 / 299_792.458)
    assert result.position_km.x == pytest.approx(expected_distance, abs=1e-5)
    assert result.light_time_seconds == pytest.approx(expected_distance / 299_792.458, abs=1e-9)
    assert result.emission_et_tdb_seconds == pytest.approx(-result.light_time_seconds)
    assert result.angular_radius_rad == pytest.approx(math.asin(6_950.0 / expected_distance))
    assert result.iterations >= 2
    assert all(query[2] is AberrationCorrection.NONE for query in api.queries)


def test_wrong_units_and_nonconvergent_solver_fail_closed() -> None:
    api = MovingBodies()
    service = ApparentPositionService(api)
    with pytest.raises(EphemerisQueryError, match="km"):
        service.position("SUN", 0, Vector3(1, 0, 0, "m"), "IAU_MOON")
    with pytest.raises(EphemerisQueryError, match="did not converge"):
        service.position("SUN", 0, Vector3(1, 0, 0, "km"), "IAU_MOON", max_iterations=1)


def test_reject_invalid_radius_and_target_radius_larger_than_range() -> None:
    service = ApparentPositionService(MovingBodies())
    with pytest.raises(EphemerisQueryError, match="target radius"):
        service.position("SUN", 0, Vector3(1, 0, 0, "km"), "IAU_MOON", target_radius_km=400_000)
