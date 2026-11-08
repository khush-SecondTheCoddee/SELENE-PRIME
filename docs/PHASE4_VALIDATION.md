# Phase 4 validation record — SPICE kernel and frame adapter

## Scope and evidence

This increment implements individually declared kernel manifests with SHA-256 verification, explicit KEEPER ownership, reverse-order unload, rollback, structured provenance records, SPK file coverage inspection, an actual target-observer query guard, and epoch-specific frame transforms. The adapter uses SpiceyPy's documented `furnsh`, `unload`, `ktotal`, `kdata`, `spkobj`, `spkcov`, `spkezr`, `namfrm`, and `pxform` interfaces.

The focused tests use an injected fake API and temporary arbitrary bytes. Those bytes are not SPICE kernels and are never treated as ephemeris evidence. The tests prove software behavior under those injected responses only.

## Executed cases

| Case | Expected behavior | Executed result |
|---|---|---|
| Explicit load and context close | Load declared files; unload only owned files in reverse order | Pass |
| Hash changed after manifest creation | Reject before calling `furnsh` | Pass |
| Caller-owned KEEPER entry exists | Refuse session and preserve caller entry | Pass |
| `furnsh` raises after adding a file | Detect ownership and roll back all files | Pass |
| `unload` fails | Surface cleanup error, retain ownership, allow explicit retry | Pass |
| State and frame query | Preserve explicit target, observer, frame, ET, correction; reject unknown frame | Pass |
| SPK body absent or epoch outside window | Raise coverage error; failed state chain remains failure | Pass |

Commands executed on Python 3.14.6 / Android (Termux):

- `pytest -q tests/unit/test_kernel_session.py` — **7 passed**.
- `python -m pytest -q` — **32 passed** (full current suite).
- `python -m mypy` — **passed**, strict configuration, 14 source files checked.
- Ruff — **not run**, Ruff is not installed in this environment.

## Not established

No genuine SPICE kernel was available or loaded. Consequently there is no result here for actual NAIF SPK coverage, lunar orientation/frame kernel availability, an independent SPICE state reference, multi-kernel competing segment resolution, or a real station-to-Sun/Earth query. No mission certification or coverage over a time interval is implied. A successful query, when run with real kernels, is point evidence at that ET and the selected frame/correction only.

For real use, obtain authentic kernels from an authoritative source, verify their source and published checksums independently, create manifest entries from those verified files, and preserve the source/version and query configuration in the run record. A locally computed digest establishes file identity after acquisition; it does not authenticate the source.
