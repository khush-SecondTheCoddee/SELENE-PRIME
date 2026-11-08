"""Typed exceptions shared by SELENE-PRIME subsystems."""


class SelenePrimeError(Exception):
    """Base class for expected SELENE-PRIME failures."""


class ConfigurationError(SelenePrimeError, ValueError):
    """Raised when a user-supplied configuration is invalid or incomplete."""


class ProvenanceError(SelenePrimeError, ValueError):
    """Raised when provenance metadata is malformed or incomplete."""


class UnsupportedInputError(SelenePrimeError):
    """Raised when an input format or scientific convention is unsupported."""


class FrameDefinitionError(ConfigurationError):
    """Raised when frame metadata is missing, conflicting, or unsuitable."""


class FrameTransformError(SelenePrimeError):
    """Raised when a requested frame transformation cannot be established."""


class OptionalDependencyError(SelenePrimeError, ImportError):
    """Raised when an optional integration dependency is unavailable."""
