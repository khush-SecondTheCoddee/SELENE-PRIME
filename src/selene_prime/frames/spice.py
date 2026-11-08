"""Optional SpiceyPy adapter for time-dependent frame rotations."""
from __future__ import annotations

import importlib
from typing import Any

from selene_prime.errors import FrameTransformError, OptionalDependencyError
from selene_prime.geometry.rotations import Rotation3


class SpiceyPyTransformProvider:
    """Use SPICE pxform with an already furnished kernel pool.

    Kernel lifecycle, coverage validation, and time conversion are outside this
    adapter. The caller supplies SPICE ET seconds. There is no identity fallback.
    """
    def __init__(self, spice_module: Any | None = None) -> None:
        if spice_module is None:
            try:
                spice_module = importlib.import_module("spiceypy")
            except ImportError as exc:
                raise OptionalDependencyError(
                    "SpiceyPy is required for SPICE frame transformations; "
                    "install the 'spice' optional dependency"
                ) from exc
        if not callable(getattr(spice_module, "pxform", None)):
            raise OptionalDependencyError("the supplied SPICE module has no callable pxform")
        self._spice = spice_module

    def rotation(self, source: str, target: str, et_seconds: float) -> Rotation3:
        try:
            raw = self._spice.pxform(source, target, et_seconds)
            rows = tuple(tuple(float(value) for value in row) for row in raw)
            return Rotation3(rows)  # type: ignore[arg-type]
        except Exception as exc:
            raise FrameTransformError(
                f"SPICE pxform failed for {source!r} to {target!r} at ET {et_seconds:.9f}; "
                "check frame definitions, furnished kernels, and epoch coverage"
            ) from exc
