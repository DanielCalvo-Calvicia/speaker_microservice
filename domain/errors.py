"""Domain errors.

They also inherit from the matching builtin exception so that callers written
against the pre-refactor behaviour (``ValueError``) keep working.
"""


class DomainError(Exception):
    """Base class for every business-rule violation raised by the domain."""


class InvalidPlaybackFormat(DomainError, ValueError):
    """The requested playback format violates an invariant (e.g. non-positive rate)."""
