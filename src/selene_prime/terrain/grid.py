"""Validated regular geographic elevation grids and NoData-aware interpolation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol, Sequence

from selene_prime.errors import TerrainGridError


class ElevationSource(Protocol):
    """Read-only row-major elevation source; absent values are returned as ``None``."""

    @property
    def rows(self) -> int: ...

    @property
    def columns(self) -> int: ...

    def elevation(self, row: int, column: int) -> float | None: ...


@dataclass(frozen=True, slots=True)
class SequenceElevationSource:
    """Small in-memory source intended for deterministic synthetic fixtures."""

    values: tuple[tuple[float | None, ...], ...]

    def __post_init__(self) -> None:
        if not self.values or not self.values[0]:
            raise TerrainGridError("elevation raster must have at least one row and column")
        width = len(self.values[0])
        if any(len(row) != width for row in self.values):
            raise TerrainGridError("elevation raster rows must have uniform length")
        for row in self.values:
            for value in row:
                if value is not None and (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                ):
                    raise TerrainGridError("elevation samples must be finite or NoData")

    @property
    def rows(self) -> int:
        return len(self.values)

    @property
    def columns(self) -> int:
        return len(self.values[0])

    def elevation(self, row: int, column: int) -> float | None:
        return self.values[row][column]


@dataclass(frozen=True, slots=True)
class GridGeometry:
    """PDS simple-cylindrical geographic registration in pixel-center coordinates.

    Projection offsets follow PDS3: integral line/sample coordinates identify
    pixel centers; the stored offsets are zero-based relative to the projection
    origin. Latitude grows north while raster row grows down. The PDS longitude
    equation uses decreasing sample index for increasing east longitude.
    """

    rows: int
    columns: int
    line_projection_offset: float
    sample_projection_offset: float
    center_latitude_deg: float
    center_longitude_deg: float
    pixels_per_degree: float
    global_longitude: bool = False
    latitude_type: str = "planetocentric"
    longitude_direction: str = "east"

    def __post_init__(self) -> None:
        if (
            isinstance(self.rows, bool)
            or not isinstance(self.rows, int)
            or isinstance(self.columns, bool)
            or not isinstance(self.columns, int)
            or self.rows <= 0
            or self.columns <= 0
        ):
            raise TerrainGridError("grid dimensions must be positive integers")
        numeric = (
            self.line_projection_offset,
            self.sample_projection_offset,
            self.center_latitude_deg,
            self.center_longitude_deg,
            self.pixels_per_degree,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in numeric
        ):
            raise TerrainGridError("grid projection parameters must be finite numbers")
        if not 0 < self.pixels_per_degree:
            raise TerrainGridError("pixels per degree must be positive")
        if not -90 <= self.center_latitude_deg <= 90:
            raise TerrainGridError("projection center latitude must be in [-90, 90]")
        if self.latitude_type not in {"planetocentric", "planetographic"}:
            raise TerrainGridError(
                "latitude type must be explicitly planetocentric or planetographic"
            )
        if self.longitude_direction != "east":
            raise TerrainGridError("only east-positive longitude is supported")
        if self.global_longitude and not math.isclose(
            self.columns / self.pixels_per_degree, 360.0, rel_tol=0.0, abs_tol=1e-8
        ):
            raise TerrainGridError("global longitude grid width must span exactly 360 degrees")

    @classmethod
    def from_coordinate_axes(
        cls,
        latitudes_deg: Sequence[float],
        longitudes_deg: Sequence[float],
        *,
        global_longitude: bool = False,
        latitude_type: str = "planetocentric",
    ) -> GridGeometry:
        """Construct from pixel-center axes, rejecting empty/nonuniform axes."""
        lat_step = _uniform_step(latitudes_deg, "latitude")
        lon_step = _uniform_step(longitudes_deg, "longitude")
        if not math.isclose(abs(lat_step), abs(lon_step), rel_tol=1e-10, abs_tol=1e-12):
            raise TerrainGridError("latitude and longitude axes must have equal angular spacing")
        if lat_step >= 0 or lon_step >= 0:
            raise TerrainGridError("axes must be ordered north-to-south and east-to-west")
        resolution = 1.0 / abs(lat_step)
        # Convert pixel-center axes to PDS's zero-based projection offsets.
        line_offset = latitudes_deg[0] * resolution
        sample_offset = longitudes_deg[0] * resolution
        return cls(
            len(latitudes_deg),
            len(longitudes_deg),
            line_offset,
            sample_offset,
            0.0,
            0.0,
            resolution,
            global_longitude,
            latitude_type,
        )

    def fractional_index(self, latitude_deg: float, longitude_deg: float) -> tuple[float, float]:
        """Map geodetic coordinates to fractional zero-based raster row/column."""
        if (
            isinstance(latitude_deg, bool)
            or isinstance(longitude_deg, bool)
            or not isinstance(latitude_deg, (int, float))
            or not isinstance(longitude_deg, (int, float))
            or not math.isfinite(latitude_deg)
            or not math.isfinite(longitude_deg)
        ):
            raise TerrainGridError("latitude and longitude must be finite numbers")
        if not -90.0 <= latitude_deg <= 90.0:
            raise TerrainGridError("latitude must be in [-90, 90] degrees")
        if abs(latitude_deg) == 90.0:
            raise TerrainGridError(
                "longitude is singular at cylindrical poles; polar products are unsupported"
            )
        longitude_delta = (longitude_deg - self.center_longitude_deg + 180.0) % 360.0 - 180.0
        row = self.line_projection_offset - (
            latitude_deg - self.center_latitude_deg
        ) * self.pixels_per_degree
        column = self.sample_projection_offset - longitude_delta * self.pixels_per_degree
        if self.global_longitude:
            column %= self.columns
        else:
            if not -1e-10 <= column <= self.columns - 1 + 1e-10:
                raise TerrainGridError("coordinate lies outside regional grid pixel-center bounds")
        if not -1e-10 <= row <= self.rows - 1 + 1e-10:
            raise TerrainGridError("latitude lies outside grid pixel-center bounds")
        return min(max(row, 0.0), self.rows - 1.0), column


def _uniform_step(values: Sequence[float], name: str) -> float:
    if len(values) < 2 or any(not math.isfinite(value) for value in values):
        raise TerrainGridError(f"{name} axis must contain at least two finite coordinates")
    step = values[1] - values[0]
    if step == 0.0:
        raise TerrainGridError(f"{name} coordinates must be strictly monotonic")
    tolerance = max(1e-10, abs(step) * 1e-8)
    if any(
        abs((values[index] - values[index - 1]) - step) > tolerance
        for index in range(2, len(values))
    ):
        raise TerrainGridError(f"{name} coordinates are nonuniform")
    return step


@dataclass(frozen=True, slots=True)
class TerrainGrid:
    """Elevation raster with named reference radius and declared sample units."""

    source: ElevationSource
    geometry: GridGeometry
    reference_radius_m: float
    product_id: str
    elevation_unit: str = "m"
    native_frame: str = "unspecified"
    datum_name: str = "unspecified"
    reference_axes_m: tuple[float, float, float] | None = None

    def __post_init__(self) -> None:
        if self.source.rows != self.geometry.rows or self.source.columns != self.geometry.columns:
            raise TerrainGridError("raster dimensions do not match grid geometry")
        if (
            isinstance(self.reference_radius_m, bool)
            or not isinstance(self.reference_radius_m, (int, float))
            or not math.isfinite(self.reference_radius_m)
            or self.reference_radius_m <= 0
        ):
            raise TerrainGridError("reference radius must be finite and positive metres")
        if not self.product_id.strip():
            raise TerrainGridError("grid product identifier must be provided")
        if self.elevation_unit != "m":
            raise TerrainGridError("terrain elevations must be converted to metres")
        if not self.native_frame.strip() or not self.datum_name.strip():
            raise TerrainGridError("native frame and datum name must be explicit")
        if self.reference_axes_m is not None and (
            len(self.reference_axes_m) != 3
            or any(not math.isfinite(axis) or axis <= 0 for axis in self.reference_axes_m)
        ):
            raise TerrainGridError("reference axes must be three positive finite metre values")

    def elevation_m(self, latitude_deg: float, longitude_deg: float) -> float:
        """Bilinearly interpolate height above the product reference radius.

        A query touching any NoData corner is rejected. Regional images do not
        extrapolate; global cylindrical images wrap in longitude only.
        """
        row, column = self.geometry.fractional_index(latitude_deg, longitude_deg)
        r0 = math.floor(row)
        r1 = min(r0 + 1, self.geometry.rows - 1)
        c0 = math.floor(column)
        c1 = (c0 + 1) % self.geometry.columns if self.geometry.global_longitude else min(
            c0 + 1, self.geometry.columns - 1
        )
        fy = row - r0
        fx = column - c0
        weighted_samples = (
            (self.source.elevation(r0, c0), (1 - fx) * (1 - fy)),
            (self.source.elevation(r0, c1), fx * (1 - fy)),
            (self.source.elevation(r1, c0), (1 - fx) * fy),
            (self.source.elevation(r1, c1), fx * fy),
        )
        if any(value is None and weight != 0.0 for value, weight in weighted_samples):
            raise TerrainGridError("bilinear interpolation footprint intersects NoData")
        return sum(float(value) * weight for value, weight in weighted_samples if value is not None)

    def surface_radius_m(self, latitude_deg: float, longitude_deg: float) -> float:
        """Return product reference radius plus interpolated height."""
        return self.reference_radius_m + self.elevation_m(latitude_deg, longitude_deg)
