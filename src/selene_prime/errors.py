"""Typed exceptions shared by SELENE-PRIME subsystems."""


class SelenePrimeError(Exception):
    """Base class for expected SELENE-PRIME failures."""


class ConfigurationError(SelenePrimeError, ValueError):
    """Raised when a user-supplied configuration is invalid or incomplete."""


class ProvenanceError(SelenePrimeError, ValueError):
    """Raised when provenance metadata is malformed or incomplete."""


class UnsupportedInputError(SelenePrimeError):
    """Raised when an input format or scientific convention is unsupported."""


class KernelError(SelenePrimeError):
    """Base class for kernel manifest, integrity, and lifecycle failures."""


class KernelManifestError(KernelError, ValueError):
    """Raised when a kernel manifest is invalid or unsupported."""


class KernelIntegrityError(KernelError):
    """Raised when a kernel file does not match its declared SHA-256 digest."""


class KernelSessionError(KernelError):
    """Raised when a SPICE session cannot safely start or load its kernels."""


class KernelCleanupError(KernelError):
    """Raised when one or more session-owned kernels could not be unloaded."""


class EphemerisCoverageError(KernelError):
    """Raised when a requested SPK coverage query is absent or excludes the epoch."""


class EphemerisQueryError(KernelError):
    """Raised when the actual target-observer SPICE state query fails validation."""


class FrameTransformError(KernelError):
    """Raised when a frame name or epoch-dependent transformation is unavailable."""
