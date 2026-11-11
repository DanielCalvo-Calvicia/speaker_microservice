"""The answer of ``POST /process/stream/set``: the NDJSON events of one playback."""

import asyncio
from collections.abc import AsyncGenerator

from shared_logging import get_logger

from application.dtos.outbound.playback_outbound import PlaybackOutboundDTO
from infrastructure.inbound.http.helpers.request_audio_reader import RequestAudioReader
from infrastructure.inbound.http.response.stream_events import NdjsonEventStream

logger = get_logger(__name__)


async def cancel_playback(task: "asyncio.Task[PlaybackOutboundDTO]", log_message: str) -> None:
    """Cancel a playback task that is still running and wait for it to unwind."""
    if task.done():
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info(log_message)


async def playback_events(
    play_task: "asyncio.Task[PlaybackOutboundDTO]",
    reader: RequestAudioReader,
    setup_response: PlaybackOutboundDTO,
    sample_rate: int,
    channels: int,
    keep_open_after_completed: bool,
    heartbeat_interval_seconds: float,
    max_heartbeats_after_completed: int | None,
) -> AsyncGenerator[str, None]:
    """``stream_started``, then ``completed`` or ``error`` (plus heartbeats if kept open)."""
    events = NdjsonEventStream()
    yield events.stream_started(setup_response.message, sample_rate, channels)

    try:
        while not play_task.done():
            await asyncio.sleep(0.1)

        response = await play_task

        if reader.read_error is not None:
            yield events.error(
                "request_stream_failed",
                f"Failed to read request stream: {reader.read_error}",
            )
        elif not response.success:
            logger.warning(
                "HTTP playback failed",
                chunks=reader.chunk_count,
                bytes=reader.total_bytes,
                message=response.message,
            )
            yield events.error("playback_failed", response.message)
        else:
            logger.info(
                "HTTP playback completed successfully",
                chunks=reader.chunk_count,
                bytes=reader.total_bytes,
                message=response.message,
            )
            yield events.completed(
                reason="end_of_input",
                chunk_count=reader.chunk_count,
                byte_count=reader.total_bytes,
                message=response.message,
            )

            heartbeat_count = 0
            while keep_open_after_completed:
                if (
                    max_heartbeats_after_completed is not None
                    and heartbeat_count >= max_heartbeats_after_completed
                ):
                    break
                await asyncio.sleep(max(0.1, heartbeat_interval_seconds))
                heartbeat_count += 1
                yield events.heartbeat()
    except Exception as error:
        logger.exception(
            "HTTP playback request failed",
            chunks=reader.chunk_count,
            bytes=reader.total_bytes,
        )
        yield events.error("stream_failed", f"Failed to play stream: {error}")
    finally:
        await cancel_playback(
            play_task, "HTTP playback task cancelled while closing response stream"
        )
