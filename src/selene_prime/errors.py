"""Typed exceptions shared by SELENE-PRIME subsystems."""


class SelenePrimeError(Exception):
    """Base class for expected SELENE-PRIME failures."""


class ConfigurationError(SelenePrimeError, ValueError):
    """Raised when a user-supplied configuration is invalid or incomplete."""


class ProvenanceError(SelenePrimeError, ValueError):
    """Raised when provenance metadata is malformed or incomplete."""


class UnsupportedInputError(SelenePrimeError):
    """Raised when an input format or scientific convention is unsupported."""
