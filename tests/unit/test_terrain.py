"""Synthetic geometric and PDS3 parser tests; no real LOLA product is included."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path

import pytest

from selene_prime.errors import TerrainGridError, TerrainProductError
from selene_prime.terrain import (
    GridGeometry,
    LolaGdrProduct,
    SequenceElevationSource,
    TerrainGrid,
)


def write_synthetic_lola_product(
    tmp_path: Path,
    values: tuple[tuple[int, ...], ...],
    *,
    sample_type: str = "LSB_INTEGER",
) -> tuple[Path, Path]:
    rows, columns = len(values), len(values[0])
    image_path = tmp_path / "mini.IMG"
    with image_path.open("wb") as stream:
        for row in values:
            endian = "<" if sample_type == "LSB_INTEGER" else ">"
            stream.write(struct.pack(endian + "h" * columns, *row))
    label_path = tmp_path / "mini.LBL"
    label_path.write_text(
        f'''PDS_VERSION_ID = "PDS3"
DATA_SET_ID = "LRO-L-LOLA-4-GDR-V1.0"
PRODUCT_ID = "SYNTHETIC_MINI"
PRODUCT_VERSION_ID = "TEST"
OBJECT = UNCOMPRESSED_FILE
 FILE_NAME = "mini.IMG"
 RECORD_TYPE = FIXED_LENGTH
 FILE_RECORDS = {rows}
 RECORD_BYTES = {columns * 2}
 ^IMAGE = "mini.IMG"
 OBJECT = IMAGE
  NAME = HEIGHT
  LINES = {rows}
  LINE_SAMPLES = {columns}
  SAMPLE_TYPE = {sample_type}
  SAMPLE_BITS = 16
  UNIT = METER
  SCALING_FACTOR = 0.5
  OFFSET = 1737400.
  MISSING_CONSTANT = -32768
 END_OBJECT = IMAGE
END_OBJECT = UNCOMPRESSED_FILE
OBJECT = IMAGE_MAP_PROJECTION
 MAP_PROJECTION_TYPE = "SIMPLE CYLINDRICAL"
 MAP_RESOLUTION = 1 <pix/deg>
 A_AXIS_RADIUS = 1737.4 <km>
 B_AXIS_RADIUS = 1737.4 <km>
 C_AXIS_RADIUS = 1737.4 <km>
 POSITIVE_LONGITUDE_DIRECTION = "EAST"
 CENTER_LATITUDE = 0 <deg>
 CENTER_LONGITUDE = 0 <deg>
 LINE_FIRST_PIXEL = 1
 LINE_LAST_PIXEL = {rows}
 SAMPLE_FIRST_PIXEL = 1
 SAMPLE_LAST_PIXEL = {columns}
 MAP_PROJECTION_ROTATION = 0.0
 MAXIMUM_LATITUDE = 2.0 <deg>
 MINIMUM_LATITUDE = -2.0 <deg>
 WESTERNMOST_LONGITUDE = 0 <deg>
 EASTERNMOST_LONGITUDE = 4 <deg>
 LINE_PROJECTION_OFFSET = 1.5 <pix>
 SAMPLE_PROJECTION_OFFSET = 3.5 <pix>
 COORDINATE_SYSTEM_TYPE = "BODY-FIXED ROTATING"
 COORDINATE_SYSTEM_NAME = "MEAN EARTH/POLAR AXIS OF DE421"
END_OBJECT = IMAGE_MAP_PROJECTION
END
''',
        encoding="ascii",
    )
    return label_path, image_path


SAMPLES = (
    (0, 4, 8, 12),
    (20, 24, 28, 32),
    (40, 44, 48, 52),
    (60, 64, 68, 72),
)


def test_pds3_lola_sample_decoding_scaling_registration_and_provenance(tmp_path: Path) -> None:
    label, image = write_synthetic_lola_product(tmp_path, SAMPLES)
    expected_label = hashlib.sha256(label.read_bytes()).hexdigest()
    expected_image = hashlib.sha256(image.read_bytes()).hexdigest()
    with LolaGdrProduct.open(
        label,
        expected_label_sha256=expected_label,
        expected_image_sha256=expected_image,
    ) as product:
        assert product.provenance.product_id == "SYNTHETIC_MINI"
        assert product.provenance.label_sha256_verified
        assert product.provenance.image_sha256_verified
        assert product.grid.reference_radius_m == 1_737_400.0
        assert product.metadata.file_format == "PDS3 detached IMG"
        assert product.metadata.sample_type == "LSB_INTEGER"
        assert product.metadata.sample_bits == 16
        assert product.metadata.byte_order == "little"
        assert product.metadata.scaling_factor == 0.5
        assert product.metadata.pixel_registration == "pixel center"
        assert product.grid.elevation_m(1.5, 3.5) == 0.0
        assert product.grid.elevation_m(1.0, 3.0) == pytest.approx(6.0)
        assert product.grid.surface_radius_m(1.0, 3.0) == pytest.approx(1_737_406.0)
        assert product.grid.native_frame == "MEAN EARTH/POLAR AXIS OF DE421"
        assert product.grid.reference_axes_m == (1_737_400.0,) * 3
    with pytest.raises(TerrainProductError, match="closed"):
        product.grid.elevation_m(1.0, 3.0)


def test_msb_signed_sample_encoding_is_decoded(tmp_path: Path) -> None:
    label, _ = write_synthetic_lola_product(tmp_path, SAMPLES, sample_type="MSB_INTEGER")
    with LolaGdrProduct.open(label) as product:
        assert product.metadata.byte_order == "big"
        assert product.grid.elevation_m(1.5, 3.5) == 0.0
        assert product.grid.elevation_m(1.0, 3.0) == pytest.approx(6.0)


def test_pds_label_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    label, _ = write_synthetic_lola_product(tmp_path, SAMPLES)
    with pytest.raises(TerrainProductError, match="trusted expected digest"):
        LolaGdrProduct.open(label, expected_label_sha256="0" * 64)


def test_image_size_mismatch_is_rejected(tmp_path: Path) -> None:
    label, image = write_synthetic_lola_product(tmp_path, SAMPLES)
    image.write_bytes(image.read_bytes()[:-1])
    with pytest.raises(TerrainProductError, match="image size mismatch"):
        LolaGdrProduct.open(label)


def test_unsupported_encoding_is_rejected(tmp_path: Path) -> None:
    label, _ = write_synthetic_lola_product(tmp_path, SAMPLES)
    text = label.read_text().replace("SAMPLE_TYPE = LSB_INTEGER", "SAMPLE_TYPE = PC_REAL")
    label.write_text(text)
    with pytest.raises(TerrainProductError, match="unsupported LOLA sample encoding"):
        LolaGdrProduct.open(label)


def test_global_longitude_wraps_and_pole_singularity_is_explicit() -> None:
    geometry = GridGeometry(
        rows=2,
        columns=360,
        line_projection_offset=0.5,
        sample_projection_offset=1.5,
        center_latitude_deg=0,
        center_longitude_deg=0,
        pixels_per_degree=1,
        global_longitude=True,
    )
    assert geometry.fractional_index(0.5, 360.0) == pytest.approx((0.0, 1.5))
    assert geometry.fractional_index(0.5, -360.0) == pytest.approx((0.0, 1.5))
    with pytest.raises(TerrainGridError, match="poles"):
        geometry.fractional_index(90, 0)
    with pytest.raises(TerrainGridError, match="finite"):
        geometry.fractional_index(float("nan"), 0)


def test_regional_grid_crossing_antimeridian_maps_both_longitude_conventions() -> None:
    geometry = GridGeometry(
        rows=2,
        columns=4,
        line_projection_offset=0.5,
        sample_projection_offset=1.5,
        center_latitude_deg=0,
        center_longitude_deg=0,
        pixels_per_degree=1,
    )
    assert geometry.fractional_index(0, 359.5)[1] == pytest.approx(2.0)
    assert geometry.fractional_index(0, -0.5)[1] == pytest.approx(2.0)
    assert geometry.fractional_index(0, 0.5)[1] == pytest.approx(1.0)
    with pytest.raises(TerrainGridError, match="outside"):
        geometry.fractional_index(0, 357)


def test_regional_edges_nodata_and_exact_sample_behavior() -> None:
    geometry = GridGeometry(2, 2, 0.5, 0.5, 0, 0, 1)
    grid = TerrainGrid(
        SequenceElevationSource(((10.0, None), (30.0, 40.0))), geometry, 1000.0, "fixture"
    )
    assert grid.elevation_m(0.5, 0.5) == 10.0
    with pytest.raises(TerrainGridError, match="NoData"):
        grid.elevation_m(0.25, 0.25)
    assert grid.elevation_m(-0.5, -0.5) == 40.0
    with pytest.raises(TerrainGridError, match="outside"):
        grid.elevation_m(-0.51, 0)


def test_grid_axes_reject_nonuniform_or_wrongly_ordered_coordinates() -> None:
    with pytest.raises(TerrainGridError, match="nonuniform"):
        GridGeometry.from_coordinate_axes([2.0, 1.0, -0.2], [3.0, 2.0, 1.0])
    with pytest.raises(TerrainGridError, match="ordered"):
        GridGeometry.from_coordinate_axes([0.0, 1.0], [1.0, 0.0])


def test_spherical_grid_site_cartesian_position_has_explicit_frame() -> None:
    from selene_prime.terrain import station_position_from_spherical_grid

    geometry = GridGeometry(2, 2, 0.5, 0.5, 0, 0, 1)
    grid = TerrainGrid(SequenceElevationSource(((0.0, 0.0), (0.0, 0.0))), geometry,
                       1000.0, "site-fixture", native_frame="SYNTHETIC_BODY_FIXED",
                       reference_axes_m=(1000.0, 1000.0, 1000.0))
    position = station_position_from_spherical_grid(grid, 0.0, 0.0)
    assert position.position_km.x == pytest.approx(1.0)
    assert position.position_km.y == pytest.approx(0.0, abs=1e-15)
    assert position.native_frame_label == "SYNTHETIC_BODY_FIXED"
    assert position.product_id == "site-fixture"


def test_site_cartesian_rejects_unknown_or_non_spherical_datum() -> None:
    from selene_prime.terrain import station_position_from_spherical_grid

    geometry = GridGeometry(2, 2, 0.5, 0.5, 0, 0, 1)
    grid = TerrainGrid(SequenceElevationSource(((0.0, 0.0), (0.0, 0.0))), geometry,
                       1000.0, "unknown", native_frame="UNKNOWN",
                       reference_axes_m=(1000.0, 1000.0, 999.0))
    with pytest.raises(TerrainGridError, match="spherical reference axes"):
        station_position_from_spherical_grid(grid, 0.0, 0.0)
