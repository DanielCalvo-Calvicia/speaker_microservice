from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ReadinessOutboundDTO:
    """Result of probing the output device without opening a stream."""

    is_ready: bool
    message: str | None = None
