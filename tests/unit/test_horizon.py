"""Analytic synthetic terrain checks for the spherical horizon engine."""
from __future__ import annotations

import math

import pytest

from selene_prime.errors import TerrainGridError
from selene_prime.terrain import (
    GridGeometry, HorizonConfig, SequenceElevationSource, TerrainGrid,
    TerrainHorizonEngine,
)


def grid_for(values: tuple[tuple[float, ...], ...], pixels_per_degree: float = 10.0) -> TerrainGrid:
    half = (len(values) - 1) / (2 * pixels_per_degree)
    coordinates = tuple(half - index / pixels_per_degree for index in range(len(values)))
    geometry = GridGeometry.from_coordinate_axes(coordinates, coordinates)
    return TerrainGrid(SequenceElevationSource(values), geometry, 1000.0, "analytic-sphere")


def test_flat_spherical_surface_has_zero_horizon_baseline() -> None:
    values = tuple(tuple(0.0 for _ in range(101)) for _ in range(101))
    grid = grid_for(values)
    result = TerrainHorizonEngine().horizon(grid, 0, 0, math.pi / 2, HorizonConfig(20.0))
    assert result.elevation_rad == 0.0
    assert result.samples > 2
    assert result.maximum_step_m <= 0.5 * 1000 * math.radians(0.1) + 1e-12


def test_single_eastward_ridge_is_detected_with_curvature() -> None:
    values = [[0.0] * 101 for _ in range(101)]
    values[50][47] = 20.0  # Raster columns run westward; col 47 is east of center.
    grid = grid_for(tuple(tuple(row) for row in values))
    result = TerrainHorizonEngine().horizon(grid, 0, 0, math.pi / 2, HorizonConfig(20.0))
    assert result.elevation_rad > math.radians(50)
    assert 0 < result.range_at_maximum_m < 10


def test_horizon_cache_clear_and_azimuth_normalization() -> None:
    grid = grid_for(tuple(tuple(0.0 for _ in range(101)) for _ in range(101)))
    engine = TerrainHorizonEngine()
    config = HorizonConfig(5.0)
    a = engine.horizon(grid, 0, 0, 0, config)
    b = engine.horizon(grid, 0, 0, 2 * math.pi, config)
    assert a is b
    engine.clear_cache()
    assert engine.horizon(grid, 0, 0, 0, config) is not a


def test_regional_edge_and_pole_failures_are_not_hidden() -> None:
    grid = grid_for(tuple(tuple(0.0 for _ in range(101)) for _ in range(101)))
    with pytest.raises(TerrainGridError, match="outside"):
        TerrainHorizonEngine().horizon(grid, 0, 5.1, 0, HorizonConfig(5.0))
    with pytest.raises(TerrainGridError, match="poles"):
        TerrainHorizonEngine().horizon(grid, 90, 0, 0, HorizonConfig(5.0))
