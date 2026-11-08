"""Unit-tagged Cartesian vector primitives.

Components are expressed in one caller-declared unit. This module does not
convert units or attach an origin/reference frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from selene_prime.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class Vector3:
    """Three finite components sharing the declared unit."""

    x: float
    y: float
    z: float
    unit: str

    def __post_init__(self) -> None:
        components = (self.x, self.y, self.z)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in components
        ):
            raise ConfigurationError("vector components must be finite numbers")
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ConfigurationError("vector unit must be a nonempty string")

    def _require_same_unit(self, other: Vector3) -> None:
        if self.unit != other.unit:
            raise ConfigurationError(f"vector units differ: {self.unit!r} and {other.unit!r}")

    def __add__(self, other: Vector3) -> Vector3:
        self._require_same_unit(other)
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z, self.unit)

    def __sub__(self, other: Vector3) -> Vector3:
        self._require_same_unit(other)
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z, self.unit)

    def dot(self, other: Vector3) -> float:
        """Return the scalar component dot product; caller tracks squared units."""
        self._require_same_unit(other)
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        """Return the cross product with squared component units."""
        self._require_same_unit(other)
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
            "1" if self.unit == "1" else f"({self.unit})^2",
        )

    @property
    def magnitude(self) -> float:
        """Return Euclidean magnitude in ``unit``."""
        return math.hypot(self.x, self.y, self.z)

    def normalized(self) -> Vector3:
        """Return a unit direction with unit label ``1``; zero vectors are invalid."""
        magnitude = self.magnitude
        if magnitude == 0.0:
            raise ConfigurationError("zero vector has no defined direction")
        return Vector3(self.x / magnitude, self.y / magnitude, self.z / magnitude, "1")
