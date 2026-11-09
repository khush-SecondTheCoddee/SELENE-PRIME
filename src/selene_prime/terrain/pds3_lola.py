"""Scoped PDS3 LOLA GDR cylindrical IMG ingestion with integrity provenance."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import mmap
from pathlib import Path
import re
import struct
from typing import Any, Literal, cast

from selene_prime.errors import TerrainProductError
from selene_prime.terrain.grid import GridGeometry, TerrainGrid


@dataclass(frozen=True, slots=True)
class _LabelNode:
    name: str
    fields: dict[str, str]
    children: tuple[_LabelNode, ...]

    def objects(self, name: str) -> tuple[_LabelNode, ...]:
        matches: list[_LabelNode] = []
        for child in self.children:
            if child.name.upper() == name.upper():
                matches.append(child)
            matches.extend(child.objects(name))
        return tuple(matches)


@dataclass(frozen=True, slots=True)
class TerrainProvenance:
    label_path: str
    image_path: str
    label_sha256: str
    image_sha256: str
    product_id: str
    data_set_id: str
    product_version_id: str | None
    label_sha256_verified: bool
    image_sha256_verified: bool


@dataclass(frozen=True, slots=True)
class LolaGdrMetadata:
    """Decoded product properties retained from the label and storage layout."""

    file_format: str
    rows: int
    columns: int
    sample_type: str
    sample_bits: int
    byte_order: str
    elevation_unit: str
    scaling_factor: float
    reference_radius_m: float
    no_data_raw_values: tuple[float, ...]
    projection_type: str
    pixel_registration: str
    pixels_per_degree: float
    latitude_type: str
    longitude_direction: str
    native_frame: str
    reference_axes_m: tuple[float, float, float]


@dataclass(frozen=True, slots=True)
class _ImageLayout:
    rows: int
    columns: int
    sample_bytes: int
    sample_format: str
    byte_order: str
    scale: float
    no_data: frozenset[int | float]
    line_prefix_bytes: int
    line_suffix_bytes: int
    record_bytes: int
    data_offset: int
    reference_radius_m: float
    native_frame: str
    reference_axes_m: tuple[float, float, float]
    sample_type: str
    no_data_values: tuple[float, ...]
    projection_type: str
    metadata: LolaGdrMetadata


class _MappedImage:
    def __init__(self, path: Path, layout: _ImageLayout) -> None:
        self.path = path
        self.layout = layout
        try:
            self._stream = path.open("rb")
            self._map = mmap.mmap(self._stream.fileno(), length=0, access=mmap.ACCESS_READ)
            self._closed = False
        except (OSError, ValueError) as exc:
            if hasattr(self, "_stream"):
                self._stream.close()
            raise TerrainProductError(f"cannot map LOLA image file: {path}") from exc

    @property
    def rows(self) -> int:
        return self.layout.rows

    @property
    def columns(self) -> int:
        return self.layout.columns

    def elevation(self, row: int, column: int) -> float | None:
        if self._closed:
            raise TerrainProductError("LOLA product raster is closed")
        if not 0 <= row < self.rows or not 0 <= column < self.columns:
            raise TerrainProductError("raster source index is out of bounds")
        pixel_offset = (
            self.layout.data_offset
            + row * self.layout.record_bytes
            + self.layout.line_prefix_bytes
            + column * self.layout.sample_bytes
        )
        try:
            raw = struct.unpack_from(self.layout.sample_format, self._map, pixel_offset)[0]
        except (struct.error, ValueError) as exc:
            raise TerrainProductError(
                f"truncated or malformed sample at row={row}, column={column}"
            ) from exc
        if raw in self.layout.no_data or not math.isfinite(float(raw)):
            return None
        # LOLA GDR IMAGE=HEIGHT uses DN*SCALING_FACTOR; OFFSET is the
        # product reference radius, not an additive height offset.
        return float(raw) * self.layout.scale

    def close(self) -> None:
        if not self._closed:
            try:
                self._map.close()
            finally:
                self._stream.close()
                self._closed = True


class LolaGdrProduct:
    """Context-managed reader for PDS3 LOLA GDR signed integer cylindrical IMG.

    Only IMAGE products with a PDS3 GDR dataset ID, simple cylindrical
    projection, fixed pixel registration, east-positive longitude, and 16-bit
    LSB/MSB signed integer samples are supported in this first adapter.
    JPEG2000, polar stereographic, PDS4, and alternate floating encodings are
    explicitly unsupported. Raster access is memory-mapped and lazy.
    """

    def __init__(
        self,
        grid: TerrainGrid,
        provenance: TerrainProvenance,
        metadata: LolaGdrMetadata,
        source: _MappedImage,
    ) -> None:
        self.grid = grid
        self.provenance = provenance
        self.metadata = metadata
        self._source = source
        self._closed = False

    @classmethod
    def open(
        cls,
        label_path: str | Path,
        *,
        expected_label_sha256: str | None = None,
        expected_image_sha256: str | None = None,
    ) -> LolaGdrProduct:
        """Validate a detached label and open its referenced LOLA GDR IMG.

        Expected hashes, when supplied, are checked against an external trusted
        manifest. Calculated hashes alone identify bytes but do not authenticate
        an origin.
        """
        try:
            label_file = Path(label_path).resolve(strict=True)
            label_bytes = label_file.read_bytes()
            label_text = label_bytes.decode("ascii")
        except (OSError, RuntimeError, UnicodeDecodeError) as exc:
            raise TerrainProductError(f"cannot read ASCII PDS3 label: {label_path}") from exc
        label_digest = hashlib.sha256(label_bytes).hexdigest()
        _verify_expected_hash(expected_label_sha256, label_digest, "label")
        root = _parse_label(label_text)
        if _value(root.fields, "PDS_VERSION_ID") != "PDS3":
            raise TerrainProductError("label is not a PDS3 product")
        data_set_id = _value(root.fields, "DATA_SET_ID")
        if data_set_id != "LRO-L-LOLA-4-GDR-V1.0":
            raise TerrainProductError(f"unsupported PDS data set: {data_set_id!r}")
        product_id = _value(root.fields, "PRODUCT_ID")
        if not product_id:
            raise TerrainProductError("PDS product label lacks PRODUCT_ID")
        image_nodes = root.objects("IMAGE")
        projection_nodes = root.objects("IMAGE_MAP_PROJECTION")
        if len(image_nodes) != 1 or len(projection_nodes) != 1:
            raise TerrainProductError(
                "label must define exactly one IMAGE and one IMAGE_MAP_PROJECTION"
            )
        image_fields = image_nodes[0].fields
        projection_fields = projection_nodes[0].fields
        file_nodes = root.objects("UNCOMPRESSED_FILE")
        if len(file_nodes) != 1:
            raise TerrainProductError("label must declare exactly one UNCOMPRESSED_FILE object")
        image_name, image_record = _image_pointer(file_nodes[0].fields)
        try:
            image_file = (label_file.parent / image_name).resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise TerrainProductError(
                f"referenced image file is unavailable: {image_name}"
            ) from exc
        image_digest = _sha256_path(image_file)
        _verify_expected_hash(expected_image_sha256, image_digest, "image")
        layout, geometry = _build_layout(
            file_nodes[0].fields, image_fields, projection_fields, image_record
        )
        expected_size = layout.data_offset + layout.rows * layout.record_bytes
        try:
            actual_size = image_file.stat().st_size
        except OSError as exc:
            raise TerrainProductError(f"cannot inspect image product size: {image_file}") from exc
        if actual_size != expected_size:
            raise TerrainProductError(
                "image size mismatch: label layout requires "
                f"{expected_size} bytes, file has {actual_size}"
            )
        source = _MappedImage(image_file, layout)
        provenance = TerrainProvenance(
            str(label_file),
            str(image_file),
            label_digest,
            image_digest,
            product_id,
            data_set_id,
            _value(root.fields, "PRODUCT_VERSION_ID", required=False),
            expected_label_sha256 is not None,
            expected_image_sha256 is not None,
        )
        try:
            grid = TerrainGrid(
                source,
                geometry,
                layout.reference_radius_m,
                product_id,
                native_frame=layout.native_frame,
                datum_name=f"LOLA GDR reference sphere, radius {layout.reference_radius_m:g} m",
                reference_axes_m=layout.reference_axes_m,
            )
        except BaseException:
            source.close()
            raise
        return cls(grid, provenance, layout.metadata, source)

    def __enter__(self) -> LolaGdrProduct:
        if self._closed:
            raise TerrainProductError("cannot re-enter a closed LOLA product")
        return self

    def __exit__(
        self, exc_type: object, exc: BaseException | None, traceback: object
    ) -> Literal[False]:
        del exc_type, exc, traceback
        self.close()
        return False

    def close(self) -> None:
        if not self._closed:
            self._source.close()
            self._closed = True


def _build_layout(
    file_fields: dict[str, str],
    image: dict[str, str],
    projection: dict[str, str],
    image_record: int | None,
) -> tuple[_ImageLayout, GridGeometry]:
    try:
        rows = _integer(image, "LINES")
        columns = _integer(image, "LINE_SAMPLES")
        bits = _integer(image, "SAMPLE_BITS")
        sample_type = _required_value(image, "SAMPLE_TYPE").upper()
        if bits != 16 or sample_type not in {"LSB_INTEGER", "MSB_INTEGER"}:
            raise TerrainProductError(
                f"unsupported LOLA sample encoding: {sample_type} / {bits} bits; "
                "supported: 16-bit signed integer"
            )
        sample_bytes = bits // 8
        byte_order = "little" if sample_type == "LSB_INTEGER" else "big"
        sample_format = ("<" if byte_order == "little" else ">") + "h"
        scale = _number(image, "SCALING_FACTOR")
        if scale == 0:
            raise TerrainProductError("SCALING_FACTOR must be nonzero")
        units = _required_value(image, "UNIT").upper()
        if units not in {"METER", "METERS", "M"}:
            raise TerrainProductError(f"unsupported elevation unit: {units!r}")
        if _required_value(image, "NAME").upper() != "HEIGHT":
            raise TerrainProductError("only IMAGE objects named HEIGHT are supported")
        reference_radius_m = _number(image, "OFFSET")
        if reference_radius_m <= 0:
            raise TerrainProductError("LOLA HEIGHT OFFSET reference radius must be positive metres")
        record_bytes = _integer(file_fields, "RECORD_BYTES")
        prefix = _integer(image, "LINE_PREFIX_BYTES", required=False, default=0)
        suffix = _integer(image, "LINE_SUFFIX_BYTES", required=False, default=0)
        if record_bytes != columns * sample_bytes + prefix + suffix:
            raise TerrainProductError(
                "RECORD_BYTES disagrees with IMAGE dimensions and line padding"
            )
        pointer = 0 if image_record is None else (image_record - 1) * record_bytes
        checksum_fields = [
            image.get(name)
            for name in ("MISSING_CONSTANT", "MISSING", "INVALID_CONSTANT", "INVALID")
        ]
        no_data_values = tuple(
            _parse_number(value) for value in checksum_fields if value is not None
        )
        no_data = frozenset(no_data_values)
        projection_type = _required_value(projection, "MAP_PROJECTION_TYPE").upper()
        if projection_type != "SIMPLE CYLINDRICAL":
            raise TerrainProductError(f"unsupported map projection: {projection_type!r}")
        longitude_direction = _required_value(projection, "POSITIVE_LONGITUDE_DIRECTION").upper()
        if longitude_direction != "EAST":
            raise TerrainProductError("LOLA grid must declare east-positive longitude")
        lat_type_raw = _required_value(projection, "COORDINATE_SYSTEM_NAME").upper()
        if "PLANETOCENTRIC" in lat_type_raw or "MEAN EARTH" in lat_type_raw:
            latitude_type = "planetocentric"
        elif "PLANETOGRAPHIC" in lat_type_raw:
            latitude_type = "planetographic"
        else:
            raise TerrainProductError(f"unknown latitude/frame semantics: {lat_type_raw!r}")
        resolution = _number(projection, "MAP_RESOLUTION")
        _require_unit(projection, "MAP_RESOLUTION", {"PIX/DEG", "PIXEL/DEG", "PIXELS/DEG"})
        line_offset = _number(projection, "LINE_PROJECTION_OFFSET")
        sample_offset = _number(projection, "SAMPLE_PROJECTION_OFFSET")
        _require_unit(projection, "LINE_PROJECTION_OFFSET", {"PIX", "PIXEL", "PIXELS"})
        _require_unit(projection, "SAMPLE_PROJECTION_OFFSET", {"PIX", "PIXEL", "PIXELS"})
        center_lat = _number(projection, "CENTER_LATITUDE")
        center_lon = _number(projection, "CENTER_LONGITUDE")
        if _number(projection, "MAP_PROJECTION_ROTATION") != 0.0:
            raise TerrainProductError("rotated cylindrical raster grids are unsupported")
        coordinate_type = _required_value(projection, "COORDINATE_SYSTEM_TYPE").upper()
        if coordinate_type != "BODY-FIXED ROTATING":
            raise TerrainProductError(f"unsupported coordinate system type: {coordinate_type!r}")
        native_frame = _required_value(projection, "COORDINATE_SYSTEM_NAME")
        axes = cast(
            tuple[float, float, float],
            tuple(
                _length_m(projection, key)
                for key in ("A_AXIS_RADIUS", "B_AXIS_RADIUS", "C_AXIS_RADIUS")
            ),
        )
        west = _number(projection, "WESTERNMOST_LONGITUDE")
        east = _number(projection, "EASTERNMOST_LONGITUDE")
        min_lat = _number(projection, "MINIMUM_LATITUDE")
        max_lat = _number(projection, "MAXIMUM_LATITUDE")
        longitude_span = (east - west) % 360.0
        if math.isclose(longitude_span, 0.0, abs_tol=1e-8):
            longitude_span = 360.0
        if not math.isclose(max_lat - min_lat, rows / resolution, rel_tol=0.0, abs_tol=2e-6):
            raise TerrainProductError(
                "declared latitude bounds disagree with image dimensions/resolution"
            )
        if not math.isclose(longitude_span, columns / resolution, rel_tol=0.0, abs_tol=2e-6):
            raise TerrainProductError(
                "declared longitude bounds disagree with image dimensions/resolution"
            )
        global_longitude = math.isclose(longitude_span, 360.0, abs_tol=1e-8)
        geometry = GridGeometry(
            rows,
            columns,
            line_offset,
            sample_offset,
            center_lat,
            center_lon,
            resolution,
            global_longitude,
            latitude_type,
            longitude_direction.lower(),
        )
        if (
            _integer(projection, "LINE_FIRST_PIXEL") != 1
            or _integer(projection, "SAMPLE_FIRST_PIXEL") != 1
        ):
            raise TerrainProductError("nonstandard first-pixel registration is unsupported")
        if (
            _integer(projection, "LINE_LAST_PIXEL") != rows
            or _integer(projection, "SAMPLE_LAST_PIXEL") != columns
        ):
            raise TerrainProductError("projection pixel bounds disagree with IMAGE dimensions")
        if image_record is not None:
            raise TerrainProductError("record-addressed or attached image objects are unsupported")
        if _required_value(file_fields, "RECORD_TYPE").upper() != "FIXED_LENGTH":
            raise TerrainProductError("LOLA GDR IMG files must use fixed-length records")
        if _integer(file_fields, "FILE_RECORDS") != rows:
            raise TerrainProductError("FILE_RECORDS disagrees with IMAGE row count")
        metadata = LolaGdrMetadata(
            "PDS3 detached IMG",
            rows,
            columns,
            sample_type,
            bits,
            byte_order,
            units,
            scale,
            reference_radius_m,
            no_data_values,
            projection_type,
            "pixel center",
            resolution,
            latitude_type,
            longitude_direction.lower(),
            native_frame,
            axes,
        )
        layout = _ImageLayout(
            rows,
            columns,
            sample_bytes,
            sample_format,
            byte_order,
            scale,
            no_data,
            prefix,
            suffix,
            record_bytes,
            pointer,
            reference_radius_m,
            native_frame,
            axes,
            sample_type,
            no_data_values,
            projection_type,
            metadata,
        )
        return layout, geometry
    except KeyError as exc:
        raise TerrainProductError(f"required PDS label field is missing: {exc.args[0]}") from exc


def _image_pointer(fields: dict[str, str]) -> tuple[str, int | None]:
    raw = fields.get("^IMAGE")
    if raw is None:
        raise TerrainProductError("PDS label lacks ^IMAGE pointer")
    parts = [part.strip().strip('"') for part in raw.strip().strip("{}").split(",")]
    if not parts[0]:
        raise TerrainProductError("^IMAGE pointer has empty filename")
    if len(parts) == 1:
        return parts[0], None
    if len(parts) == 2:
        try:
            record = int(parts[1])
        except ValueError as exc:
            raise TerrainProductError("^IMAGE record pointer must be an integer") from exc
        if record < 1:
            raise TerrainProductError("PDS record pointers are one-based positive integers")
        return parts[0], record
    raise TerrainProductError("unsupported ^IMAGE pointer syntax")


def _parse_label(text: str) -> _LabelNode:
    root: dict[str, Any] = {"name": "ROOT", "fields": {}, "children": []}
    stack = [root]
    pending = ""
    ended = False
    for line in _remove_comments(text).splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pending = f"{pending} {stripped}".strip()
        if not _balanced(pending):
            continue
        if pending.strip().upper() == "END":
            if len(stack) != 1:
                raise TerrainProductError("PDS label terminates with open objects")
            ended = True
            pending = ""
            break
        if "=" not in pending:
            pending = ""
            continue
        key, value = (part.strip() for part in pending.split("=", 1))
        key = key.upper()
        if key == "END":
            if len(stack) != 1:
                raise TerrainProductError("PDS label terminates with open objects")
            ended = True
            break
        if key == "OBJECT":
            name = _scalar(value).upper()
            child: dict[str, Any] = {"name": name, "fields": {}, "children": []}
            stack[-1]["children"].append(child)
            stack.append(child)
        elif key == "END_OBJECT":
            if len(stack) == 1:
                raise TerrainProductError("PDS label has unmatched END_OBJECT")
            if _scalar(value).upper() != stack[-1]["name"]:
                raise TerrainProductError("PDS END_OBJECT name does not match its OBJECT")
            stack.pop()
        else:
            if key in stack[-1]["fields"]:
                raise TerrainProductError(f"duplicate PDS keyword in one scope: {key}")
            stack[-1]["fields"][key] = value
        pending = ""
    if pending or len(stack) != 1 or not ended:
        raise TerrainProductError("PDS label lacks END or ends within an incomplete value/object")
    return _freeze_node(root)


def _freeze_node(value: dict[str, Any]) -> _LabelNode:
    return _LabelNode(
        value["name"],
        {key: item.strip() for key, item in value["fields"].items()},
        tuple(_freeze_node(child) for child in value["children"]),
    )


def _remove_comments(text: str) -> str:
    result: list[str] = []
    in_string = False
    in_comment = False
    index = 0
    while index < len(text):
        pair = text[index : index + 2]
        char = text[index]
        if in_comment:
            if pair == "*/":
                in_comment = False
                result.extend("  ")
                index += 2
                continue
            result.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if char == '"' and (index == 0 or text[index - 1] != "\\"):
            in_string = not in_string
        if not in_string and pair == "/*":
            in_comment = True
            result.extend("  ")
            index += 2
            continue
        result.append(char)
        index += 1
    if in_comment or in_string:
        raise TerrainProductError("PDS label contains an unterminated comment or quoted string")
    return "".join(result)


def _balanced(value: str) -> bool:
    in_string = False
    braces = 0
    for index, char in enumerate(value):
        if char == '"' and (index == 0 or value[index - 1] != "\\"):
            in_string = not in_string
        elif not in_string and char == "{":
            braces += 1
        elif not in_string and char == "}":
            braces -= 1
    return not in_string and braces == 0


def _scalar(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('""', '"').strip()
    return value.split("<", 1)[0].strip().upper() if "<" in value else value.strip()


def _required_value(fields: dict[str, str], key: str) -> str:
    value = fields.get(key)
    if value is None:
        raise KeyError(key)
    return _scalar(value)


def _value(fields: dict[str, str], key: str, *, required: bool = True) -> str | None:
    value = fields.get(key)
    if value is None:
        if required:
            raise KeyError(key)
        return None
    return _scalar(value)


def _number(fields: dict[str, str], key: str) -> float:
    value = _value(fields, key)
    assert value is not None
    return _parse_number(value)


def _parse_number(raw: str) -> float:
    normalized = raw.strip().split("<", 1)[0].strip().replace("D", "E")
    try:
        value = float(normalized)
    except ValueError as exc:
        raise TerrainProductError(f"expected numeric PDS value, got {raw!r}") from exc
    if not math.isfinite(value):
        raise TerrainProductError(f"PDS numeric value must be finite, got {raw!r}")
    return value


def _integer(fields: dict[str, str], key: str, *, required: bool = True, default: int = 0) -> int:
    raw = _value(fields, key, required=required)
    if raw is None:
        return default
    value = _parse_number(raw)
    if not value.is_integer():
        raise TerrainProductError(f"PDS field {key} must be an integer")
    return int(value)


def _require_unit(fields: dict[str, str], key: str, allowed: set[str]) -> None:
    raw = fields.get(key)
    match = None if raw is None else re.search(r"<\s*([^>]+)\s*>\s*$", raw)
    if match is None or match.group(1).strip().upper() not in allowed:
        raise TerrainProductError(
            f"PDS field {key} must declare one of these units: {sorted(allowed)}"
        )


def _length_m(fields: dict[str, str], key: str) -> float:
    raw = fields.get(key)
    if raw is None:
        raise TerrainProductError(f"required PDS radius field is missing: {key}")
    match = re.fullmatch(r"\s*(.*?)\s*<\s*([^>]+)\s*>\s*", raw)
    if match is None:
        raise TerrainProductError(f"PDS radius field {key} must include a length unit")
    value = _parse_number(match.group(1))
    unit = match.group(2).strip().upper()
    if unit in {"KM", "KILOMETER", "KILOMETERS"}:
        return value * 1000.0
    if unit in {"M", "METER", "METERS"}:
        return value
    raise TerrainProductError(f"unsupported radius unit for {key}: {unit!r}")


def _verify_expected_hash(expected: str | None, actual: str, kind: str) -> None:
    if expected is not None:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
            raise TerrainProductError(f"expected {kind} SHA-256 must be 64 hexadecimal characters")
        if expected.lower() != actual:
            raise TerrainProductError(f"{kind} SHA-256 does not match trusted expected digest")


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise TerrainProductError(f"cannot hash image product: {path}") from exc
    return digest.hexdigest()
