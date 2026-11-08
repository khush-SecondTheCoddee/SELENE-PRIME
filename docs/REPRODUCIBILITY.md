# Reproducibility

**Status:** policy and software-foundation guidance; end-to-end reproducibility has not yet been demonstrated.

## Current package

The Phase 2 runtime code uses only the Python standard library. `pyproject.toml` specifies the supported Python lower bound and bounded development-tool versions. The development extra is not a lockfile, and its resolved versions can change within those ranges. No third-party scientific dependencies have been selected yet, so a truthful cross-platform lock cannot be supplied in this phase.

For a reproducible environment, record the Python implementation/version, OS/architecture, package source revision, and the exact resolved dependency list from the environment. Once NumPy/SPICE/terrain dependencies and supported platforms are selected, generate and commit a lock or constraints artifact for each supported environment and verify installation from it in CI.

## Run and data provenance policy

Every scientific run will record software version/revision, timezone-aware creation timestamp, configuration identity, and input artifact identities/hashes. Hash fields are assertions until a later artifact-management subsystem computes and verifies them. Keep kernel manifests, terrain product identifiers, label files, source references, model/passband selections, numerical settings, and uncertainty seeds with benchmark outputs. Do not redistribute restricted data; document authoritative acquisition and product versions instead.

The `RunProvenance` foundation record serializes its supplied fields to deterministic JSON. It does not validate file existence, verify hashes, identify kernel coverage, or establish provenance authenticity.
