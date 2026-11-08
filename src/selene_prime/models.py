"""Small immutable records shared across subsystem boundaries.

These records preserve explicit metadata. They do not perform time, frame, datum,
or unit conversion; those operations belong to validated scientific services.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from selene_prime.errors import ConfigurationError, ProvenanceError

_SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True, slots=True)
class Epoch:
    """An epoch value with its source time-scale label; no conversion is implied."""

    value: str
    time_scale: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ConfigurationError("epoch value must not be empty")
        if not self.time_scale.strip():
            raise ConfigurationError("epoch time_scale must not be empty")


@dataclass(frozen=True, slots=True)
class Quantity:
    """A finite numeric value paired with an explicit unit string."""

    value: float
    unit: str

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not math.isfinite(self.value):
            raise ConfigurationError("quantity value must be a finite number")
        if not self.unit.strip():
            raise ConfigurationError("quantity unit must not be empty")


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Reference to an input artifact and optional asserted SHA-256 digest.

    This validates digest syntax only. It does not read files or assert that the
    digest matches the referenced artifact.
    """

    name: str
    role: str
    location: str | None = None
    sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ProvenanceError("artifact name must not be empty")
        if not self.role.strip():
            raise ProvenanceError("artifact role must not be empty")
        if self.sha256 is not None and not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ProvenanceError("sha256 must contain exactly 64 hexadecimal characters")


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """Serializable record identifying inputs and software for one run."""

    software_version: str
    created_at: str
    artifacts: tuple[ArtifactReference, ...] = ()
    configuration_sha256: str | None = None
    source_revision: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        if not self.software_version.strip():
            raise ProvenanceError("software_version must not be empty")
        if self.schema_version < 1:
            raise ProvenanceError("schema_version must be a positive integer")
        try:
            timestamp = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ProvenanceError("created_at must be an ISO-8601 timestamp") from exc
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ProvenanceError("created_at must include a timezone")
        if self.configuration_sha256 is not None and not _SHA256_PATTERN.fullmatch(
            self.configuration_sha256
        ):
            raise ProvenanceError(
                "configuration_sha256 must contain exactly 64 hexadecimal characters"
            )

    def to_json(self) -> str:
        """Return deterministic JSON for this record (no filesystem verification)."""
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_json(cls, payload: str) -> RunProvenance:
        """Parse and validate a JSON provenance record."""
        try:
            raw: Any = json.loads(payload)
            if not isinstance(raw, dict):
                raise TypeError("top-level JSON value must be an object")
            data = dict(raw)
            artifacts_raw = data.get("artifacts", ())
            if not isinstance(artifacts_raw, (list, tuple)):
                raise TypeError("artifacts must be a list")
            data["artifacts"] = tuple(ArtifactReference(**item) for item in artifacts_raw)
            return cls(**data)
        except (TypeError, KeyError, json.JSONDecodeError) as exc:
            raise ProvenanceError(f"invalid provenance JSON: {exc}") from exc
