"""Validated proper three-dimensional rotation matrices."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, cast

from selene_prime.errors import ConfigurationError
from selene_prime.geometry.vectors import Vector3

Matrix3 = tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]


def _determinant(matrix: Matrix3) -> float:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


@dataclass(frozen=True, slots=True)
class Rotation3:
    """A proper orthonormal matrix; frame names and epochs belong to callers.

    ``rows`` maps column vectors by left multiplication. The matrix must satisfy
    ``R.T @ R = I`` and ``det(R) = +1`` within ``tolerance``.
    """

    rows: Matrix3
    tolerance: float = 1e-12

    def __post_init__(self) -> None:
        try:
            rows: Any = tuple(tuple(row) for row in self.rows)
        except TypeError as exc:
            raise ConfigurationError("rotation rows must be a 3 by 3 numeric matrix") from exc
        if len(rows) != 3 or any(len(row) != 3 for row in rows):
            raise ConfigurationError("rotation rows must be a 3 by 3 numeric matrix")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for row in rows
            for value in row
        ):
            raise ConfigurationError("rotation matrix values must be finite numbers")
        if (
            isinstance(self.tolerance, bool)
            or not isinstance(self.tolerance, (int, float))
            or not math.isfinite(self.tolerance)
            or self.tolerance <= 0
            or self.tolerance >= 1.0
        ):
            raise ConfigurationError("rotation tolerance must be finite and between 0 and 1")
        matrix: Matrix3 = rows
        for i in range(3):
            for j in range(3):
                product = sum(matrix[k][i] * matrix[k][j] for k in range(3))
                expected = 1.0 if i == j else 0.0
                if abs(product - expected) > self.tolerance:
                    raise ConfigurationError("rotation matrix is not orthonormal within tolerance")
        if abs(_determinant(matrix) - 1.0) > self.tolerance:
            raise ConfigurationError("rotation matrix must have determinant +1")
        object.__setattr__(self, "rows", matrix)

    @classmethod
    def identity(cls) -> Rotation3:
        """Return the identity rotation."""
        return cls(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))

    def apply(self, vector: Vector3) -> Vector3:
        """Rotate vector components while preserving their unit label."""
        values = (vector.x, vector.y, vector.z)
        x, y, z = (
            sum(row[index] * values[index] for index in range(3))
            for row in self.rows
        )
        return Vector3(x, y, z, vector.unit)

    def transpose(self) -> Rotation3:
        """Return the inverse rotation, equal to the matrix transpose."""
        inverse = cast(
            Matrix3,
            tuple(tuple(self.rows[j][i] for j in range(3)) for i in range(3)),
        )
        return Rotation3(inverse, tolerance=self.tolerance)
