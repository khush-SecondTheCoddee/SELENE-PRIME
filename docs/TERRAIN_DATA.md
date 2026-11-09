# Terrain data support — Phase 5

## Supported profile

The first product adapter reads detached **PDS3 LRO LOLA GDR** cylindrical `.IMG` files where the label declares:

- `DATA_SET_ID = LRO-L-LOLA-4-GDR-V1.0` and one product identifier;
- one `UNCOMPRESSED_FILE`, one `IMAGE`, and one `IMAGE_MAP_PROJECTION`;
- fixed-length rows with no unsupported record addressing;
- 16-bit signed `LSB_INTEGER` or `MSB_INTEGER` samples;
- `IMAGE` named `HEIGHT`, metre units, scale factor, and reference-radius `OFFSET`;
- unrotated simple cylindrical map projection, east-positive longitude, body-fixed rotating coordinates, and pixel-center registration;
- explicit angular resolution, projection offsets, coordinate-system name, axis radii with units, and image dimensions/bounds that agree.

The adapter memory maps the raster and decodes samples on demand. It preserves label/image SHA-256 digests, product identifiers, encoding, scale, NoData sentinels, registration, grid dimensions, angular resolution, native coordinate-system name, latitude type, and datum axes. If trusted expected SHA-256 values are supplied, they are checked. A locally calculated digest identifies bytes; it does not prove that they came from NASA/PDS. This adapter does not interpret a PDS integer `CHECKSUM` field as a cryptographic hash.

The official LOLA GDR SIS example describes `LDEM_64` as pixel-registered, gives 16-bit `LSB_INTEGER`, metre units, a 0.5 scale, a 1,737,400 m `OFFSET`, simple cylindrical projection parameters, and the Mean Earth/Polar Axis of DE421 frame. For this `HEIGHT` product, the SIS states `HEIGHT = DN × SCALING_FACTOR`; its `OFFSET` is separately the reference radius, so the adapter adds it only when calculating surface radius. See the [LOLA GDR sample label in the product SIS](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/rdrsis.htm) and [PDS3 standards reference](https://pds.nasa.gov/datastandards/pds3/standards/).

## Explicit exclusions

PDS4 labels, JPEG2000, polar stereographic grids, attached or record-addressed IMAGE objects, VAX/PC floating formats, equirectangular projections, multiband data, arbitrary PDS3 raster products, rotated rasters, and unknown coordinate semantics are rejected. No automatic datum/frame transformation is applied. The grid retains its native frame and latitude type; consumers must transform coordinates using an independently validated frame/datum service before combining it with another frame.

## Interpolation

`TerrainGrid` treats integer line/sample coordinates as pixel centers. It uses bilinear interpolation on a regular cylindrical grid, with row increasing southward and the PDS sample direction represented explicitly. Global grids wrap in longitude; regional grids accept either 0–360 or −180–180 longitude values by choosing the nearest longitude difference around the projection center, then reject coordinates outside pixel-center bounds. It does not extrapolate regionally. At an exact pole, cylindrical longitude is singular, so the query is rejected; polar stereographic support is future work. Bilinear queries fail if a nonzero-weight corner is NoData, rather than replacing unknown terrain with zero.

Interpolation assumes the declared raster registration and projection are correct. It cannot recover terrain finer than the input spacing and is not itself a terrain-horizon error bound.

## Obtaining and supplying products

Obtain LOLA GDR data and its detached label from the [PDS Geosciences LOLA archive](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) or the PDS product collection. Keep the `.LBL` and `.IMG` together. Verify the dataset/product version and file digests against a trusted PDS/mission manifest or a locally controlled acquisition record, then pass the trusted digests to `LolaGdrProduct.open`. Do not use a synthetic array or unit-test fixture as a real DEM.

Example:

```python
from selene_prime.terrain import LolaGdrProduct

with LolaGdrProduct.open(
    "LDEM_64.LBL",
    expected_label_sha256="<trusted 64-character SHA-256>",
    expected_image_sha256="<trusted 64-character SHA-256>",
) as product:
    height_m = product.grid.elevation_m(latitude_deg=12.0, longitude_deg=45.0)
    radius_m = product.grid.surface_radius_m(latitude_deg=12.0, longitude_deg=45.0)
    print(product.provenance, product.metadata)
```

A failed/missing input file, unsupported label field, digest mismatch, encoding mismatch, inconsistent dimensions, or invalid interpolation footprint raises a typed terrain exception.
