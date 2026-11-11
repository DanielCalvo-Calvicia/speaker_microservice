"""Outbound adapter: plays audio on an output device through an ``AudioDriver``.

Implements ``SpeakerOutboundPort``. It only talks to hardware; which formats to try is decided
by ``domain.operations.format_negotiation``, which device to use by ``DeviceSelector``.

A playback session pumps the incoming stream into a queue that a worker drains into the
device. Starting a new session supersedes the running one.
"""

import asyncio
from collections.abc import AsyncIterator, Callable

from shared_logging import get_logger

from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from application.dtos.outbound.readiness_outbound import ReadinessOutboundDTO
from application.errors import SpeakerUnavailable
from application.ports.outbound.speaker_outbound_port import SpeakerOutboundPort
from domain.operations.format_negotiation import fallback_formats
from domain.operations.resample import LinearResampler
from domain.value_objects.playback_format import PlaybackFormat
from infrastructure.outbound.sounddevice_playback.audio_driver import AudioDriver, RawOutput
from infrastructure.outbound.sounddevice_playback.sounddevice_device_selector import (
    DeviceSelector,
)

logger = get_logger(__name__)

_QUEUE_POLL_SECONDS = 0.1
# Added to the duration of the queued audio: the device's own buffering and a slow start.
_DRAIN_MARGIN_SECONDS = 2.0
_BYTES_PER_SAMPLE = 2  # PCM16


def _drain_timeout_seconds(queued_bytes: int, audio_format: PlaybackFormat) -> float:
    """How long the end of a session may wait for the device to play what was queued.

    A sender faster than real time (tts is) hands over the whole reply at once, so when its stream
    ends the device may still have to play nearly all of it. The duration of everything queued is an
    upper bound of what is left (the device has been playing it since the start): the wait always
    ends, even when the device stalls, and never cuts a reply that is playing normally.
    """
    bytes_per_second = audio_format.sample_rate * audio_format.channels * _BYTES_PER_SAMPLE
    return queued_bytes / bytes_per_second + _DRAIN_MARGIN_SECONDS


class SoundDeviceAudioPlayback(SpeakerOutboundPort):
    def __init__(self, driver: AudioDriver, selector: DeviceSelector) -> None:
        self._driver = driver
        self._selector = selector
        self._stream: RawOutput | None = None
        self._playback_task: asyncio.Task[None] | None = None
        self._is_playing = False
        self._lock = asyncio.Lock()
        self._current_session: object | None = None

        try:
            self._device_index = selector.select()
        except Exception as error:
            logger.critical("Failed to query sounddevice output devices", error=error)
            raise SpeakerUnavailable(f"sounddevice bootstrap failed: {error}") from error
        logger.info("SoundDeviceAudioPlayback initialized", device_index=self._device_index)

    def is_playing(self) -> bool:
        return self._is_playing

    async def play(
        self,
        audio_format: PlaybackFormat,
        audio_stream: AsyncIterator[bytes],
        on_started: Callable[[PlaybackOutboundDTO], None],
    ) -> PlaybackOutboundDTO:
        # Unique token for this session; lets the finally block detect supersession.
        session_id = object()

        # Setup phase (lock held)
        async with self._lock:
            if self._is_playing:
                logger.info("Existing playback is active; cleaning it up before starting a new one")
                await self._cleanup_playback_task()

            try:
                opened = await asyncio.to_thread(self._open_device_stream, audio_format)
            except Exception as error:
                logger.error("Failed to open hardware device", error=error)
                failed = PlaybackOutboundDTO(
                    success=False, message=f"Hardware stream open failure: {error}"
                )
                on_started(failed)
                return failed

            queue: asyncio.Queue[bytes | None] = asyncio.Queue()
            self._is_playing = True
            self._current_session = session_id
        # Lock released: stream consumption runs outside the lock.

        counters = _Counters()
        resampler = None
        if opened.sample_rate != audio_format.sample_rate:
            # The device cannot play the stream's rate. Writing the samples as they are would play
            # them at the wrong speed and pitch, so they are converted to the rate it accepted.
            logger.warning(
                "Output device rate differs from the stream rate; resampling",
                stream_rate=audio_format.sample_rate,
                device_rate=opened.sample_rate,
            )
            resampler = LinearResampler(
                audio_format.sample_rate, opened.sample_rate, audio_format.channels
            )
        self._playback_task = asyncio.create_task(
            self._audio_player_worker(queue, counters, resampler)
        )
        on_started(PlaybackOutboundDTO(success=True, message="Playback stream started"))

        stream_error: Exception | None = None
        drain_timed_out = False
        try:
            async for chunk in audio_stream:
                if not self._is_playing or self._current_session is not session_id:
                    logger.info("Playback session superseded; stopping audio consumption")
                    break
                if chunk:
                    counters.queued_chunks += 1
                    counters.queued_bytes += len(chunk)
                    await queue.put(chunk)
        except Exception as error:
            stream_error = error
            logger.error(
                "Error consuming inbound audio stream",
                type=type(error).__name__,
                message=str(error),
            )
        finally:
            logger.info(
                "Finished consuming inbound audio stream",
                queued_chunks=counters.queued_chunks,
                queued_bytes=counters.queued_bytes,
            )
            # Only clean up shared state if this session is still the active one.
            superseded = self._current_session is not session_id
            if not superseded:
                await queue.put(None)
                drained = await self._wait_for_drain(
                    queue, session_id, _drain_timeout_seconds(counters.queued_bytes, audio_format)
                )
                if drained == "drained":
                    logger.info("Playback queue drained successfully")
                elif drained == "replaced":
                    # A newer request (or a close) took over while this one was still draining:
                    # the state belongs to it now, and this one just ends.
                    superseded = True
                    logger.info("Playback session superseded while draining")
                else:
                    drain_timed_out = True
                    logger.warning(
                        "Playback queue cleanup timed out; truncating",
                        queued_bytes=counters.queued_bytes,
                        written_bytes=counters.written_bytes,
                    )
                if not superseded:
                    self._is_playing = False
                    self._current_session = None

        logger.info(
            "Playback session finalized",
            queued_chunks=counters.queued_chunks,
            queued_bytes=counters.queued_bytes,
            written_chunks=counters.written_chunks,
            written_bytes=counters.written_bytes,
        )
        if stream_error is not None:
            return PlaybackOutboundDTO(success=False, message=str(stream_error))
        if superseded:
            return PlaybackOutboundDTO(
                success=True, message="Playback session superseded by new request"
            )
        if drain_timed_out:
            # The device did not play what was queued within the bound (a stalled device): the audio
            # was cut, so the caller is told instead of being answered "success" (R-6, Q01-6).
            return PlaybackOutboundDTO(
                success=False,
                message=(
                    "Playback did not finish: the device played "
                    f"{counters.written_bytes} of {counters.queued_bytes} bytes "
                    "before the wait ran out"
                ),
            )
        return PlaybackOutboundDTO(success=True, message="Playback session finalized successfully")

    async def _wait_for_drain(
        self, queue: "asyncio.Queue[bytes | None]", session_id: object, timeout: float
    ) -> str:
        """Wait for the device to play the queue: ``drained``, ``replaced`` or ``timeout``.

        ``replaced`` means a newer request or a close made this session no longer the current one
        (its worker was cancelled, so the queue would never drain): waiting out the bound would hold
        the caller's request for nothing and report a stalled device that is not stalled.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        join = asyncio.ensure_future(queue.join())
        try:
            while not join.done():
                if self._current_session is not session_id:
                    return "replaced"
                remaining = deadline - loop.time()
                if remaining <= 0:
                    return "timeout"
                await asyncio.wait({join}, timeout=min(_QUEUE_POLL_SECONDS, remaining))
            return "drained"
        finally:
            if not join.done():
                join.cancel()

    async def close(self) -> None:
        logger.info("Cleaning up sounddevice resources")
        async with self._lock:
            await self._cleanup_playback_task()
            if self._stream is not None:
                self._release_stream(self._stream)
                self._stream = None
        logger.info("Sounddevice cleanup completed")

    async def check_readiness(self) -> ReadinessOutboundDTO:
        """Probe the output device without opening a stream."""
        try:
            info = await asyncio.to_thread(self._driver.device_info, self._device_index)
        except Exception as error:
            logger.warning("Speaker readiness check failed", error=error)
            return ReadinessOutboundDTO(is_ready=False, message=str(error))
        if info.max_output_channels > 0:
            logger.info(
                "Speaker hardware is ready",
                device_index=info.index,
                max_output_channels=info.max_output_channels,
            )
            return ReadinessOutboundDTO(is_ready=True)
        logger.warning("Speaker device has no output channels", device_index=info.index)
        return ReadinessOutboundDTO(
            is_ready=False, message="Selected device has no output channels."
        )

    def _open_device_stream(self, audio_format: PlaybackFormat) -> PlaybackFormat:
        """Open the device at the first format it accepts and return that format."""
        if self._stream is not None:
            logger.info("Closing previous stream before opening a new one")
            self._release_stream(self._stream)
            self._stream = None

        last_error: Exception | None = None
        for candidate in fallback_formats(audio_format):
            try:
                self._stream = self._driver.open_output(self._device_index, candidate)
            except Exception as error:
                logger.warning(
                    "Failed to open device with candidate format", candidate=candidate, error=error
                )
                last_error = error
                continue
            logger.info("Speaker started", device=self._device_index, format=candidate)
            return candidate

        assert last_error is not None
        raise last_error

    async def _audio_player_worker(
        self,
        queue: "asyncio.Queue[bytes | None]",
        counters: "_Counters",
        resampler: LinearResampler | None = None,
    ) -> None:
        """Background worker consuming raw bytes and writing them to the device."""
        logger.info("Audio player worker started")
        while self._is_playing:
            try:
                chunk = await asyncio.wait_for(queue.get(), timeout=_QUEUE_POLL_SECONDS)
            except TimeoutError:
                continue

            if chunk is None:  # stop sentinel
                queue.task_done()
                logger.info("Audio player worker received stop sentinel")
                break

            if self._stream is not None:
                try:
                    playable = resampler.process(chunk) if resampler is not None else chunk
                    if playable:
                        await asyncio.to_thread(self._stream.write, playable)
                    counters.written_chunks += 1
                    counters.written_bytes += len(chunk)
                except Exception as error:
                    logger.error("sounddevice write exception", error=error)
                    break

            queue.task_done()
        logger.info(
            "Audio player worker stopped",
            written_chunks=counters.written_chunks,
            written_bytes=counters.written_bytes,
        )

    async def _cleanup_playback_task(self) -> None:
        """Cancel the active worker task and reset playback state. Call with the lock held."""
        self._is_playing = False
        self._current_session = None
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()
            try:
                await self._playback_task
            except asyncio.CancelledError:
                logger.info("Playback task cancelled")
        self._playback_task = None

    @staticmethod
    def _release_stream(stream: RawOutput) -> None:
        try:
            if stream.active:
                stream.stop()
            stream.close()
        except Exception as error:
            logger.error("Error closing audio stream", error=error)


class _Counters:
    def __init__(self) -> None:
        self.queued_chunks = 0
        self.queued_bytes = 0
        self.written_chunks = 0
        self.written_bytes = 0
