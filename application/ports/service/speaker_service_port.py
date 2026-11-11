from abc import ABC, abstractmethod

from application.dtos.inbound.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.dtos.outbound.readiness_outbound import ReadinessOutboundDTO


class SpeakerServicePort(ABC):
    """The service's own port: the speaker use cases. ``SpeakerService`` implements it; the inbound
    adapters call it (through the inbound port); nothing else in the application knows the concrete
    service."""

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
