"""Explicit error types used by providers, validation, and scientific workflows."""


class BiomedicalError(Exception):
    """Base exception with a stable machine-readable category."""

    category = "biomedical_error"


class ValidationError(BiomedicalError):
    category = "validation_error"


class NetworkError(BiomedicalError):
    category = "network_error"


class ProviderError(BiomedicalError):
    category = "provider_error"


class RateLimitError(ProviderError):
    category = "rate_limit"


class AuthenticationError(ProviderError):
    category = "authentication_error"


class ParseError(BiomedicalError):
    category = "parse_error"


class UnsupportedFormatError(BiomedicalError):
    category = "unsupported_format"


class InsufficientEvidenceError(BiomedicalError):
    category = "insufficient_evidence"
