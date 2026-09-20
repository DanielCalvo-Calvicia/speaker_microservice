from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable

from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.dtos.readiness_outbound import ReadinessOutboundDTO
from domain.value_objects.playback_format import PlaybackFormat


class AudioPlaybackPort(ABC):
    """What the application needs from an output device."""

    @abstractmethod
    async def play(
        self,
        audio_format: PlaybackFormat,
        audio_stream: AsyncIterator[bytes],
        on_started: Callable[[PlaybackOutboundDTO], None],
    ) -> PlaybackOutboundDTO:
        """Write ``audio_stream`` to the device as close to ``audio_format`` as it allows.

        ``on_started`` is called once, as soon as the device is open (success) or has failed
        to open (failure); the returned result describes how the whole playback ended.
        A hardware failure is reported in the result, not raised.
        """

    @abstractmethod
    async def close(self) -> None:
        """Interrupt any playback and release the device. Must be idempotent."""

    @abstractmethod
    async def check_readiness(self) -> ReadinessOutboundDTO:
        """Probe the output device without opening a stream."""

    @abstractmethod
    def is_playing(self) -> bool:
        """True while a playback session is active."""
