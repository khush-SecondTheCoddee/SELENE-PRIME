"""Analytic overlap area for two coplanar circular disks."""

from __future__ import annotations

import math

from selene_prime.errors import ConfigurationError


def circle_overlap_area(radius_a: float, radius_b: float, separation: float) -> float:
    """Return intersection area in squared input units.

    The inputs must share one length or angular unit. Tangency has zero area;
    coincident and contained disks use the exact limiting area.
    """
    values = (radius_a, radius_b, separation)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        raise ConfigurationError("circle radii and separation must be finite numbers")
    if radius_a <= 0 or radius_b <= 0 or separation < 0:
        raise ConfigurationError("circle radii must be positive and separation nonnegative")
    if separation >= radius_a + radius_b:
        return 0.0
    if separation <= abs(radius_a - radius_b):
        return math.pi * min(radius_a, radius_b) ** 2

    d2 = separation * separation
    a2 = radius_a * radius_a
    b2 = radius_b * radius_b
    cosine_a = (d2 + a2 - b2) / (2.0 * separation * radius_a)
    cosine_b = (d2 + b2 - a2) / (2.0 * separation * radius_b)
    # Roundoff can move a mathematically valid cosine just outside [-1, 1].
    angle_a = math.acos(min(1.0, max(-1.0, cosine_a)))
    angle_b = math.acos(min(1.0, max(-1.0, cosine_b)))
    radicand = (-separation + radius_a + radius_b) * (separation + radius_a - radius_b)
    radicand *= (separation - radius_a + radius_b) * (separation + radius_a + radius_b)
    lens = 0.5 * math.sqrt(max(0.0, radicand))
    return a2 * angle_a + b2 * angle_b - lens


def occulted_fraction(target_radius: float, occultor_radius: float, separation: float) -> float:
    """Return fraction of the target disk area covered by an occulting disk."""
    fraction = circle_overlap_area(target_radius, occultor_radius, separation) / (
        math.pi * target_radius * target_radius
    )
    return min(1.0, max(0.0, fraction))
