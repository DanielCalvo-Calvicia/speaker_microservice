class ApplicationError(Exception):
    """Base class for failures of a use case that are not business-rule violations."""


class SpeakerUnavailable(ApplicationError, RuntimeError):
    """No output device could be selected.

    Also a RuntimeError so callers written against the previous behaviour keep working.
    """
