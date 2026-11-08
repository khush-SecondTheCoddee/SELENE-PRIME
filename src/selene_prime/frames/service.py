"""Named, epoch-specific reference-frame transforms backed by a kernel session."""

from __future__ import annotations

from dataclasses import dataclass
import math

from selene_prime.errors import FrameTransformError
from selene_prime.geometry.rotations import Rotation3
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels.session import KernelSession


@dataclass(frozen=True, slots=True)
class FrameTransform:
    """A validated rotation whose direction and epoch remain explicit."""

    from_frame: str
    to_frame: str
    et_tdb_seconds_past_j2000: float
    rotation: Rotation3

    def apply(self, vector: Vector3) -> Vector3:
        """Map vector components from ``from_frame`` into ``to_frame``."""
        return self.rotation.apply(vector)


class FrameService:
    """Frame operations that never substitute an identity for a missing transform."""

    def __init__(self, session: KernelSession) -> None:
        self._session = session

    def transform(self, from_frame: str, to_frame: str, et: float) -> FrameTransform:
        """Resolve and validate a SPICE transform at ET (seconds past J2000 TDB)."""
        if not from_frame.strip() or not to_frame.strip() or not math.isfinite(et):
            raise FrameTransformError("frame names and finite ET are required")
        rotation = self._session.frame_rotation(from_frame, to_frame, et)
        return FrameTransform(from_frame, to_frame, et, rotation)

    def transform_vector(
        self, vector: Vector3, from_frame: str, to_frame: str, et: float
    ) -> Vector3:
        """Apply a validated, epoch-specific SPICE frame transform."""
        return self.transform(from_frame, to_frame, et).apply(vector)
