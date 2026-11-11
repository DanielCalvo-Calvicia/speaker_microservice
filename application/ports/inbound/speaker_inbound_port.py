from abc import ABC, abstractmethod

from application.dtos.inbound.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.dtos.outbound.readiness_outbound import ReadinessOutboundDTO


class SpeakerInboundPort(ABC):
    """What every inbound adapter offers, whatever its transport (HTTP today, gRPC or a CLI later).

    The same operations with DTOs and no transport types: an adapter decodes its own requests into
    these calls and encodes what they return. A new inbound adapter implements this port, so its
    functions are the same.
    """

    @abstractmethod
    def health(self) -> bool:
        """True while the adapter is serving."""

    @abstractmethod
    async def check_readiness(self) -> ReadinessOutboundDTO:
        """Probe whether the output device is usable without opening a stream."""

    @abstractmethod
    async def play(self, request: PlayStreamInboundDTO) -> PlaybackOutboundDTO:
        """Play the request's audio stream until it ends. A new call supersedes a running one."""
