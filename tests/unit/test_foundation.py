"""Tests for foundational records; these do not validate scientific algorithms."""

import json
import logging
from io import StringIO

import pytest

from selene_prime.errors import ConfigurationError, ProvenanceError
from selene_prime.logging import configure_logging
from selene_prime.models import ArtifactReference, Epoch, Quantity, RunProvenance


def test_epoch_preserves_value_and_time_scale_without_conversion() -> None:
    epoch = Epoch("2026-11-08T00:00:00Z", "UTC")
    assert (epoch.value, epoch.time_scale) == ("2026-11-08T00:00:00Z", "UTC")


def test_epoch_requires_explicit_nonempty_fields() -> None:
    with pytest.raises(ConfigurationError):
        Epoch(" ", "UTC")
    with pytest.raises(ConfigurationError):
        Epoch("2451545.0", " ")


def test_quantity_requires_finite_value_and_unit() -> None:
    assert Quantity(1.5, "km").unit == "km"
    for invalid in (float("nan"), float("inf"), -float("inf"), True):
        with pytest.raises(ConfigurationError):
            Quantity(invalid, "m")
    with pytest.raises(ConfigurationError):
        Quantity(2.0, " ")


def test_artifact_digest_validation_is_syntax_only() -> None:
    digest = "a" * 64
    artifact = ArtifactReference("terrain", "dem", "file:///terrain.img", digest)
    assert artifact.sha256 == digest
    with pytest.raises(ProvenanceError):
        ArtifactReference("terrain", "dem", sha256="not-a-digest")


def test_provenance_json_round_trip_is_deterministic() -> None:
    provenance = RunProvenance(
        software_version="1.0.0",
        created_at="2026-11-08T00:00:00Z",
        artifacts=(ArtifactReference("kernels", "kernel-manifest", sha256="b" * 64),),
        configuration_sha256="c" * 64,
        source_revision="abc123",
    )
    encoded = provenance.to_json()
    assert encoded == provenance.to_json()
    restored = RunProvenance.from_json(encoded)
    assert restored == provenance
    assert json.loads(encoded)["schema_version"] == 1


def test_provenance_rejects_naive_timestamp_and_invalid_digest() -> None:
    with pytest.raises(ProvenanceError):
        RunProvenance("1.0.0", "2026-11-08T00:00:00")
    with pytest.raises(ProvenanceError):
        RunProvenance("1.0.0", "2026-11-08T00:00:00Z", configuration_sha256="bad")


def test_structured_logging_is_json_and_does_not_touch_root_logger() -> None:
    stream = StringIO()
    root_handlers = tuple(logging.getLogger().handlers)
    logger = configure_logging(logging.INFO, stream=stream)
    logger.info("query accepted", extra={"case_id": "analytic-1"})
    event = json.loads(stream.getvalue())
    assert event["message"] == "query accepted"
    assert event["fields"]["case_id"] == "analytic-1"
    assert tuple(logging.getLogger().handlers) == root_handlers
