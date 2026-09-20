from shared_logging import get_logger

from application.dtos.play_stream_inbound import PlayStreamInboundDTO
from application.dtos.playback_outbound import PlaybackOutboundDTO
from application.dtos.readiness_outbound import ReadinessOutboundDTO
from application.ports.inbound.speaker_playback_port import SpeakerPlaybackPort
from application.ports.outbound.audio_playback_port import AudioPlaybackPort
from domain.errors import InvalidPlaybackFormat
from domain.value_objects.playback_format import PlaybackFormat

logger = get_logger(__name__)


class SpeakerService(SpeakerPlaybackPort):
    """Orchestrates the speaker use cases. Business rules live in the domain."""

    def __init__(self, playback: AudioPlaybackPort, name: str = "Speaker") -> None:
        self.name = name
        self._playback = playback
        logger.info("SpeakerService initialized", name=name)

    async def play(self, request: PlayStreamInboundDTO) -> PlaybackOutboundDTO:
        try:
            audio_format = PlaybackFormat(
                sample_rate=request.sample_rate, channels=request.channels
            )
        except InvalidPlaybackFormat as error:
            logger.warning("Rejecting playback request", error=error)
            result = PlaybackOutboundDTO(success=False, message=str(error))
            request.acknowledge_setup(result)
            return result

        result = await self._playback.play(
            audio_format, request.audio_stream, request.acknowledge_setup
        )
        logger.info("Playback finished", success=result.success, message=result.message)
        return result

    async def stop_playback(self) -> None:
        await self._playback.close()
        logger.info("Speaker playback stopped")

    async def check_readiness(self) -> ReadinessOutboundDTO:
        return await self._playback.check_readiness()

    def is_available(self) -> bool:
        return self._playback.is_playing()
