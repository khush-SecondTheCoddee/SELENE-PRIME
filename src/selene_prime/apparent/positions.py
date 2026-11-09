"""Topocentric geometric light-time positions using SPICE state queries."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol

from selene_prime.errors import EphemerisQueryError
from selene_prime.geometry.rotations import Rotation3
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels.session import AberrationCorrection, StateQueryResult


class EphemerisSession(Protocol):
    """Minimal query interface implemented by :class:`KernelSession`."""
    def validate_state_query(self, target: str, observer: str, et: float, frame: str,
                             correction: AberrationCorrection) -> StateQueryResult: ...
    def frame_rotation(self, from_frame: str, to_frame: str, et: float) -> Rotation3: ...


@dataclass(frozen=True, slots=True)
class ApparentPosition:
    """Station-relative target position at reception epoch, with LT applied."""
    target: str
    observer_body: str
    frame: str
    reception_et_tdb_seconds: float
    emission_et_tdb_seconds: float
    light_time_seconds: float
    position_km: Vector3
    angular_radius_rad: float | None
    iterations: int
    correction: str = "LT (iterated light time; no stellar aberration)"

    @property
    def distance_km(self) -> float:
        return self.position_km.magnitude

    @property
    def direction(self) -> Vector3:
        return self.position_km.normalized()


class ApparentPositionService:
    """Solve geometric light time for a body-fixed lunar surface observer.

    Inputs are ET seconds past J2000 TDB and a site vector in the named lunar
    body-fixed frame, expressed in km from the lunar center. The station
    barycentric reception position includes the Moon's SPICE barycentric state
    and the rotated site vector. Stellar aberration is deliberately omitted and
    clearly identified; it can be added only with a separately validated model.
    """
    def __init__(self, session: EphemerisSession, *, moon_target: str = "MOON",
                 barycenter: str = "SOLAR SYSTEM BARYCENTER", inertial_frame: str = "J2000") -> None:
        self._session = session
        self._moon = moon_target
        self._barycenter = barycenter
        self._inertial = inertial_frame

    def position(self, target: str, reception_et: float, station_fixed_km: Vector3,
                 body_fixed_frame: str, *, target_radius_km: float | None = None,
                 time_tolerance_s: float = 1e-9, max_iterations: int = 20) -> ApparentPosition:
        """Return a finite-distance apparent position using iterated one-way LT."""
        if not target.strip() or target == self._moon:
            raise EphemerisQueryError("target must be a named body other than the observer Moon")
        if not math.isfinite(reception_et):
            raise EphemerisQueryError("reception ET must be finite TDB seconds past J2000")
        if station_fixed_km.unit != "km":
            raise EphemerisQueryError("station vector must use km")
        if target_radius_km is not None and (not math.isfinite(target_radius_km) or target_radius_km <= 0):
            raise EphemerisQueryError("target radius must be finite positive km")
        if not math.isfinite(time_tolerance_s) or time_tolerance_s <= 0:
            raise EphemerisQueryError("light-time tolerance must be finite and positive")
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1:
            raise EphemerisQueryError("max_iterations must be a positive integer")
        if not body_fixed_frame.strip():
            raise EphemerisQueryError("body-fixed station frame must be explicitly named")
        rotation = self._session.frame_rotation(body_fixed_frame, self._inertial, reception_et)
        site_inertial = rotation.apply(station_fixed_km)
        moon = self._state(self._moon, reception_et)
        observer = (moon[0] + site_inertial.x, moon[1] + site_inertial.y,
                    moon[2] + site_inertial.z)
        emission_et = reception_et
        light_time = 0.0
        for iteration in range(1, max_iterations + 1):
            target_state = self._state(target, emission_et)
            vector = (target_state[0] - observer[0], target_state[1] - observer[1],
                      target_state[2] - observer[2])
            updated = math.sqrt(sum(component * component for component in vector)) / 299_792.458
            next_emission = reception_et - updated
            if abs(next_emission - emission_et) <= time_tolerance_s:
                emission_et, light_time = next_emission, updated
                break
            emission_et, light_time = next_emission, updated
        else:
            raise EphemerisQueryError(
                f"light-time iteration for {target!r} did not converge in {max_iterations} iterations"
            )
        target_state = self._state(target, emission_et)
        vector = (target_state[0] - observer[0], target_state[1] - observer[1],
                  target_state[2] - observer[2])
        distance = math.sqrt(sum(component * component for component in vector))
        if distance <= 0 or not math.isfinite(distance):
            raise EphemerisQueryError("computed target-station distance is invalid")
        if target_radius_km is not None and target_radius_km >= distance:
            raise EphemerisQueryError("target radius must be smaller than observer-target distance")
        angular_radius = None if target_radius_km is None else math.asin(target_radius_km / distance)
        return ApparentPosition(
            target, self._moon, self._inertial, reception_et, emission_et, light_time,
            Vector3(*vector, "km"), angular_radius, iteration,
        )

    def _state(self, target: str, et: float) -> tuple[float, float, float, float, float, float]:
        result = self._session.validate_state_query(
            target, self._barycenter, et, self._inertial, AberrationCorrection.NONE
        )
        return result.state_km_km_s
