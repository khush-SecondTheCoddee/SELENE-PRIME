# Reproducibility

**Status:** policy and software-foundation guidance; end-to-end reproducibility has not yet been demonstrated.

## Current package

Current core runtime code uses only the Python standard library; SpiceyPy is an optional bounded extra. `pyproject.toml` specifies the supported Python lower bound and bounded development-tool versions. The development extra is not a lockfile, and its resolved versions can change within those ranges. No third-party numerical stack has been selected. `pyproject.toml` bounds pytest/Ruff/mypy and optional SpiceyPy versions. `uv.lock` records resolved package versions and hashes across its declared Python/platform markers. The current base package has no runtime dependencies. Lockfile installation of the `dev` extra has not completed on Termux because Ruff requires a Rust/maturin build unavailable in this toolchain.

For a reproducible environment, record the Python implementation/version, OS/architecture, package source revision, and the exact resolved dependency list from the environment. The lockfile is generated with `uv lock` and checked with `uv lock --check`. Hosted CI should verify `uv sync --locked --extra dev` on its supported Linux matrix.

## Run and data provenance policy

Every scientific run will record software version/revision, timezone-aware creation timestamp, configuration identity, and input artifact identities/hashes. Hash fields are assertions until a later artifact-management subsystem computes and verifies them. Keep kernel manifests, terrain product identifiers, label files, source references, model/passband selections, numerical settings, and uncertainty seeds with benchmark outputs. Do not redistribute restricted data; document authoritative acquisition and product versions instead.

The `RunProvenance` record serializes supplied fields to deterministic JSON; asserted hashes are not verified by that record. Benchmark records and the current synthetic report preserve reference, input description, tolerance, actual value, error, and status. This does not establish authenticity of the reference or end-to-end scientific reproducibility.
