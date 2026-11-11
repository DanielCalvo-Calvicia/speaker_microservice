"""Outbound adapter: a playback backend that plays nothing (SPEAKER_BACKEND=null, ADR-012).

Implements ``SpeakerOutboundPort`` without any sound hardware or PortAudio, so a machine with no
sound card (a server, a CI run, a container on Windows) can run the service and Brain's pipeline.
It behaves like the real backend for its caller: it reads the whole request stream however fast
the sender is (otherwise Brain's request would back up), takes the time the audio would take to
play (so ``completed`` arrives when real playback would), lets a new request supersede the running
one and keeps no audio, only counters in the log.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from shared_logging import get_logger

from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.dtos.outbound.readiness_outbound import ReadinessOutboundDTO
from application.ports.outbound.speaker_outbound_port import SpeakerOutboundPort
from domain.value_objects.playback_format import PlaybackFormat

logger = get_logger(__name__)

# What `/available` says in its `reason` (the deployment tool shows it as a warning).
NULL_NOTE = "null sink (SPEAKER_BACKEND=null): audio is discarded, nothing is played"

_POLL_SECONDS = 0.1  # how often a waiting playback looks for a newer request or a close
_BYTES_PER_SAMPLE = 2  # PCM16


class NullAudioPlayback(SpeakerOutboundPort):
    def __init__(
        self,
        realtime: bool = True,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._realtime = realtime
        self._sleep = sleep
        self._monotonic = monotonic
        self._session: object | None = None  # the token of the playback that is current

    def is_playing(self) -> bool:
        return self._session is not None

    async def play(
        self,
        audio_format: PlaybackFormat,
        audio_stream: AsyncIterator[bytes],
        on_started: Callable[[PlaybackOutboundDTO], None],
    ) -> PlaybackOutboundDTO:
        session = object()
        self._session = session  # a new request supersedes the running one (ADR-008)
        started_at = self._monotonic()
        on_started(PlaybackOutboundDTO(success=True, message="Playback stream started"))

        queued_chunks = 0
        queued_bytes = 0
        stream_error: Exception | None = None
        try:
            async for chunk in audio_stream:
                if self._session is not session:
                    logger.info("Playback session superseded; stopping audio consumption")
                    break
                if chunk:
                    queued_chunks += 1
                    queued_bytes += len(chunk)
        except Exception as error:
            stream_error = error
            logger.error(
                "Error consuming inbound audio stream",
                type=type(error).__name__,
                message=str(error),
            )

        if stream_error is None and self._realtime:
            bytes_per_second = audio_format.sample_rate * audio_format.channels * _BYTES_PER_SAMPLE
            await self._wait_until_played(
                session, started_at + queued_bytes / bytes_per_second
            )
        superseded = self._session is not session
        if not superseded:
            self._session = None
        logger.info(
            "Null playback session finalized",
            queued_chunks=queued_chunks,
            queued_bytes=queued_bytes,
        )
        if stream_error is not None:
            return PlaybackOutboundDTO(success=False, message=str(stream_error))
        if superseded:
            return PlaybackOutboundDTO(
                success=True, message="Playback session superseded by new request"
            )
        return PlaybackOutboundDTO(success=True, message="Playback session finalized successfully")

    async def close(self) -> None:
        self._session = None  # whatever plays ends at its next look

    async def check_readiness(self) -> ReadinessOutboundDTO:
        return ReadinessOutboundDTO(is_ready=True, message=NULL_NOTE)

    async def _wait_until_played(self, session: object, deadline: float) -> None:
        """Wait until a device would have finished the audio, or this playback is replaced."""
        while self._session is session:
            remaining = deadline - self._monotonic()
            if remaining <= 0:
                return
            await self._sleep(min(remaining, _POLL_SECONDS))
