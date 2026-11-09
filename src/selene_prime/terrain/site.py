"""Station Cartesian positions derived from explicitly spherical DEM products."""
from __future__ import annotations

from dataclasses import dataclass
import math

from selene_prime.errors import TerrainGridError
from selene_prime.geometry.vectors import Vector3
from selene_prime.terrain.grid import TerrainGrid


@dataclass(frozen=True, slots=True)
class TerrainSitePosition:
    """Cartesian station vector retained in the DEM product's native frame label."""
    latitude_planetocentric_deg: float
    longitude_east_deg: float
    product_id: str
    native_frame_label: str
    position_km: Vector3


def station_position_from_spherical_grid(
    grid: TerrainGrid, latitude_planetocentric_deg: float, longitude_east_deg: float,
) -> TerrainSitePosition:
    """Convert a supported DEM site to a radial body-centered Cartesian vector.

    The function accepts only a product whose three declared reference axes
    equal its reference radius. It preserves the exact product frame label and
    does not claim that this label maps to a SPICE frame name. Product-specific
    frame/datum conversion must be sourced and validated by the caller.
    """
    axes = grid.reference_axes_m
    if axes is None or any(not math.isclose(axis, grid.reference_radius_m, rel_tol=0.0, abs_tol=1e-6)
                           for axis in axes):
        raise TerrainGridError("site conversion requires declared spherical reference axes")
    if grid.geometry.latitude_type != "planetocentric":
        raise TerrainGridError("site conversion requires planetocentric DEM latitude")
    radius_m = grid.surface_radius_m(latitude_planetocentric_deg, longitude_east_deg)
    lat, lon = math.radians(latitude_planetocentric_deg), math.radians(longitude_east_deg)
    radius_km = radius_m / 1000.0
    position = Vector3(radius_km * math.cos(lat) * math.cos(lon),
                       radius_km * math.cos(lat) * math.sin(lon),
                       radius_km * math.sin(lat), "km")
    return TerrainSitePosition(latitude_planetocentric_deg, longitude_east_deg,
                               grid.product_id, grid.native_frame, position)
