"""Execute small analytic/synthetic checks and write auditable JSON results."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

from selene_prime.geometry.circles import circle_overlap_area
from selene_prime.radiometry import SolarDiskConfig, integrate_solar_disk
from selene_prime.terrain import GridGeometry, SequenceElevationSource, TerrainGrid
from selene_prime.validation import BenchmarkCase, execute_benchmark


def main() -> None:
    alpha = 0.01
    uniform = SolarDiskConfig(100.0, 1.0, 0.0, "analytic uniform-disk case", "synthetic", 128)
    cases = (
        (BenchmarkCase("circle_partial_overlap", "circle_overlap", "analytic",
                       "Closed-form two-circle lens area; fixed reference from tests/references/geometry_reference_cases.json",
                       "r1=r2=1, separation=1", 1.2283696986087567, "unit^2", 2e-15, 0.0),
         lambda: circle_overlap_area(1.0, 1.0, 1.0)),
        (BenchmarkCase("solar_half_plane", "solar_visibility", "analytic",
                       "Reflection symmetry of a uniform circular disk across a straight horizon",
                       "angular radius=0.01 rad; center elevation=0; horizon=0; u=0", 0.5,
                       "fraction", 1e-12, 0.0),
         lambda: integrate_solar_disk(solar_angular_radius_rad=alpha, solar_azimuth_rad=0.2,
                                      solar_elevation_rad=0.0, config=uniform,
                                      horizon_elevation=lambda _az: 0.0).visible_fraction),
        (BenchmarkCase("dem_bilinear_center", "dem_interpolation", "synthetic",
                       "Independent four-corner arithmetic mean at the center of a 2x2 pixel grid",
                       "values=((0,2),(4,6)) m; query at central pixel-coordinate midpoint",
                       3.0, "m", 1e-14, 0.0),
         _bilinear_center),
    )
    results = [execute_benchmark(case, evaluator) for case, evaluator in cases]
    report = {
        "schema_version": 1,
        "designation": "analytic_and_synthetic_only",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "software": {"python": sys.version.split()[0], "platform": platform.platform()},
        "results": [
            {"case_id": result.case.case_id, "category": result.case.category,
             "designation": result.case.designation, "reference_source": result.case.reference_source,
             "inputs": result.case.inputs, "expected": result.case.expected, "actual": result.actual,
             "unit": result.case.unit, "absolute_error": result.absolute_error,
             "relative_error": result.relative_error,
             "absolute_tolerance": result.case.absolute_tolerance,
             "relative_tolerance": result.case.relative_tolerance, "status": result.status}
            for result in results
        ],
    }
    output = Path("reports/ANALYTIC_SYNTHETIC_BENCHMARKS.json")
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if any(result.status != "pass" for result in results):
        raise SystemExit("one or more analytic/synthetic benchmark cases failed")
    print(f"Wrote {len(results)} passing analytic/synthetic cases to {output}")


def _bilinear_center() -> float:
    geometry = GridGeometry(rows=2, columns=2, line_projection_offset=0.5,
                            sample_projection_offset=0.5, center_latitude_deg=0,
                            center_longitude_deg=0, pixels_per_degree=1)
    grid = TerrainGrid(SequenceElevationSource(((0.0, 2.0), (4.0, 6.0))), geometry,
                       1000.0, "synthetic-2x2", reference_axes_m=(1000.0, 1000.0, 1000.0))
    # Pixel-center coordinate axes are +0.5 and -0.5 degrees.
    return grid.elevation_m(0.0, 0.0)


if __name__ == "__main__":
    main()
