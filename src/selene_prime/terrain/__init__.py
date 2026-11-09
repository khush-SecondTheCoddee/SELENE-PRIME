"""Terrain product ingestion and validated elevation grids."""

from selene_prime.terrain.grid import (
    GridGeometry,
    SequenceElevationSource,
    TerrainGrid,
)
from selene_prime.terrain.horizon import HorizonConfig, HorizonResult, TerrainHorizonEngine
from selene_prime.terrain.site import TerrainSitePosition, station_position_from_spherical_grid
from selene_prime.terrain.pds3_lola import LolaGdrMetadata, LolaGdrProduct, TerrainProvenance

__all__ = [
    "GridGeometry",
    "HorizonConfig",
    "HorizonResult",
    "LolaGdrMetadata",
    "LolaGdrProduct",
    "SequenceElevationSource",
    "TerrainGrid",
    "TerrainHorizonEngine",
    "TerrainSitePosition",
    "station_position_from_spherical_grid",
    "TerrainProvenance",
]
