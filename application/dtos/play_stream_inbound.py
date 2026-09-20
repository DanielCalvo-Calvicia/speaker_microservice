import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass

from application.dtos.playback_outbound import PlaybackOutboundDTO


@dataclass(slots=True, frozen=True)
class PlayStreamInboundDTO:
    """Carries a playback request, and the audio to play, into the application layer.

    ``setup_future`` lets the caller learn as soon as the device is ready (or has failed to
    open) without waiting for the whole stream to be played.
    """

    audio_stream: AsyncIterator[bytes]
    sample_rate: int = 24000
    channels: int = 1
    setup_future: asyncio.Future[PlaybackOutboundDTO] | None = None

    def acknowledge_setup(self, result: PlaybackOutboundDTO) -> None:
        """Resolve ``setup_future`` once; later calls and a missing future are ignored."""
        if self.setup_future is not None and not self.setup_future.done():
            self.setup_future.set_result(result)
