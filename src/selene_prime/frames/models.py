"""Named frame metadata and frame-tagged vectors.

Declarations are caller-supplied metadata, not proof that a SPICE frame is loaded.
No default lunar frame registry is shipped.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from selene_prime.errors import ConfigurationError, FrameDefinitionError
from selene_prime.geometry.vectors import Vector3


class FrameKind(str, Enum):
    """Broad frame classification used at coordinate-service boundaries."""
    INERTIAL = "inertial"
    BODY_FIXED = "body_fixed"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class FrameDefinition:
    """Caller-verified description of a named frame."""
    name: str
    center: str
    kind: FrameKind
    source: str

    def __post_init__(self) -> None:
        for field_name, value in (("name", self.name), ("center", self.center), ("source", self.source)):
            if not isinstance(value, str) or not value.strip():
                raise FrameDefinitionError(f"frame {field_name} must be a nonempty string")
        if not isinstance(self.kind, FrameKind):
            raise FrameDefinitionError("frame kind must be an explicit FrameKind")


class FrameRegistry:
    """Explicit registry; unknown frames are never inferred or auto-created."""
    def __init__(self) -> None:
        self._frames: dict[str, FrameDefinition] = {}

    def register(self, definition: FrameDefinition) -> None:
        existing = self._frames.get(definition.name)
        if existing is not None:
            if existing != definition:
                raise FrameDefinitionError(
                    f"frame {definition.name!r} is already registered differently"
                )
            raise FrameDefinitionError(f"frame {definition.name!r} is already registered")
        self._frames[definition.name] = definition

    def get(self, name: str) -> FrameDefinition:
        try:
            return self._frames[name]
        except KeyError as exc:
            raise FrameDefinitionError(f"frame {name!r} is not registered") from exc

    def require_body_fixed(self, name: str, *, center: str) -> FrameDefinition:
        definition = self.get(name)
        if definition.kind is not FrameKind.BODY_FIXED:
            raise FrameDefinitionError(f"frame {name!r} is not declared body-fixed")
        if definition.center != center:
            raise FrameDefinitionError(
                f"frame {name!r} is centered on {definition.center!r}, not {center!r}"
            )
        return definition

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._frames)


@dataclass(frozen=True, slots=True)
class FramedVector3:
    """A vector whose components are expressed in a named reference frame."""
    vector: Vector3
    frame: str

    def __post_init__(self) -> None:
        if not isinstance(self.frame, str) or not self.frame.strip():
            raise ConfigurationError("vector frame must be a nonempty string")
