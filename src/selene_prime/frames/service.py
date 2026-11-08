"""Fail-closed rotation-only reference-frame transformation service."""
from __future__ import annotations

import math
from typing import Protocol

from selene_prime.errors import FrameTransformError
from selene_prime.frames.models import FramedVector3, FrameRegistry
from selene_prime.geometry.rotations import Rotation3


class TransformProvider(Protocol):
    """Provider returning a rotation mapping source-frame components to target."""

    def rotation(self, source: str, target: str, et_seconds: float) -> Rotation3:
        """Return source-to-target rotation at SPICE ET seconds."""


class FrameService:
    """Apply frame rotations without origin translation.

    Source and target must share an origin. ET is supplied explicitly; this
    service does not parse UTC or convert time systems.
    """

    def __init__(
        self, registry: FrameRegistry, provider: TransformProvider | None = None
    ) -> None:
        self._registry = registry
        self._provider = provider

    def transform_vector(
        self, value: FramedVector3, *, target_frame: str, et_seconds: float
    ) -> FramedVector3:
        if (
            isinstance(et_seconds, bool)
            or not isinstance(et_seconds, (int, float))
            or not math.isfinite(et_seconds)
        ):
            raise FrameTransformError("ET seconds must be a finite numeric value")

        source_definition = self._registry.get(value.frame)
        target_definition = self._registry.get(target_frame)
        if source_definition.center != target_definition.center:
            raise FrameTransformError(
                "rotation-only transformation requires frames with the same origin; "
                f"{value.frame!r} is centered on {source_definition.center!r}, "
                f"but {target_frame!r} is centered on {target_definition.center!r}"
            )
        if value.frame == target_frame:
            return FramedVector3(value.vector, target_frame)
        if self._provider is None:
            raise FrameTransformError(
                f"no transform provider is configured for {value.frame!r} to {target_frame!r}"
            )
        try:
            rotation = self._provider.rotation(value.frame, target_frame, float(et_seconds))
            transformed = rotation.apply(value.vector)
        except FrameTransformError:
            raise
        except Exception as exc:
            raise FrameTransformError(
                f"failed to transform {value.frame!r} to {target_frame!r} "
                f"at ET {et_seconds:.9f}"
            ) from exc
        return FramedVector3(transformed, target_frame)

    def require_body_fixed(self, frame: str, *, center: str) -> None:
        """Validate a frame before using it for body-fixed surface coordinates."""
        self._registry.require_body_fixed(frame, center=center)
