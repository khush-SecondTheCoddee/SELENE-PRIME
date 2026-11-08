# Phase 4 — Reference-frame service: implementation record

**Scope:** explicit frame metadata, frame-tagged vectors, rotation-only transforms, and an optional SpiceyPy pxform adapter.

## Implemented

- Frames are explicitly registered with a name, center identifier, broad kind, and provenance/source string.
- Unknown frame names and conflicting duplicate declarations fail closed.
- Body-fixed coordinate boundaries can require a declared body-fixed frame and expected center.
- Frame-tagged vectors preserve their units through rotations.
- Rotation-only transformations are allowed only between frames declared to share the same origin. Different centers require a future state-transform service; no translation is invented.
- The transform service requires finite SPICE ET seconds and never assumes identity for distinct frames.
- The optional SpiceyPy adapter delegates to pxform(source, target, et); SPICE errors become typed frame-transform errors.
- SpiceyPy is not imported at package import time. Kernel furnishing, ownership, time conversion, and coverage remain outside this adapter.

## Deliberate limitations

- No default IAU_MOON, MOON_ME, or other lunar frame is registered. A name must be backed by the actual mission kernel set and an explicit project declaration.
- A registry declaration is metadata, not proof that SPICE can resolve the frame. The actual pxform call is the runtime check.
- This is a rotation-only vector service. It does not transform between different origins, calculate state vectors, or apply translational/velocity terms.
- ET is already ephemeris time in seconds past J2000 as required by SPICE. No UTC/TDB parsing or conversion is performed here.
- The existing generic ellipsoid implementation supports oblate/spherical ellipsoids only. It is not declared to be a lunar datum and does not yet implement a triaxial lunar reference surface.
- No real lunar kernels, lunar datum constants, product metadata, or external lunar reference points were available to validate in this phase.

## Verification

Unit tests use synthetic frame declarations and an injected fake transform provider. They verify rotation direction, unit preservation, unknown-frame rejection, origin mismatch rejection, invalid epochs, and propagation of SPICE transform failure. These tests validate service behavior, not the correctness of any real lunar frame definition or kernel set.

## Phase 4 exit criteria

The software interface and failure behavior are implemented. Scientific qualification of a selected lunar frame/datum remains pending until a concrete product/use case, authoritative parameter sources, genuine kernels, and independent reference points are selected and tested.
