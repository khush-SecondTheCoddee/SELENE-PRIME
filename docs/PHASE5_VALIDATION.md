# Phase 5 validation record — terrain product and grid

## Executed synthetic checks

Tests use a 4×4 synthetic image and PDS3 label with metadata shaped after the published LOLA GDR `LDEM_64` example. The sample values and mini product are deterministic test data, not real lunar observations.

| Case | Independent expected value / condition | Actual test evidence | Status |
|---|---|---|---|
| 16-bit little-endian signed decoding | First raw sample 0; declared scale 0.5 gives 0 m | `test_pds3_lola_sample_decoding_scaling_registration_and_provenance` | Pass |
| Bilinear pixel-center interpolation | Four corners at the query are heights 0, 2, 10, 12 m; arithmetic mean is 6 m | Same test | Pass |
| Reference radius use | 1,737,400 m radius + 6 m height = 1,737,406 m | Same test | Pass |
| Big-endian signed decoding | Same signed raw matrix and scale must produce the same heights | `test_msb_signed_sample_encoding_is_decoded` | Pass |
| Product file integrity | Trusted expected SHA-256 mismatch rejects; exact image byte length is required | `test_pds_label_hash_mismatch_is_rejected`, `test_image_size_mismatch_is_rejected` | Pass |
| Unsupported storage encoding | `PC_REAL` is rejected by this 16-bit integer profile | `test_unsupported_encoding_is_rejected` | Pass |
| Longitude conventions and periodicity | Longitudes differing by 360° map to the same global-grid sample | `test_global_longitude_wraps_and_pole_singularity_is_explicit` | Pass |
| Regional antimeridian | Equivalent 359.5° and −0.5° inputs map identically; remote coordinate rejects | `test_regional_grid_crossing_antimeridian_maps_both_longitude_conventions` | Pass |
| Edges and NoData | Exact valid pixel center remains usable despite zero-weight NoData neighbors; nonzero-weight NoData rejects; out-of-center regional extrapolation rejects | `test_regional_edges_nodata_and_exact_sample_behavior` | Pass |
| Grid regularity | Nonuniform axes and unsupported axis order reject | `test_grid_axes_reject_nonuniform_or_wrongly_ordered_coordinates` | Pass |

The analytic interpolation value is calculated directly from its four scalar corner heights using the bilinear interpolation definition. These checks validate parser and grid behavior for the synthetic case only.

## Commands executed

- `pytest -q tests/unit/test_terrain.py` — **9 passed** on Python 3.14.6 / Android (Termux).
- `python -m pytest -q` — **41 passed** on Python 3.14.6 / Android (Termux).
- `python -m mypy` — **passed**, strict configuration, 17 source files checked.
- `python -m compileall -q src tests` — **passed**.
- `git diff --check` — **passed**.
- Ruff — **not run**, Ruff is not installed in this environment.

## Authentic product acquisition evidence

The real PDS3 LDEM_16 product was opened with the reader using the archive image SHA-256 as an expected digest. The 33,177,600-byte image hash is `a511e40d7a3ea3275945b4da2a1df377133264fab0be94b7434b1cf8907254cb`. A separately downloaded copy from the official LOLA Data Node mirror compared byte-for-byte and produced the same hash. Individual kernel hashes are recorded in `config/research_kernels_de421.json`. This verifies local bytes against a second official host copy; it is not a checksum published by the PDS archive. The detached label digest is recorded locally but has no independently trusted digest in the archive listing. See `docs/REAL_DATA_CASE.md` for the pending end-to-end computation workflow.

## Limitations

The synthetic fixture uses simplified dimensions rather than the published raster. Authentic PDS ingestion was separately exercised as recorded above; automatic frame conversion, horizon accuracy, global data continuity, and compatibility with all LOLA GDR releases remain pending. The 62-test suite itself remains synthetic for terrain cases.

The PDS3 LOLA GDR SIS states the sampled `HEIGHT` conversion is `DN × SCALING_FACTOR` in metres and distinguishes the `OFFSET` reference radius; the adapter retains these as separate quantities. The PDS3 standard defines projection offsets and pixel-coordinate conventions; test expectations use the corresponding pixel-center mapping. References: [LOLA GDR sample and SIS](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/rdrsis.htm), [PDS3 Standards Reference](https://pds.nasa.gov/datastandards/pds3/standards/), and [LOLA GDR product overview](https://ode.rsl.wustl.edu/mars/pagehelp/Content/Missions_Instruments/LRO/LOLA/GDR/GDRDEM.htm).
