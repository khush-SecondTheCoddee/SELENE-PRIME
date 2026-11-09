"""Finite solar disk quadrature and independent obstruction masks."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

from selene_prime.errors import ConfigurationError

HorizonFunction = Callable[[float], float]


@dataclass(frozen=True, slots=True)
class SolarDiskConfig:
    """Explicit radiometry and numerical choices; no default physical constants."""
    irradiance_w_m2_at_1au: float
    distance_au: float
    limb_darkening_u: float
    limb_darkening_source: str
    passband: str
    subdivisions: int = 256

    def __post_init__(self) -> None:
        if not math.isfinite(self.irradiance_w_m2_at_1au) or self.irradiance_w_m2_at_1au <= 0:
            raise ConfigurationError("1-AU solar irradiance must be finite and positive")
        if not math.isfinite(self.distance_au) or self.distance_au <= 0:
            raise ConfigurationError("Sun distance must be finite and positive AU")
        if not math.isfinite(self.limb_darkening_u) or not 0 <= self.limb_darkening_u <= 1:
            raise ConfigurationError("linear limb-darkening coefficient must be in [0, 1]")
        if not self.limb_darkening_source.strip() or not self.passband.strip():
            raise ConfigurationError("limb-darkening source and passband must be documented")
        if isinstance(self.subdivisions, bool) or not isinstance(self.subdivisions, int) or self.subdivisions < 8:
            raise ConfigurationError("disk quadrature subdivisions must be an integer >= 8")


@dataclass(frozen=True, slots=True)
class SolarDiskResult:
    """Disk area visibility and limb-weighted flux visibility for one geometry."""
    visible_fraction: float
    irradiance_visible_fraction: float
    earth_occluded_fraction: float
    terrain_occluded_fraction: float
    combined_occluded_fraction: float
    direct_normal_w_m2: float
    direct_horizontal_w_m2: float
    solar_angular_radius_rad: float
    sample_count: int
    subdivisions: int
    passband: str
    limb_darkening_source: str
    irradiance_w_m2_at_1au: float
    distance_au: float
    atmosphere_model: str


def integrate_solar_disk(
    *, solar_angular_radius_rad: float, solar_azimuth_rad: float,
    solar_elevation_rad: float, config: SolarDiskConfig,
    earth_angular_radius_rad: float | None = None,
    earth_azimuth_rad: float | None = None,
    earth_elevation_rad: float | None = None,
    horizon_elevation: HorizonFunction | None = None,
    atmosphere_model: str = "opaque geometric Earth disk; atmosphere ignored",
) -> SolarDiskResult:
    """Integrate a tangent-plane solar disk with Earth and terrain masks.

    Angular disk locations use gnomonic coordinates centered on the solar
    direction. Earth occultation is a circular opaque disk in the same plane;
    terrain visibility tests every quadrature ray against a caller-supplied
    azimuth horizon. Masks are combined per sample before integration, so
    overlapping obstructions are not double-counted. ``visible_fraction`` and
    obstruction fractions are solid-angle fractions of the apparent solar disk;
    ``irradiance_visible_fraction`` separately includes limb darkening and
    projected irradiance weights.
    """
    if not math.isfinite(solar_angular_radius_rad) or not 0 < solar_angular_radius_rad < math.pi / 2:
        raise ConfigurationError("solar angular radius must be in (0, pi/2)")
    if not math.isfinite(solar_azimuth_rad) or not math.isfinite(solar_elevation_rad):
        raise ConfigurationError("solar azimuth and elevation must be finite")
    if not -math.pi / 2 <= solar_elevation_rad <= math.pi / 2:
        raise ConfigurationError("solar elevation must be in [-pi/2, pi/2]")
    if earth_angular_radius_rad is None and (earth_azimuth_rad is not None or earth_elevation_rad is not None):
        raise ConfigurationError("Earth radius and apparent direction must be provided together")
    if earth_angular_radius_rad is not None:
        if earth_azimuth_rad is None or earth_elevation_rad is None:
            raise ConfigurationError("Earth radius and apparent direction must be provided together")
        if not math.isfinite(earth_angular_radius_rad) or not 0 < earth_angular_radius_rad < math.pi / 2:
            raise ConfigurationError("Earth angular radius must be in (0, pi/2)")
        if not math.isfinite(earth_azimuth_rad) or not math.isfinite(earth_elevation_rad):
            raise ConfigurationError("Earth azimuth and elevation must be finite")
        if not -math.pi / 2 <= earth_elevation_rad <= math.pi / 2:
            raise ConfigurationError("Earth elevation must be in [-pi/2, pi/2]")
    if horizon_elevation is not None and not callable(horizon_elevation):
        raise ConfigurationError("horizon_elevation must be callable")
    if not atmosphere_model.strip():
        raise ConfigurationError("atmosphere_model must be explicitly identified")

    center, east_basis, vertical_basis = _enu_basis(solar_azimuth_rad, solar_elevation_rad)
    earth_direction = None
    if earth_angular_radius_rad is not None:
        assert earth_azimuth_rad is not None and earth_elevation_rad is not None
        earth_direction = _enu_direction(earth_azimuth_rad, earth_elevation_rad)

    solar_radius_tan = math.tan(solar_angular_radius_rad)
    n = config.subdivisions
    step = 2.0 * solar_radius_tan / n
    total_weight = visible_weight = horizontal_weight = 0.0
    total_solid_angle = visible_solid_angle = 0.0
    earth_solid_angle = terrain_solid_angle = combined_solid_angle = 0.0
    samples = 0
    for row in range(n):
        y = -solar_radius_tan + (row + 0.5) * step
        for column in range(n):
            x = -solar_radius_tan + (column + 0.5) * step
            r2 = x * x + y * y
            if r2 > solar_radius_tan * solar_radius_tan:
                continue
            samples += 1
            radius = math.sqrt(r2)
            theta = math.atan(radius)
            mu = math.sqrt(max(0.0, 1.0 - (math.sin(theta) / math.sin(solar_angular_radius_rad)) ** 2))
            intensity = 1.0 - config.limb_darkening_u * (1.0 - mu)
            # dOmega and projected-area factors for gnomonic tangent-plane coordinates.
            weight = intensity / ((1.0 + r2) ** 2)
            solid_angle_weight = 1.0 / ((1.0 + r2) ** 1.5)
            total_weight += weight
            total_solid_angle += solid_angle_weight
            ray = _normalize((center[0] + x * east_basis[0] + y * vertical_basis[0],
                              center[1] + x * east_basis[1] + y * vertical_basis[1],
                              center[2] + x * east_basis[2] + y * vertical_basis[2]))
            earth_blocked = (earth_direction is not None and earth_angular_radius_rad is not None
                             and _dot(ray, earth_direction) >= math.cos(earth_angular_radius_rad))
            if earth_blocked:
                earth_solid_angle += solid_angle_weight
            ray_azimuth = math.atan2(ray[0], ray[1]) % (2.0 * math.pi)
            ray_elevation = math.asin(max(-1.0, min(1.0, ray[2])))
            terrain_blocked = False
            if horizon_elevation is not None:
                horizon = horizon_elevation(ray_azimuth)
                if not math.isfinite(horizon) or not -math.pi / 2 <= horizon <= math.pi / 2:
                    raise ConfigurationError("horizon callback must return finite elevation in [-pi/2, pi/2]")
                terrain_blocked = ray_elevation <= horizon
                if terrain_blocked:
                    terrain_solid_angle += solid_angle_weight
            if earth_blocked or terrain_blocked:
                combined_solid_angle += solid_angle_weight
            else:
                visible_solid_angle += solid_angle_weight
                visible_weight += weight
                horizontal_weight += weight * max(0.0, math.sin(ray_elevation))

    if total_weight <= 0 or total_solid_angle <= 0 or samples == 0:
        raise ConfigurationError("solar disk quadrature produced no in-disk samples")
    irradiance = config.irradiance_w_m2_at_1au / (config.distance_au ** 2)
    return SolarDiskResult(
        visible_solid_angle / total_solid_angle, visible_weight / total_weight,
        earth_solid_angle / total_solid_angle, terrain_solid_angle / total_solid_angle,
        combined_solid_angle / total_solid_angle, irradiance * visible_weight / total_weight,
        irradiance * horizontal_weight / total_weight, solar_angular_radius_rad, samples, n,
        config.passband, config.limb_darkening_source, config.irradiance_w_m2_at_1au,
        config.distance_au, atmosphere_model,
    )


def _enu_direction(azimuth: float, elevation: float) -> tuple[float, float, float]:
    ce = math.cos(elevation)
    return ce * math.sin(azimuth), ce * math.cos(azimuth), math.sin(elevation)


def _enu_basis(azimuth: float, elevation: float) -> tuple[
    tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]
]:
    center = _enu_direction(azimuth, elevation)
    east = math.cos(azimuth), -math.sin(azimuth), 0.0
    vertical = (-math.sin(elevation) * math.sin(azimuth),
                -math.sin(elevation) * math.cos(azimuth), math.cos(elevation))
    return center, east, vertical


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(_dot(v, v))
    return v[0] / norm, v[1] / norm, v[2] / norm
