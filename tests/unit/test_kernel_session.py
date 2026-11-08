"""Failure-injection checks; temporary bytes are not valid scientific SPICE kernels."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

import pytest

from selene_prime.errors import (
    EphemerisCoverageError,
    EphemerisQueryError,
    FrameTransformError,
    KernelCleanupError,
    KernelIntegrityError,
    KernelSessionError,
)
from selene_prime.frames import FrameService
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels import (
    AberrationCorrection,
    KernelKind,
    KernelManifest,
    KernelRole,
    KernelSession,
    KernelSpec,
)

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
QUARTER_TURN = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


class FakeSpice:
    def __init__(self) -> None:
        self.loaded: list[tuple[str, str]] = []
        self.unload_order: list[str] = []
        self.fail_load_after_add: str | None = None
        self.fail_unload: set[str] = set()
        self.fail_query = False
        self.coverage = {301: [(0.0, 100.0)]}

    def ktotal(self, kind: str) -> int:
        assert kind == "ALL"
        return len(self.loaded)

    def kdata(self, which: int, kind: str) -> tuple[object, ...]:
        assert kind == "ALL"
        path, kernel_type = self.loaded[which]
        return (path, kernel_type, "", "", True)

    def furnsh(self, path: str) -> None:
        self.loaded.append((path, "SPK"))
        if path == self.fail_load_after_add:
            raise RuntimeError("injected furnsh error after KEEPER add")

    def unload(self, path: str) -> None:
        self.unload_order.append(path)
        if path in self.fail_unload:
            raise RuntimeError("injected unload failure")
        self.loaded = [record for record in self.loaded if record[0] != path]

    def namfrm(self, frame: str) -> int:
        return {"J2000": 1, "MOON_PA": 31000}.get(frame, 0)

    def pxform(self, from_frame: str, to_frame: str, et: float) -> Iterable[Iterable[float]]:
        del et
        if from_frame == "J2000" and to_frame == "MOON_PA":
            return QUARTER_TURN
        return IDENTITY

    def spkezr(
        self, target: str, et: float, frame: str, abcorr: str, observer: str
    ) -> tuple[Iterable[float], float]:
        del target, et, frame, abcorr, observer
        if self.fail_query:
            raise RuntimeError("injected SPICE chain failure")
        return (1.0, 2.0, 3.0, 0.1, 0.2, 0.3), 2.5

    def spkobj(self, spk: str) -> Iterable[int]:
        del spk
        return [301]

    def spkcov(self, spk: str, body_id: int) -> object:
        del spk
        return self.coverage.get(body_id, [])

    def wncard(self, window: object) -> int:
        return len(window)  # type: ignore[arg-type]

    def wnfetd(self, window: object, interval: int) -> tuple[float, float]:
        return window[interval]  # type: ignore[index,return-value]


def make_manifest(tmp_path: Path, count: int = 1) -> KernelManifest:
    specs = []
    for index in range(count):
        path = tmp_path / f"fixture-{index}.bsp"
        path.write_bytes(f"not a SPICE kernel {index}".encode())
        specs.append(
            KernelSpec(
                path.name,
                hashlib.sha256(path.read_bytes()).hexdigest(),
                KernelKind.SPK,
                KernelRole.EPHEMERIS,
                "synthetic lifecycle test bytes; not an official kernel",
            )
        )
    return KernelManifest(tuple(specs), tmp_path)


def test_session_loads_owns_and_unloads_only_its_files_in_reverse_order(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path, count=2)
    spice = FakeSpice()
    with KernelSession(manifest, spice_api=spice) as session:
        assert len(session.loaded_kernels) == 2
        assert all(record.owned_by_session for record in session.loaded_kernels)
    assert spice.unload_order == [str((tmp_path / "fixture-1.bsp").resolve()), str((tmp_path / "fixture-0.bsp").resolve())]
    assert spice.loaded == []


def test_manifest_hash_mismatch_rejects_before_loading(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path)
    (tmp_path / "fixture-0.bsp").write_bytes(b"changed after manifest construction")
    spice = FakeSpice()
    with pytest.raises(KernelIntegrityError):
        with KernelSession(manifest, spice_api=spice):
            pytest.fail("hash mismatch must stop before context entry")
    assert spice.loaded == []


def test_preloaded_foreign_keeper_content_is_rejected_and_preserved(tmp_path: Path) -> None:
    spice = FakeSpice()
    spice.loaded.append(("caller-owned.bsp", "SPK"))
    with pytest.raises(KernelSessionError, match="pre-populated"):
        with KernelSession(make_manifest(tmp_path), spice_api=spice):
            pytest.fail("foreign KEEPER must not be shared")
    assert spice.loaded == [("caller-owned.bsp", "SPK")]


def test_partial_load_failure_rolls_back_added_kernel(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path, count=2)
    spice = FakeSpice()
    spice.fail_load_after_add = str((tmp_path / "fixture-1.bsp").resolve())
    with pytest.raises(KernelSessionError, match="failed to load"):
        with KernelSession(manifest, spice_api=spice):
            pytest.fail("second load should fail")
    assert spice.loaded == []
    assert spice.unload_order == [str((tmp_path / "fixture-1.bsp").resolve()), str((tmp_path / "fixture-0.bsp").resolve())]


def test_cleanup_failure_is_visible_and_remaining_ownership_is_retryable(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path)
    spice = FakeSpice()
    path = str((tmp_path / "fixture-0.bsp").resolve())
    spice.fail_unload.add(path)
    session = KernelSession(manifest, spice_api=spice)
    with pytest.raises(KernelCleanupError):
        with session:
            pass
    assert spice.loaded == [(path, "SPK")]
    spice.fail_unload.clear()
    session.close()
    assert spice.loaded == []


def test_actual_target_observer_query_and_frame_service_are_explicit(tmp_path: Path) -> None:
    spice = FakeSpice()
    with KernelSession(make_manifest(tmp_path), spice_api=spice) as session:
        query = session.validate_state_query(
            "SUN", "MOON", 25.0, "MOON_PA", AberrationCorrection.CN_S
        )
        assert query.state_km_km_s == (1.0, 2.0, 3.0, 0.1, 0.2, 0.3)
        assert query.light_time_seconds == 2.5
        mapped = FrameService(session).transform_vector(
            Vector3(1.0, 0.0, 0.0, "km"), "J2000", "MOON_PA", 25.0
        )
        assert mapped == Vector3(0.0, 1.0, 0.0, "km")
        with pytest.raises(FrameTransformError, match="unknown"):
            FrameService(session).transform("UNKNOWN", "MOON_PA", 25.0)


def test_state_chain_failure_and_spk_coverage_gap_are_not_accepted(tmp_path: Path) -> None:
    manifest = make_manifest(tmp_path)
    spice = FakeSpice()
    with KernelSession(manifest, spice_api=spice) as session:
        with pytest.raises(EphemerisCoverageError, match="not covered"):
            session.check_spk_body_coverage(manifest.kernels[0], 301, 101.0)
        with pytest.raises(EphemerisCoverageError, match="no segment"):
            session.check_spk_body_coverage(manifest.kernels[0], 399, 25.0)
        spice.fail_query = True
        with pytest.raises(EphemerisQueryError, match="chain is not established"):
            session.validate_state_query(
                "SUN", "MOON", 25.0, "MOON_PA", AberrationCorrection.NONE
            )
