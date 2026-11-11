from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class PlaybackOutboundDTO:
    """Outcome of setting up or finishing a playback, handed back to an inbound adapter."""

    success: bool
    message: str
