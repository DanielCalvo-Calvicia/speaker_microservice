from abc import ABC, abstractmethod

from application.dtos.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.dtos.readiness_outbound import ReadinessOutboundDTO


class SpeakerPlaybackPort(ABC):
    """What the outside world may ask of the application."""

    @abstractmethod
    async def play(self, request: PlayStreamInboundDTO) -> PlaybackOutboundDTO:
        """Play the request's audio stream until it ends. A new call supersedes a running one."""

    @abstractmethod
    async def stop_playback(self) -> None:
        """Interrupt any playback and release the device. Does nothing if idle."""

    @abstractmethod
    async def check_readiness(self) -> ReadinessOutboundDTO:
        """Probe whether the output device is usable without opening a stream."""

    @abstractmethod
    def is_available(self) -> bool:
        """True while a playback session is active."""
