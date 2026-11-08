"""Explicitly owned, serialized SPICE kernel sessions and guarded queries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import os
from pathlib import Path
import threading
from typing import Iterable, Literal, Protocol, cast

from selene_prime.errors import (
    EphemerisCoverageError,
    EphemerisQueryError,
    FrameTransformError,
    KernelCleanupError,
    KernelIntegrityError,
    KernelManifestError,
    KernelSessionError,
)
from selene_prime.geometry.rotations import Matrix3, Rotation3
from selene_prime.geometry.vectors import Vector3
from selene_prime.kernels.manifest import KernelKind, KernelManifest, KernelRole, KernelSpec, sha256_file


_PROCESS_SPICE_LOCK = threading.RLock()


def _reset_process_lock_after_fork() -> None:
    """Avoid inheriting a lock owned by a vanished thread in a forked child."""
    global _PROCESS_SPICE_LOCK
    _PROCESS_SPICE_LOCK = threading.RLock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_process_lock_after_fork)


class AberrationCorrection(str, Enum):
    """CSPICE SPKEZR aberration-correction tokens supported by this adapter."""

    NONE = "NONE"
    LT = "LT"
    LT_S = "LT+S"
    CN = "CN"
    CN_S = "CN+S"
    XLT = "XLT"
    XLT_S = "XLT+S"
    XCN = "XCN"
    XCN_S = "XCN+S"


class SpiceApi(Protocol):
    """Narrow subset of SpiceyPy used by this module and injectable in tests."""

    def ktotal(self, kind: str) -> int: ...

    def kdata(self, which: int, kind: str) -> tuple[object, ...]: ...

    def furnsh(self, path: str) -> None: ...

    def unload(self, path: str) -> None: ...

    def namfrm(self, frame: str) -> int: ...

    def pxform(self, from_frame: str, to_frame: str, et: float) -> Iterable[Iterable[float]]: ...

    def spkezr(
        self, target: str, et: float, frame: str, abcorr: str, observer: str
    ) -> tuple[Iterable[float], float]: ...

    def spkobj(self, spk: str) -> Iterable[int]: ...

    def spkcov(self, spk: str, body_id: int) -> object: ...

    def wncard(self, window: object) -> int: ...

    def wnfetd(self, window: object, interval: int) -> tuple[float, float]: ...


@dataclass(frozen=True, slots=True)
class LoadedKernel:
    """Verified manifest entry loaded and owned by a session."""

    path: str
    sha256: str
    kind: KernelKind
    role: KernelRole
    source: str
    size_bytes: int
    load_order: int
    owned_by_session: bool = True


@dataclass(frozen=True, slots=True)
class StateQueryResult:
    """Validated SPICE target state relative to an observer at one ET epoch."""

    target: str
    observer: str
    frame: str
    et_tdb_seconds_past_j2000: float
    aberration_correction: AberrationCorrection
    state_km_km_s: tuple[float, float, float, float, float, float]
    light_time_seconds: float
    kernels: tuple[LoadedKernel, ...]


class KernelSession:
    """Context-managed owner for a manifest's SPICE KEEPER loads.

    A process-wide reentrant lock is held for the full context lifetime. A clean
    KEEPER pool is required at entry; this adapter never calls ``kclear`` and
    unloads only paths it loaded. Use one kernel-owning session per process.
    """

    def __init__(self, manifest: KernelManifest, *, spice_api: SpiceApi | None = None) -> None:
        self.manifest = manifest
        self._spice = spice_api
        self._state = "new"
        self._owned: list[tuple[KernelSpec, Path]] = []
        self._loaded_records: list[LoadedKernel] = []
        self._lock_held = False
        self._process_id: int | None = None
        self._thread_id: int | None = None

    @property
    def loaded_kernels(self) -> tuple[LoadedKernel, ...]:
        """Return immutable load/provenance records in manifest order."""
        return tuple(self._loaded_records)

    @property
    def is_open(self) -> bool:
        """Whether the session currently owns an active SPICE pool lock."""
        return self._state == "open"

    def __enter__(self) -> KernelSession:
        if self._state != "new":
            raise KernelSessionError(f"session cannot be entered from state {self._state!r}")
        _PROCESS_SPICE_LOCK.acquire()
        self._lock_held = True
        self._process_id = os.getpid()
        self._thread_id = threading.get_ident()
        try:
            self._spice = self._spice or _import_spiceypy()
            loaded_count = self._spice.ktotal("ALL")
            if loaded_count != 0:
                raise KernelSessionError(
                    f"refusing to share a pre-populated SPICE KEEPER pool ({loaded_count} kernels)"
                )
            resolved = [(spec, self.manifest.resolve(spec)) for spec in self.manifest.kernels]
            canonical_paths = [path for _, path in resolved]
            if len(set(canonical_paths)) != len(canonical_paths):
                raise KernelManifestError("manifest paths resolve to duplicate kernel files")
            for spec, path in resolved:
                self._verify_file(spec, path)
            for spec, path in resolved:
                self._load_one(spec, path)
            self._state = "open"
            return self
        except BaseException as primary:
            cleanup_errors = self._unload_owned()
            self._state = "failed" if self._owned else "closed"
            self._release_lock()
            if cleanup_errors:
                raise BaseExceptionGroup(
                    "SPICE session setup failed and rollback encountered unload errors",
                    [primary, *cleanup_errors],
                )
            raise

    def __exit__(self, exc_type: object, exc: BaseException | None, traceback: object) -> Literal[False]:
        del exc_type, traceback
        try:
            self.close()
        except KernelCleanupError as cleanup_error:
            if exc is not None:
                raise BaseExceptionGroup(
                    "SPICE session body and kernel cleanup both failed",
                    [exc, cleanup_error],
                )
            raise
        return False

    def close(self) -> None:
        """Unload session-owned kernels in reverse load order and release the lock.

        If an unload fails, all remaining owned paths are retained for an
        explicit later ``close()`` retry, and the failure is raised.
        """
        if self._state == "closed":
            return
        if self._state == "new":
            self._state = "closed"
            return
        if self._process_id != os.getpid():
            raise KernelSessionError("an active SPICE session cannot be closed from a forked process")
        if self._thread_id != threading.get_ident():
            raise KernelSessionError("an active SPICE session must be closed by its owning thread")
        if not self._lock_held:
            _PROCESS_SPICE_LOCK.acquire()
            self._lock_held = True
        errors = self._unload_owned()
        self._state = "failed" if self._owned else "closed"
        self._release_lock()
        if errors:
            error = KernelCleanupError(
                "failed to unload session-owned kernels: "
                + ", ".join(str(path) for _, path in self._owned)
            )
            raise error from errors[0]

    def check_spk_body_coverage(self, spec: KernelSpec, body_id: int, et: float) -> tuple[tuple[float, float], ...]:
        """Read one SPK file's coverage and require ``et`` in a body interval.

        This file-level check is diagnostic. A state query between two bodies
        must additionally call :meth:`validate_state_query`, which asks SPICE to
        resolve the actual target-observer chain at the requested epoch.
        """
        self._ensure_open()
        if spec.kind is not KernelKind.SPK:
            raise EphemerisCoverageError(f"coverage requested for non-SPK kernel: {spec.path}")
        if isinstance(body_id, bool) or not isinstance(body_id, int):
            raise EphemerisCoverageError("SPK body_id must be an integer NAIF ID")
        if not math.isfinite(et):
            raise EphemerisCoverageError("SPK coverage epoch must be finite ET seconds")
        path = self.manifest.resolve(spec)
        if not any(owned_path == path for _, owned_path in self._owned):
            raise EphemerisCoverageError("coverage kernel is not owned by this active session")
        assert self._spice is not None
        try:
            objects = {int(code) for code in self._spice.spkobj(str(path))}
            if body_id not in objects:
                raise EphemerisCoverageError(
                    f"SPK {path} contains no segment for NAIF body {body_id}"
                )
            window = self._spice.spkcov(str(path), body_id)
            intervals = tuple(
                (float(start), float(stop))
                for start, stop in (
                    self._spice.wnfetd(window, index)
                    for index in range(self._spice.wncard(window))
                )
            )
        except EphemerisCoverageError:
            raise
        except Exception as exc:
            raise EphemerisCoverageError(
                f"SPICE could not inspect coverage for body {body_id} in {path}"
            ) from exc
        if not intervals or not any(start <= et <= stop for start, stop in intervals):
            raise EphemerisCoverageError(
                f"ET {et} is not covered for NAIF body {body_id} by SPK {path}"
            )
        return intervals

    def validate_state_query(
        self,
        target: str,
        observer: str,
        et: float,
        frame: str,
        correction: AberrationCorrection,
    ) -> StateQueryResult:
        """Execute and validate the actual target-to-observer state chain at ET.

        ET is seconds past J2000 TDB. A successful query is point evidence only;
        it does not establish coverage at other epochs or certify a mission.
        """
        self._ensure_open()
        if not target.strip() or not observer.strip() or target == observer:
            raise EphemerisQueryError("target and observer must be distinct nonempty SPICE names")
        if not math.isfinite(et):
            raise EphemerisQueryError("ET must be finite seconds past J2000 TDB")
        if not frame.strip():
            raise FrameTransformError("output frame must be explicitly named")
        if not isinstance(correction, AberrationCorrection):
            raise EphemerisQueryError("aberration correction must be an explicit supported enum")
        self.frame_rotation("J2000", frame, et)
        assert self._spice is not None
        try:
            raw_state, raw_light_time = self._spice.spkezr(
                target, et, frame, correction.value, observer
            )
            state = tuple(float(component) for component in raw_state)
            light_time = float(raw_light_time)
        except Exception as exc:
            raise EphemerisQueryError(
                "SPICE state query failed for "
                f"target={target!r}, observer={observer!r}, et={et}, frame={frame!r}, "
                f"abcorr={correction.value!r}; query coverage/frame chain is not established"
            ) from exc
        if len(state) != 6 or any(not math.isfinite(value) for value in state):
            raise EphemerisQueryError("SPICE returned an invalid or nonfinite six-component state")
        if not math.isfinite(light_time) or light_time < 0.0:
            raise EphemerisQueryError("SPICE returned invalid one-way light time")
        return StateQueryResult(
            target,
            observer,
            frame,
            et,
            correction,
            state,
            light_time,
            self.loaded_kernels,
        )

    def frame_rotation(self, from_frame: str, to_frame: str, et: float) -> Rotation3:
        """Query an epoch-specific SPICE frame transform and validate proper rotation."""
        self._ensure_open()
        if not from_frame.strip() or not to_frame.strip() or not math.isfinite(et):
            raise FrameTransformError("frame names and finite ET are required")
        assert self._spice is not None
        for name in (from_frame, to_frame):
            try:
                frame_id = int(self._spice.namfrm(name))
            except Exception as exc:
                raise FrameTransformError(f"SPICE could not resolve frame {name!r}") from exc
            if frame_id == 0:
                raise FrameTransformError(f"SPICE frame name is unknown: {name!r}")
        try:
            raw_matrix = self._spice.pxform(from_frame, to_frame, et)
            rows = tuple(tuple(float(value) for value in row) for row in raw_matrix)
            if len(rows) != 3 or any(len(row) != 3 for row in rows):
                raise ValueError("pxform did not return a 3 by 3 matrix")
            return Rotation3(cast(Matrix3, rows), tolerance=1e-10)
        except Exception as exc:
            raise FrameTransformError(
                f"SPICE transform unavailable from {from_frame!r} to {to_frame!r} at ET {et}"
            ) from exc

    def transform_vector(
        self, vector: Vector3, from_frame: str, to_frame: str, et: float
    ) -> Vector3:
        """Apply an actual SPICE frame rotation while preserving component units."""
        return self.frame_rotation(from_frame, to_frame, et).apply(vector)

    def _load_one(self, spec: KernelSpec, path: Path) -> None:
        assert self._spice is not None
        try:
            self._spice.furnsh(str(path))
        except Exception as exc:
            try:
                self._track_if_loaded(spec, path)
            except Exception as inspect_error:
                raise BaseExceptionGroup(
                    f"kernel load and post-failure ownership inspection failed for {path}",
                    [exc, inspect_error],
                )
            raise KernelSessionError(f"SPICE failed to load kernel {path}") from exc
        loaded = self._track_if_loaded(spec, path)
        if not loaded:
            raise KernelSessionError(
                f"SPICE furnsh returned but KEEPER does not list the requested kernel: {path}"
            )
        try:
            after_hash = sha256_file(path)
        except KernelManifestError:
            raise
        if after_hash != spec.sha256:
            raise KernelIntegrityError(f"kernel changed while SPICE loaded it: {path}")

    def _track_if_loaded(self, spec: KernelSpec, path: Path) -> bool:
        assert self._spice is not None
        records = self._keeper_records()
        match = next((record for record in records if _same_path(record[0], path)), None)
        if match is None:
            return False
        if not any(owned_path == path for _, owned_path in self._owned):
            self._owned.append((spec, path))
            actual_type = match[1].upper()
            if actual_type != spec.kind.value:
                raise KernelSessionError(
                    f"kernel type mismatch for {path}: manifest={spec.kind.value}, "
                    f"SPICE KEEPER={actual_type}"
                )
            self._loaded_records.append(
                LoadedKernel(
                    str(path),
                    spec.sha256,
                    spec.kind,
                    spec.role,
                    spec.source,
                    path.stat().st_size,
                    len(self._loaded_records),
                )
            )
        return True

    def _keeper_records(self) -> tuple[tuple[str, str], ...]:
        assert self._spice is not None
        result: list[tuple[str, str]] = []
        count = self._spice.ktotal("ALL")
        for index in range(count):
            data = self._spice.kdata(index, "ALL")
            if len(data) < 4:
                raise KernelSessionError("SPICE kdata returned an incomplete KEEPER record")
            result.append((str(data[0]), str(data[1])))
        return tuple(result)

    def _verify_file(self, spec: KernelSpec, path: Path) -> None:
        digest = sha256_file(path)
        if digest != spec.sha256:
            raise KernelIntegrityError(
                f"SHA-256 mismatch for kernel {path}: expected {spec.sha256}, got {digest}"
            )
        if spec.kind is KernelKind.TEXT:
            try:
                with path.open("rb") as stream:
                    first_line = stream.readline(256).strip()
            except OSError as exc:
                raise KernelManifestError(f"cannot inspect text kernel header: {path}") from exc
            if not first_line.startswith(b"KPL/"):
                raise KernelManifestError(f"text kernel lacks a KPL header: {path}")
            if first_line == b"KPL/MK":
                raise KernelManifestError(
                    f"meta-kernels are not accepted; list each individual kernel explicitly: {path}"
                )

    def _unload_owned(self) -> list[BaseException]:
        if self._spice is None:
            return []
        errors: list[BaseException] = []
        remaining: list[tuple[KernelSpec, Path]] = []
        for spec, path in reversed(self._owned):
            try:
                self._spice.unload(str(path))
            except BaseException as exc:
                errors.append(exc)
                remaining.append((spec, path))
        self._owned = list(reversed(remaining))
        return errors

    def _ensure_open(self) -> None:
        if self._state != "open":
            raise KernelSessionError(f"SPICE query requires an open session; state={self._state!r}")
        if self._process_id != os.getpid():
            raise KernelSessionError("an active SPICE session cannot be used from a forked process")
        if self._thread_id != threading.get_ident():
            raise KernelSessionError("SPICE session queries must run on the owning thread")

    def _release_lock(self) -> None:
        if self._lock_held:
            self._lock_held = False
            _PROCESS_SPICE_LOCK.release()


def _same_path(keeper_path: str, requested_path: Path) -> bool:
    try:
        return Path(keeper_path).resolve(strict=False) == requested_path
    except (OSError, RuntimeError):
        return os.path.abspath(keeper_path) == str(requested_path)


def _import_spiceypy() -> SpiceApi:
    try:
        import spiceypy  # type: ignore[import-not-found]
    except ImportError as exc:
        raise KernelSessionError(
            "SpiceyPy is optional; install SELENE-PRIME with the 'spice' extra"
        ) from exc
    return cast(SpiceApi, spiceypy)
