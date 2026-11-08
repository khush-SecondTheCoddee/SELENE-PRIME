"""Tests for explicit frame metadata and fail-closed transformations."""
from __future__ import annotations

from typing import Any

import pytest

from selene_prime.errors import FrameDefinitionError, FrameTransformError
from selene_prime.frames import (
    FrameDefinition,
    FrameKind,
    FrameRegistry,
    FrameService,
    FramedVector3,
    SpiceyPyTransformProvider,
)
from selene_prime.geometry.rotations import Rotation3
from selene_prime.geometry.vectors import Vector3


MOON_FIXED = FrameDefinition(
    "TEST_MOON_FIXED", "301", FrameKind.BODY_FIXED, "synthetic unit-test declaration"
)
MOON_INERTIAL = FrameDefinition(
    "TEST_MOON_INERTIAL", "301", FrameKind.INERTIAL, "synthetic unit-test declaration"
)


class FixedRotationProvider:
    def __init__(self, rotation: Rotation3) -> None:
        self.rotation_value = rotation
        self.calls: list[tuple[str, str, float]] = []

    def rotation(self, source: str, target: str, et_seconds: float) -> Rotation3:
        self.calls.append((source, target, et_seconds))
        return self.rotation_value


def registry_with_test_frames() -> FrameRegistry:
    registry = FrameRegistry()
    registry.register(MOON_FIXED)
    registry.register(MOON_INERTIAL)
    return registry


def quarter_turn() -> Rotation3:
    return Rotation3(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))


def test_registry_requires_explicit_frames_and_rejects_conflicts() -> None:
    registry = FrameRegistry()
    registry.register(MOON_FIXED)
    assert registry.get("TEST_MOON_FIXED") == MOON_FIXED
    with pytest.raises(FrameDefinitionError):
        registry.get("IAU_MOON")
    with pytest.raises(FrameDefinitionError):
        registry.register(MOON_FIXED)
    with pytest.raises(FrameDefinitionError):
        registry.register(
            FrameDefinition("TEST_MOON_FIXED", "399", FrameKind.BODY_FIXED, "conflicting")
        )


def test_registry_requires_body_fixed_frame_and_expected_center() -> None:
    registry = registry_with_test_frames()
    assert registry.require_body_fixed("TEST_MOON_FIXED", center="301") == MOON_FIXED
    with pytest.raises(FrameDefinitionError):
        registry.require_body_fixed("TEST_MOON_INERTIAL", center="301")
    with pytest.raises(FrameDefinitionError):
        registry.require_body_fixed("TEST_MOON_FIXED", center="399")


def test_service_applies_source_to_target_rotation_and_preserves_unit() -> None:
    registry = registry_with_test_frames()
    provider = FixedRotationProvider(quarter_turn())
    service = FrameService(registry, provider)
    source = FramedVector3(Vector3(1.0, 0.0, 0.0, "m"), "TEST_MOON_INERTIAL")
    result = service.transform_vector(source, target_frame="TEST_MOON_FIXED", et_seconds=1234.5)
    assert result.frame == "TEST_MOON_FIXED"
    assert result.vector.x == pytest.approx(0.0)
    assert result.vector.y == pytest.approx(1.0)
    assert result.vector.z == pytest.approx(0.0)
    assert result.vector.unit == "m"
    assert provider.calls == [("TEST_MOON_INERTIAL", "TEST_MOON_FIXED", 1234.5)]


def test_same_frame_is_identity_without_external_provider() -> None:
    registry = registry_with_test_frames()
    service = FrameService(registry)
    value = FramedVector3(Vector3(1.0, 2.0, 3.0, "m"), "TEST_MOON_FIXED")
    assert service.transform_vector(value, target_frame="TEST_MOON_FIXED", et_seconds=0.0) == value


def test_service_fails_closed_without_provider_or_for_different_origins() -> None:
    registry = registry_with_test_frames()
    service = FrameService(registry)
    value = FramedVector3(Vector3(1.0, 0.0, 0.0, "m"), "TEST_MOON_INERTIAL")
    with pytest.raises(FrameTransformError, match="no transform provider"):
        service.transform_vector(value, target_frame="TEST_MOON_FIXED", et_seconds=1.0)

    registry.register(
        FrameDefinition("TEST_EARTH_FIXED", "399", FrameKind.BODY_FIXED, "synthetic test")
    )
    with pytest.raises(FrameTransformError, match="same origin"):
        service.transform_vector(value, target_frame="TEST_EARTH_FIXED", et_seconds=1.0)


@pytest.mark.parametrize("et", [float("nan"), float("inf"), -float("inf"), True])
def test_service_rejects_invalid_et(et: Any) -> None:
    registry = registry_with_test_frames()
    service = FrameService(registry, FixedRotationProvider(Rotation3.identity()))
    value = FramedVector3(Vector3(1.0, 0.0, 0.0, "1"), "TEST_MOON_INERTIAL")
    with pytest.raises(FrameTransformError, match="finite"):
        service.transform_vector(value, target_frame="TEST_MOON_FIXED", et_seconds=et)


def test_provider_wraps_spice_pxform_failure_without_identity_fallback() -> None:
    class BrokenSpice:
        @staticmethod
        def pxform(source: str, target: str, et: float) -> list[list[float]]:
            raise RuntimeError("no frame kernel")

    provider = SpiceyPyTransformProvider(BrokenSpice())
    with pytest.raises(FrameTransformError, match="pxform failed"):
        provider.rotation("IAU_MOON", "MOON_ME", 10.0)


def test_provider_converts_spice_rotation_matrix() -> None:
    class FakeSpice:
        @staticmethod
        def pxform(source: str, target: str, et: float) -> list[list[float]]:
            assert (source, target, et) == ("A", "B", 42.0)
            return [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]

    result = SpiceyPyTransformProvider(FakeSpice()).rotation("A", "B", 42.0)
    assert result.apply(Vector3(1.0, 0.0, 0.0, "1")) == Vector3(0.0, 1.0, 0.0, "1")


def test_service_rejects_unknown_target_frame() -> None:
    registry = registry_with_test_frames()
    service = FrameService(registry, FixedRotationProvider(Rotation3.identity()))
    value = FramedVector3(Vector3(1.0, 0.0, 0.0, "m"), "TEST_MOON_FIXED")
    with pytest.raises(FrameDefinitionError):
        service.transform_vector(value, target_frame="UNKNOWN", et_seconds=0.0)


def test_injected_provider_does_not_require_spiceypy_import() -> None:
    fake = type(
        "Fake", (), {"pxform": staticmethod(lambda a, b, et: Rotation3.identity().rows)}
    )()
    provider = SpiceyPyTransformProvider(fake)
    assert provider.rotation("A", "B", 0.0) == Rotation3.identity()
