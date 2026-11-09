"""Resolution-aware terrain horizons on an explicitly spherical datum.

Supports planetocentric regular grids only. Bearings are clockwise from north;
returned horizon angles are radians. Ellipsoidal/polar products are rejected.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import math
from threading import RLock

from selene_prime.errors import TerrainGridError
from selene_prime.terrain.grid import TerrainGrid


@dataclass(frozen=True, slots=True)
class HorizonConfig:
    """Ray controls; step fraction is relative to the smaller local DEM cell."""
    max_range_m: float
    step_fraction: float = 0.5
    max_samples: int = 2_000_000

    def __post_init__(self) -> None:
        if not math.isfinite(self.max_range_m) or self.max_range_m <= 0:
            raise TerrainGridError("maximum horizon range must be finite and positive")
        if not math.isfinite(self.step_fraction) or not 0 < self.step_fraction <= 0.5:
            raise TerrainGridError("step_fraction must be in (0, 0.5] pixel")
        if isinstance(self.max_samples, bool) or not isinstance(self.max_samples, int) or self.max_samples < 2:
            raise TerrainGridError("max_samples must be an integer of at least two")


@dataclass(frozen=True, slots=True)
class HorizonResult:
    """Maximum apparent terrain elevation by azimuth and sampling diagnostics."""
    azimuth_rad: float
    elevation_rad: float
    range_at_maximum_m: float
    samples: int
    maximum_step_m: float
    grid_product_id: str
    reference_radius_m: float


class TerrainHorizonEngine:
    """Compute spherical line-of-sight horizons with a bounded thread-safe cache.

    Rays follow great-circle bearings on the reference sphere. DEM elevations
    are added radially and projected into the observer tangent plane. Sampling
    is at most half the smaller local pixel width by default. This controls
    raster-scale misses but is not a subpixel terrain guarantee.
    """
    def __init__(self, cache_size: int = 256) -> None:
        if isinstance(cache_size, bool) or not isinstance(cache_size, int) or cache_size < 0:
            raise TerrainGridError("cache_size must be a nonnegative integer")
        self._cache_size = cache_size
        self._cache: OrderedDict[tuple[object, ...], tuple[TerrainGrid, HorizonResult]] = OrderedDict()
        # Retain the grid so Python cannot recycle its id while this key exists.
        self._lock = RLock()

    def horizon(self, grid: TerrainGrid, latitude_deg: float, longitude_deg: float,
                azimuth_rad: float, config: HorizonConfig) -> HorizonResult:
        """Return horizon elevation for a site and north-clockwise azimuth."""
        if grid.geometry.latitude_type != "planetocentric":
            raise TerrainGridError("horizon engine requires planetocentric DEM latitude")
        axes = grid.reference_axes_m
        if axes is None or any(not math.isclose(axis, grid.reference_radius_m, rel_tol=0.0, abs_tol=1e-6)
                               for axis in axes):
            raise TerrainGridError(
                "spherical horizon engine requires declared reference axes equal to reference_radius_m"
            )
        if not math.isfinite(latitude_deg) or not -90 < latitude_deg < 90:
            raise TerrainGridError("station latitude must be finite and strictly between poles")
        if not math.isfinite(longitude_deg) or not math.isfinite(azimuth_rad):
            raise TerrainGridError("station longitude and azimuth must be finite")
        if config.max_range_m > math.pi * grid.reference_radius_m:
            raise TerrainGridError("maximum range cannot exceed half the reference-sphere circumference")
        azimuth = azimuth_rad % (2.0 * math.pi)
        key = (id(grid), latitude_deg, longitude_deg % 360.0, azimuth, config)
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None:
                self._cache.move_to_end(key)
                return entry[1]
        result = self._trace(grid, latitude_deg, longitude_deg, azimuth, config)
        if self._cache_size:
            with self._lock:
                self._cache[key] = (grid, result)
                self._cache.move_to_end(key)
                while len(self._cache) > self._cache_size:
                    self._cache.popitem(last=False)
        return result

    def clear_cache(self) -> None:
        """Discard cached profiles, for example after replacing mutable data."""
        with self._lock:
            self._cache.clear()

    @staticmethod
    def _trace(grid: TerrainGrid, lat0_deg: float, lon0_deg: float,
               azimuth: float, config: HorizonConfig) -> HorizonResult:
        radius = grid.reference_radius_m
        lat0, lon0 = math.radians(lat0_deg), math.radians(lon0_deg)
        station_radius = radius + grid.elevation_m(lat0_deg, lon0_deg)
        up = (math.cos(lat0) * math.cos(lon0), math.cos(lat0) * math.sin(lon0), math.sin(lat0))
        east = (-math.sin(lon0), math.cos(lon0), 0.0)
        north = (-math.sin(lat0) * math.cos(lon0), -math.sin(lat0) * math.sin(lon0), math.cos(lat0))
        angular_pixel = math.radians(1.0 / grid.geometry.pixels_per_degree)
        max_angle, max_range, range_m, count, maximum_step = -math.pi / 2, 0.0, 0.0, 0, 0.0
        origin = (station_radius * up[0], station_radius * up[1], station_radius * up[2])
        # Estimate the one-sided local DEM slope as range approaches zero. A
        # zero baseline would incorrectly erase a downhill local horizon.
        probe = min(0.01, radius * angular_pixel * max(1e-6, abs(math.cos(lat0))) * 1e-3)
        probe_delta = probe / radius
        probe_lat_sin = (math.sin(lat0) * math.cos(probe_delta)
                         + math.cos(lat0) * math.sin(probe_delta) * math.cos(azimuth))
        probe_lat = math.asin(max(-1.0, min(1.0, probe_lat_sin)))
        probe_lon = lon0 + math.atan2(
            math.sin(azimuth) * math.sin(probe_delta) * math.cos(lat0),
            math.cos(probe_delta) - math.sin(lat0) * math.sin(probe_lat),
        )
        probe_height = grid.elevation_m(math.degrees(probe_lat), math.degrees(probe_lon))
        probe_radius = radius + probe_height
        probe_point = (probe_radius * math.cos(probe_lat) * math.cos(probe_lon),
                       probe_radius * math.cos(probe_lat) * math.sin(probe_lon),
                       probe_radius * math.sin(probe_lat))
        pdx, pdy, pdz = (probe_point[0] - origin[0], probe_point[1] - origin[1],
                         probe_point[2] - origin[2])
        pvertical = pdx * up[0] + pdy * up[1] + pdz * up[2]
        peast = pdx * east[0] + pdy * east[1] + pdz * east[2]
        pnorth = pdx * north[0] + pdy * north[1] + pdz * north[2]
        max_angle = math.atan2(pvertical, math.hypot(peast, pnorth))
        max_range, count = probe, 1
        while range_m < config.max_range_m:
            delta = range_m / radius
            sin_lat = math.sin(lat0) * math.cos(delta) + math.cos(lat0) * math.sin(delta) * math.cos(azimuth)
            lat = math.asin(max(-1.0, min(1.0, sin_lat)))
            lon = lon0 + math.atan2(
                math.sin(azimuth) * math.sin(delta) * math.cos(lat0),
                math.cos(delta) - math.sin(lat0) * math.sin(lat),
            )
            if range_m > 0:
                height = grid.elevation_m(math.degrees(lat), math.degrees(lon))
                terrain_radius = radius + height
                point = (terrain_radius * math.cos(lat) * math.cos(lon),
                         terrain_radius * math.cos(lat) * math.sin(lon), terrain_radius * math.sin(lat))
                dx, dy, dz = point[0] - origin[0], point[1] - origin[1], point[2] - origin[2]
                vertical = dx * up[0] + dy * up[1] + dz * up[2]
                horizontal_e = dx * east[0] + dy * east[1] + dz * east[2]
                horizontal_n = dx * north[0] + dy * north[1] + dz * north[2]
                angle = math.atan2(vertical, math.hypot(horizontal_e, horizontal_n))
                if angle > max_angle:
                    max_angle, max_range = angle, range_m
            count += 1
            if count > config.max_samples:
                raise TerrainGridError("horizon ray exceeded max_samples; increase step or reduce range")
            cell = radius * angular_pixel * max(1e-6, abs(math.cos(lat)))
            step = min(config.step_fraction * cell, config.max_range_m - range_m)
            maximum_step = max(maximum_step, step)
            if step <= 0:
                break
            range_m += step
        return HorizonResult(azimuth, max_angle, max_range, count, maximum_step,
                             grid.product_id, radius)
