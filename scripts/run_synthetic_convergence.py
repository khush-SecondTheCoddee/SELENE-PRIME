"""Record successive disk-quadrature and terrain-step refinements on fixtures."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path

from selene_prime.radiometry import SolarDiskConfig, integrate_solar_disk
from selene_prime.terrain import (GridGeometry, HorizonConfig, SequenceElevationSource,
                                  TerrainGrid, TerrainHorizonEngine)


def planar_overlap_fraction(r: float, s: float, d: float) -> float:
    """Independent closed-form two-circle overlap normalized by solar area."""
    if d >= r + s:
        return 0.0
    if d <= abs(r - s):
        return min(r, s) ** 2 / r**2
    a = math.acos((d*d + r*r - s*s) / (2*d*r))
    b = math.acos((d*d + s*s - r*r) / (2*d*s))
    lens = 0.5 * math.sqrt((-d+r+s)*(d+r-s)*(d-r+s)*(d+r+s))
    return (r*r*a + s*s*b - lens) / (math.pi*r*r)


def make_ridge_grid() -> TerrainGrid:
    n, resolution, radius = 101, 10.0, 1000.0
    half = (n - 1) / (2 * resolution)
    axis = tuple(half - i / resolution for i in range(n))
    values = [[0.0] * n for _ in range(n)]
    values[50][47] = 8.0
    geometry = GridGeometry.from_coordinate_axes(axis, axis)
    return TerrainGrid(SequenceElevationSource(tuple(tuple(row) for row in values)), geometry,
                       radius, "synthetic-ridge", reference_axes_m=(radius, radius, radius))


def main() -> None:
    alpha, earth_radius, separation = 0.01, 0.006, 0.008
    solar_elevation, solar_azimuth = 0.003, 0.4
    earth_azimuth = solar_azimuth + separation / math.cos(solar_elevation)
    grid = make_ridge_grid()
    horizon_engine = TerrainHorizonEngine(cache_size=0)
    rows: list[dict[str, object]] = []
    previous: dict[str, float] | None = None
    for n in (32, 64, 128, 256):
        config = SolarDiskConfig(1361.0, 1.0, 0.0,
                                 "uniform synthetic convergence fixture", "synthetic", n)
        common = dict(solar_angular_radius_rad=alpha, solar_azimuth_rad=solar_azimuth,
                      solar_elevation_rad=solar_elevation, config=config)
        earth_only = integrate_solar_disk(
            **common, earth_angular_radius_rad=earth_radius, earth_azimuth_rad=earth_azimuth,
            earth_elevation_rad=solar_elevation,
        )
        combined = integrate_solar_disk(
            **common, earth_angular_radius_rad=earth_radius, earth_azimuth_rad=earth_azimuth,
            earth_elevation_rad=solar_elevation, horizon_elevation=lambda _az: 0.0,
        )
        terrain_only = integrate_solar_disk(
            **common, horizon_elevation=lambda _az: 0.0,
        )
        horizon = horizon_engine.horizon(
            grid, 0.0, 0.0, math.pi / 2,
            HorizonConfig(20.0, step_fraction=0.5 * 32 / n),
        )
        current = {
            "direct_normal_w_m2": combined.direct_normal_w_m2,
            "irradiance_visible_fraction": combined.irradiance_visible_fraction,
            "direct_horizontal_w_m2": combined.direct_horizontal_w_m2,
            "terrain_visible_fraction": terrain_only.visible_fraction,
            "earth_only_visible_fraction": earth_only.visible_fraction,
            "earth_occulted_fraction": earth_only.earth_occluded_fraction,
            "combined_visible_fraction": combined.visible_fraction,
            "combined_occluded_fraction": combined.combined_occluded_fraction,
            "terrain_horizon_rad": horizon.elevation_rad,
        }
        diffs = None if previous is None else {key: abs(current[key] - previous[key]) for key in current}
        rows.append({"resolution": n, "disk_subdivisions": n,
                     "terrain_step_fraction_pixel": 0.5 * 32 / n,
                     "values": current, "absolute_difference_from_previous": diffs,
                     "disk_samples": combined.sample_count,
                     "horizon_samples": horizon.samples})
        previous = current
    report = {
        "schema_version": 1,
        "designation": "synthetic_refinement_study_not_mission_validation",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture": {"solar_radius_rad": alpha, "earth_radius_rad": earth_radius,
                    "center_separation_tangent_rad": separation,
                    "solar_elevation_rad": solar_elevation, "limb_darkening_u": 0.0,
                    "terrain": "101x101 spherical grid; one 8 m ridge three pixels east of station"},
        "independent_planar_circle_overlap_fraction": planar_overlap_fraction(alpha, earth_radius, separation),
        "tolerance_policy": "No pass/fail tolerance assigned; no project scientific error budget is selected.",
        "successive_refinements": rows,
    }
    path = Path("reports/SYNTHETIC_REFINEMENT_STUDY.json")
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} successive synthetic refinements to {path}")


if __name__ == "__main__":
    main()
