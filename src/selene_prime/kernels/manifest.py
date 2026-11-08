"""Explicit, hash-bearing SPICE kernel manifests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from selene_prime.errors import KernelManifestError

_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class KernelKind(str, Enum):
    """Kernel file class expected from SPICE KEEPER metadata."""

    SPK = "SPK"
    CK = "CK"
    BINARY_PCK = "PCK"
    DSK = "DSK"
    EK = "EK"
    TEXT = "TEXT"


class KernelRole(str, Enum):
    """Scientific/engineering role declared by the manifest author."""

    EPHEMERIS = "ephemeris"
    ORIENTATION = "orientation"
    FRAME_DEFINITION = "frame_definition"
    LEAP_SECONDS = "leap_seconds"
    SPACECRAFT_CLOCK = "spacecraft_clock"
    INSTRUMENT = "instrument"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class KernelSpec:
    """One individual kernel; meta-kernel files are intentionally unsupported."""

    path: str
    sha256: str
    kind: KernelKind
    role: KernelRole
    source: str

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise KernelManifestError("kernel path must be a nonempty string")
        if not isinstance(self.sha256, str) or not _SHA256.fullmatch(self.sha256):
            raise KernelManifestError("kernel sha256 must be 64 hexadecimal characters")
        if not isinstance(self.kind, KernelKind):
            raise KernelManifestError("kernel kind must be a supported KernelKind")
        if not isinstance(self.role, KernelRole):
            raise KernelManifestError("kernel role must be a supported KernelRole")
        if not isinstance(self.source, str) or not self.source.strip():
            raise KernelManifestError("kernel source/provenance must be provided")
        object.__setattr__(self, "sha256", self.sha256.lower())

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        kind: KernelKind,
        role: KernelRole,
        source: str,
    ) -> KernelSpec:
        """Construct a spec using a digest computed from the actual supplied file."""
        kernel_path = Path(path)
        return cls(str(kernel_path), sha256_file(kernel_path), kind, role, source)


@dataclass(frozen=True, slots=True)
class KernelManifest:
    """Ordered kernel set and base directory for resolving relative paths."""

    kernels: tuple[KernelSpec, ...]
    base_directory: Path = Path(".")
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != 1
        ):
            raise KernelManifestError(f"unsupported kernel manifest schema: {self.schema_version}")
        if not self.kernels:
            raise KernelManifestError("kernel manifest must contain at least one kernel")
        if any(not isinstance(spec, KernelSpec) for spec in self.kernels):
            raise KernelManifestError("manifest kernels must be KernelSpec records")
        normalized = [Path(spec.path).as_posix() for spec in self.kernels]
        if len(normalized) != len(set(normalized)):
            raise KernelManifestError("manifest contains duplicate kernel paths")
        object.__setattr__(self, "base_directory", Path(self.base_directory))

    def resolve(self, spec: KernelSpec) -> Path:
        """Resolve one path against the manifest directory and require a regular file."""
        candidate = Path(spec.path)
        if not candidate.is_absolute():
            candidate = self.base_directory / candidate
        try:
            resolved = candidate.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise KernelManifestError(f"kernel file is unavailable: {candidate}") from exc
        if not resolved.is_file():
            raise KernelManifestError(f"kernel path is not a regular file: {resolved}")
        return resolved

    def to_json(self) -> str:
        """Serialize the declared manifest; the resolution base is intentionally external."""
        value: dict[str, Any] = {
            "schema_version": self.schema_version,
            "kernels": [
                {
                    "path": item.path,
                    "sha256": item.sha256,
                    "kind": item.kind.value,
                    "role": item.role.value,
                    "source": item.source,
                }
                for item in self.kernels
            ],
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_json(cls, payload: str, *, base_directory: str | Path = ".") -> KernelManifest:
        """Parse and validate a manifest JSON string."""
        try:
            raw: Any = json.loads(payload)
            if not isinstance(raw, dict) or set(raw) != {"schema_version", "kernels"}:
                raise TypeError("manifest must have schema_version and kernels fields")
            if not isinstance(raw["kernels"], list):
                raise TypeError("kernels must be a JSON array")
            specs = tuple(
                KernelSpec(
                    path=item["path"],
                    sha256=item["sha256"],
                    kind=KernelKind(item["kind"]),
                    role=KernelRole(item["role"]),
                    source=item["source"],
                )
                for item in raw["kernels"]
            )
            return cls(specs, Path(base_directory), raw["schema_version"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, KernelManifestError):
                raise
            raise KernelManifestError(f"invalid kernel manifest JSON: {exc}") from exc

    @classmethod
    def load(cls, path: str | Path) -> KernelManifest:
        """Load a JSON manifest and resolve its relative paths from the manifest file."""
        try:
            manifest_path = Path(path).resolve(strict=True)
            payload = manifest_path.read_text(encoding="utf-8")
        except (OSError, RuntimeError) as exc:
            raise KernelManifestError(f"cannot read kernel manifest: {path}") from exc
        return cls.from_json(payload, base_directory=manifest_path.parent)


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 from a file's bytes; this does not establish source authenticity."""
    if chunk_size <= 0:
        raise KernelManifestError("chunk_size must be positive")
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for block in iter(lambda: stream.read(chunk_size), b""):
                digest.update(block)
    except OSError as exc:
        raise KernelManifestError(f"cannot hash kernel file: {path}") from exc
    return digest.hexdigest()
